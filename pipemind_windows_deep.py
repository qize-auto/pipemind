"""PipeMind — Windows 深度适配层
注册表 / 服务 / 事件日志 / 计划任务 / 回收站 / UAC / 代理 / 自启动
"""
import os, subprocess, json, datetime, ctypes, sys, tempfile, glob, re

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))

# Windows-only 模块
try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False


def _ps(cmd: str, timeout: int = 15) -> tuple[str, str, int]:
    """执行 PowerShell 命令"""
    try:
        r = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", "timeout", -1
    except Exception as e:
        return "", str(e), -2


# ═══════════════════════════════════════
#  注册表操作
# ═══════════════════════════════════════

def reg_read(key_path: str, value_name: str = "") -> str:
    """读取注册表"""
    if not HAS_WINREG:
        return "⚠ 注册表操作仅支持 Windows"
    try:
        # 解析路径
        parts = key_path.split("\\", 1)
        hive_map = {
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
            "HKCU": winreg.HKEY_CURRENT_USER,
            "HKCR": winreg.HKEY_CLASSES_ROOT,
            "HKU":  winreg.HKEY_USERS,
            "HKCC": winreg.HKEY_CURRENT_CONFIG,
        }
        hive = hive_map.get(parts[0].upper(), winreg.HKEY_CURRENT_USER)
        sub_key = parts[1] if len(parts) > 1 else ""
        
        with winreg.OpenKey(hive, sub_key) as key:
            if value_name:
                value, type_id = winreg.QueryValueEx(key, value_name)
                type_names = {1: "SZ", 3: "BINARY", 4: "DWORD", 7: "MULTI_SZ", 11: "QWORD"}
                tname = type_names.get(type_id, str(type_id))
                return f"{value_name} ({tname}): {value}"
            else:
                # 列出所有值
                results = []
                i = 0
                while True:
                    try:
                        name, value, type_id = winreg.EnumValue(key, i)
                        results.append(f"  {name or '(默认)'}: {value}")
                        i += 1
                    except OSError:
                        break
                return "\n".join(results) if results else "(empty)"
    except FileNotFoundError:
        return "❌ 注册表路径不存在"
    except Exception as e:
        return f"❌ {e}"


def reg_write(key_path: str, value_name: str, value: str, value_type: str = "SZ") -> str:
    """写入注册表"""
    type_map = {"SZ": winreg.REG_SZ, "DWORD": winreg.REG_DWORD, "QWORD": winreg.REG_QWORD,
                "BINARY": winreg.REG_BINARY, "MULTI_SZ": winreg.REG_MULTI_SZ}
    try:
        parts = key_path.split("\\", 1)
        hive_map = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
        hive = hive_map.get(parts[0].upper(), winreg.HKEY_CURRENT_USER)
        sub_key = parts[1] if len(parts) > 1 else ""
        
        with winreg.CreateKey(hive, sub_key) as key:
            wt = type_map.get(value_type.upper(), winreg.REG_SZ)
            if wt == winreg.REG_DWORD:
                winreg.SetValueEx(key, value_name, 0, wt, int(value))
            else:
                winreg.SetValueEx(key, value_name, 0, wt, value)
        return f"✅ 已写入: {key_path}\\{value_name}"
    except PermissionError:
        return "❌ 权限不足（需管理员）"
    except Exception as e:
        return f"❌ {e}"


# ═══════════════════════════════════════
#  服务管理
# ═══════════════════════════════════════

def service_list(filter: str = "") -> str:
    """列出服务"""
    cmd = 'Get-Service | Select-Object Name, Status, DisplayName | Format-Table -AutoSize'
    if filter:
        cmd = f'Get-Service | Where-Object {{$_.Name -like "*{filter}*" -or $_.DisplayName -like "*{filter}*"}} | Select-Object Name, Status, DisplayName | Format-Table -AutoSize'
    out, err, code = _ps(cmd, 10)
    lines = out.split("\n")[:25]
    return "\n".join(lines) if lines else "(no matches)"

def service_action(name: str, action: str) -> str:
    """启停服务"""
    if action not in ("start", "stop", "restart"):
        return "❌ action 需为 start/stop/restart"
    out, err, code = _ps(f"{action}-Service '{name}'", 30)
    if code == 0:
        return f"✅ {action} '{name}' 成功"
    return f"❌ {err[:200]}" if err else f"❌ 操作失败"


# ═══════════════════════════════════════
#  事件日志
# ═══════════════════════════════════════

def event_log(log_name: str = "System", max_events: int = 20, filter_keyword: str = "") -> str:
    """读取事件日志"""
    cmd = f"Get-WinEvent -LogName {log_name} -MaxEvents {max_events} | Select-Object TimeCreated, LevelDisplayName, Message | Format-Table -AutoSize -Wrap"
    if filter_keyword:
        cmd = f"Get-WinEvent -LogName {log_name} -MaxEvents {max_events} | Where-Object {{$_.Message -like '*{filter_keyword}*'}} | Select-Object TimeCreated, LevelDisplayName, Message | Format-Table -AutoSize -Wrap"
    out, err, code = _ps(cmd, 15)
    return out[:3000] if out else f"(no events or {err[:100]})"


# ═══════════════════════════════════════
#  计划任务
# ═══════════════════════════════════════

def scheduled_tasks(filter: str = "") -> str:
    """列出计划任务"""
    cmd = 'Get-ScheduledTask | Select-Object TaskName, State, TaskPath | Format-Table -AutoSize'
    if filter:
        cmd = f'Get-ScheduledTask | Where-Object {{$_.TaskName -like "*{filter}*"}} | Select-Object TaskName, State, TaskPath | Format-Table -AutoSize'
    out, err, code = _ps(cmd, 10)
    lines = out.split("\n")[:25]
    return "\n".join(lines) if lines else "(no tasks)"


def create_task(name: str, script_path: str, schedule: str = "daily", time: str = "09:00") -> str:
    """创建 Windows 计划任务"""
    action = f"-Action New-ScheduledTaskAction -Execute 'python' -Argument '{script_path}'"
    trigger = f"-Trigger New-ScheduledTaskTrigger -Daily -At '{time}'"
    if schedule == "hourly":
        trigger = f"-Trigger New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Hours 1)"
    elif schedule == "onstart":
        trigger = f"-Trigger New-ScheduledTaskTrigger -AtStartup"
    
    cmd = f"Register-ScheduledTask -TaskName '{name}' {action} {trigger} -Force"
    out, err, code = _ps(cmd, 10)
    if code == 0:
        return f"✅ 已创建计划任务: {name}"
    return f"❌ {err[:200]}" if err else "❌ 创建失败"


# ═══════════════════════════════════════
#  回收站
# ═══════════════════════════════════════

def recycle_bin_list() -> str:
    """列出回收站内容"""
    out, err, code = _ps("$rb = New-Object -ComObject Shell.Application; $rb.NameSpace(0xa).Items() | Select-Object Name, Size, Path | Format-Table -AutoSize", 10)
    return out[:2000].strip() or "(empty)"

def recycle_bin_empty() -> str:
    """清空回收站"""
    out, err, code = _ps("Clear-RecycleBin -Force", 10)
    return "✅ 回收站已清空" if code == 0 else f"❌ {err[:100]}"


# ═══════════════════════════════════════
#  自启动管理
# ═══════════════════════════════════════

def startup_list() -> str:
    """列出开机自启项"""
    out, err, code = _ps("Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | Format-Table -AutoSize", 10)
    return out[:2000].strip() or "(no startup items)"

def startup_add(name: str, command: str) -> str:
    """添加开机自启"""
    cmd = f'New-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" -Name "{name}" -Value "{command}" -PropertyType String -Force'
    out, err, code = _ps(cmd, 10)
    return f"✅ 已添加自启: {name}" if code == 0 else f"❌ {err[:100]}"

def startup_remove(name: str) -> str:
    """移除开机自启"""
    cmd = f'Remove-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" -Name "{name}" -Force'
    out, err, code = _ps(cmd, 10)
    return f"✅ 已移除自启: {name}" if code == 0 else f"❌ {err[:100]}"


# ═══════════════════════════════════════
#  UAC 提权
# ═══════════════════════════════════════

def is_admin() -> bool:
    """检查是否管理员"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def elevate(script_path: str = "") -> str:
    """请求管理员权限运行脚本"""
    if is_admin():
        return "✅ 已是管理员权限"
    try:
        script = script_path or __file__
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}"', None, 1)
        return "✅ 已请求管理员权限"
    except Exception as e:
        return f"❌ {e}"


# ═══════════════════════════════════════
#  代理感知
# ═══════════════════════════════════════

def get_proxy() -> dict:
    """读取 Windows 代理设置"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
            enabled = winreg.QueryValueEx(key, "ProxyEnable")[0]
            server = winreg.QueryValueEx(key, "ProxyServer")[0] if enabled else ""
            return {"enabled": bool(enabled), "server": server}
    except Exception:
        return {"enabled": False, "server": ""}

def set_proxy(server: str) -> str:
    """设置 Windows 代理"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings", 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1 if server else 0)
            if server:
                winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, server)
        # 通知系统
        _ps('[System.Net.WebRequest]::DefaultWebProxy = New-Object System.Net.WebProxy("' + server + '")', 5)
        return f"✅ 代理已设置为: {server}" if server else "✅ 代理已关闭"
    except Exception as e:
        return f"❌ {e}"


# ═══════════════════════════════════════
#  Windows 版本信息
# ═══════════════════════════════════════

def windows_info() -> str:
    """获取完整 Windows 信息"""
    out, err, code = _ps("Get-ComputerInfo | Select-Object WindowsVersion, WindowsEditionId, WindowsInstallationType, OsHardwareAbstractionLayer, OsArchitecture | Format-List", 10)
    return out.strip() or "Windows info unavailable"
