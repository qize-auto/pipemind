"""PipeMind 后台守护进程 — 常驻内存，Web 控制台 + 远程管理

架构：
  pipemind.py --daemon  →  启动本模块  →  持久化 PipeMind + Web 服务器
  pipemind.py --tray    →  启动托盘    →  连接守护进程 HTTP API
  pipemind.py --stop    →  停止守护进程
"""

import os, sys, json, time, signal, threading, atexit, subprocess, datetime

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(PIPEMIND_DIR, "memory")
PID_FILE = os.path.join(MEMORY_DIR, "_daemon.pid")

_agent = None
_running = False


# ── PipeMind 持久化实例 ────────────────────────────

def get_agent():
    """获取/创建持久化的 PipeMind 实例（跨 Web 请求复用）"""
    global _agent
    if _agent is None:
        sys.path.insert(0, PIPEMIND_DIR)
        import pipemind
        print("  🧠 初始化 PipeMind 实例...")
        _agent = pipemind.PipeMind()
        print(f"  ✅ 实例就绪 (会话: {_agent.session_id})")
    return _agent


def reset_agent():
    """重置实例（/restart 时调用）"""
    global _agent
    if _agent is not None:
        try:
            _agent.save()
        except:
            pass
    _agent = None


# ── PID 管理 ──────────────────────────────────────

def _save_pid(port):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(PID_FILE, "w") as f:
        json.dump({
            "pid": os.getpid(),
            "port": port,
            "started": time.time(),
        }, f)


def _cleanup_pid():
    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except:
            pass


def is_running():
    """检查守护进程是否存活"""
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE) as f:
            info = json.load(f)
        # 检查进程是否存在
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x400, False, info["pid"])
            if handle:
                kernel32.CloseHandle(handle)
                return True
        else:
            os.kill(info["pid"], 0)
            return True
    except:
        pass
    _cleanup_pid()
    return False


# ── 生命周期管理 ──────────────────────────────────

def stop_daemon():
    """停止正在运行的守护进程"""
    if not os.path.exists(PID_FILE):
        return False, "未找到 PID 文件（守护进程未运行）"
    try:
        with open(PID_FILE) as f:
            info = json.load(f)
        # 通过 HTTP 发送停止请求（优雅关闭）
        try:
            req = urllib.request.Request(
                f"http://localhost:{info['port']}/api/daemon/stop",
                data=b"{}",
                headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=5)
            time.sleep(1)
            return True, "已发送停止信号"
        except:
            # HTTP 不通，直接杀进程
            if sys.platform == "win32":
                os.system(f"taskkill /F /PID {info['pid']} >nul 2>&1")
            else:
                os.kill(info["pid"], signal.SIGTERM)
            _cleanup_pid()
            return True, "已强制终止"
    except Exception as e:
        return False, str(e)


def start_daemon(port=9090, hidden=True):
    """以子进程方式启动守护进程"""
    if is_running():
        return True, "守护进程已在运行"

    script = os.path.join(PIPEMIND_DIR, "pipemind.py")
    cmd = [sys.executable or "python", script, "--daemon", "--port", str(port)]

    if hidden and sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        proc = subprocess.Popen(
            cmd,
            startupinfo=startupinfo,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
    else:
        proc = subprocess.Popen(cmd)

    # 等待就绪（最多 15 秒）
    for i in range(30):
        time.sleep(0.5)
        if is_running():
            return True, f"守护进程已启动 (PID: {proc.pid}, 端口: {port})"

    return False, "启动超时"


def run_server(port=9090):
    """启动 Web 服务器（主线程阻塞）"""
    global _running
    _running = True

    # 初始化持久化实例
    agent = get_agent()

    # Patch web 模块，注入持久化 agent
    import pipemind_web
    pipemind_web._daemon_agent = agent
    pipemind_web._daemon_port = port

    _save_pid(port)
    atexit.register(_cleanup_pid)

    print(f"\n  🌐 PipeMind 守护进程")
    print(f"     http://localhost:{port}")
    print(f"     PID: {os.getpid()}")
    print(f"     🧠 记忆进化: 每日凌晨聚合")
    print(f"     🌉 弈辛守护: 每5分钟健康检查")
    print(f"     🧬 本体进化: 每日凌晨自调优")
    print(f"     Ctrl+C 停止\n")

    # ── 启动记忆进化定时器 ──
    _start_consolidation_timer()

    # ── 启动弈辛健康监控 ──
    try:
        import pipemind_wsl_bridge as wsl
        monitor = wsl.get_monitor()
        monitor.start()
        print(f"     ✅ 弈辛监控已启动")
    except Exception as e:
        print(f"     ⚠ 弈辛监控启动失败: {e}")

    # 启动 Web 服务器（阻塞）
    pipemind_web.run(port=port, daemon_mode=True)

    _cleanup_pid()
    _running = False


def _start_consolidation_timer():
    """启动每日聚合定时器（后台线程，每小时检查一次）"""
    def _timer_loop():
        last_date = None
        while _running:
            try:
                now = datetime.datetime.now()
                today = now.strftime("%Y-%m-%d")

                # 凌晨 3:00-3:05 之间执行，每天一次
                if now.hour == 3 and 0 <= now.minute < 5 and last_date != today:
                    last_date = today
                    try:
                        import pipemind_memory_evolution as evo
                        print(f"  🧠 开始每日记忆聚合 ({today})...")
                        result = evo.daily_consolidate()
                        print(f"  ✅ 聚合完成: {result['sessions']} 会话, "
                              f"{result['knowledge']} 知识, {result['archived']} 归档")
                    except Exception as e:
                        print(f"  ⚠ 聚合失败: {e}")

                # 凌晨 4:00 生成进化日报 + 自调优
                if now.hour == 4 and 0 <= now.minute < 5 and last_date != today:
                    try:
                        import pipemind_self_evolution as se
                        report = se.generate_daily_report()
                        print(f"  🧬 进化日报已生成: {report['performance']['total']} 对话, "
                              f"{'; '.join(report['tuning']['changes']) or '无调优'}")
                    except Exception as e:
                        print(f"  ⚠ 进化日报生成失败: {e}")
            except:
                pass
            time.sleep(3600)  # 每小时检查一次

    t = threading.Thread(target=_timer_loop, daemon=True)
    t.start()


if __name__ == "__main__":
    # 独立运行
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9090)
    args = parser.parse_args()
    run_server(args.port)
else:
    import urllib.request, urllib.error
