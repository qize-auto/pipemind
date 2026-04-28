"""PipeMind — 进化版工具系统（Windows 原生）"""
import os, subprocess, json, datetime, glob, sys, re, platform, time

_PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
_TOOLS = {}

def register(name, fn, description, parameters):
    _TOOLS[name] = {"fn": fn, "desc": description, "params": parameters}

def get_all_schemas() -> list[dict]:
    schemas = []
    for name, tool in _TOOLS.items():
        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool["desc"],
                "parameters": tool["params"]
            }
        })
    return schemas

def execute(name: str, args: dict) -> str:
    if name not in _TOOLS:
        return f"Error: unknown tool '{name}'"
    try:
        result = _TOOLS[name]["fn"](**args)
        return str(result)[:5000]
    except Exception as e:
        return f"Error executing {name}: {e}"

# ═══════════════════════════════════════
#  文件工具
# ═══════════════════════════════════════

def _read_file(path: str, offset: int = 0, limit: int = 200) -> str:
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"File not found: {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        total = len(lines)
        start = offset
        end = min(offset + limit, total)
        result = "".join(lines[start:end])
        info = f"📄 {os.path.basename(path)} ({total} lines, showing {start+1}-{end})\n"
        if end < total:
            result += f"\n... ({total - end} more lines)"
        return info + result
    except UnicodeDecodeError:
        return "(binary file)"
    except Exception as e:
        return f"Error: {e}"

def _write_file(path: str, content: str) -> str:
    path = os.path.expanduser(path)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Written {len(content)} chars to {path}"
    except Exception as e:
        return f"❌ {e}"

def _patch_file(path: str, old_string: str, new_string: str) -> str:
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"File not found: {path}"
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if old_string not in content:
            return f"String not found in file"
        count = content.count(old_string)
        content = content.replace(old_string, new_string)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Replaced {count} occurrence(s) in {path}"
    except Exception as e:
        return f"❌ {e}"

def _list_files(path: str = ".", pattern: str = "*", depth: int = 1) -> str:
    path = os.path.expanduser(path)
    if not os.path.isdir(path):
        return f"Directory not found: {path}"
    try:
        items = []
        for root, dirs, files in os.walk(path):
            level = root.replace(path, "").count(os.sep)
            if level >= depth:
                break
            for f in sorted(files):
                if glob.fnmatch.fnmatch(f, pattern):
                    fp = os.path.join(root, f)
                    sz = os.path.getsize(fp)
                    mt = datetime.datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%m-%d %H:%M")
                    items.append(f"{'  ' * level}📄 {f:<30s} {sz:>8,d}B  {mt}")
            for d in sorted(dirs):
                items.append(f"{'  ' * level}📁 {d}/")
        return "\n".join(items[:60]) if items else "(empty)"
    except Exception as e:
        return f"Error: {e}"

def _search_files(pattern: str, path: str = ".") -> str:
    path = os.path.expanduser(path)
    results = []
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                if pattern.lower() in f.lower():
                    results.append(os.path.join(root, f))
                if len(results) >= 30:
                    break
            if len(results) >= 30:
                break
    except: pass
    return "\n".join(results[:30]) if results else "(no matches)"

# ═══════════════════════════════════════
#  终端工具
# ═══════════════════════════════════════

def _run_terminal(command: str, timeout: int = 30) -> str:
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        output = result.stdout or ""
        if result.stderr:
            output += f"\n⚠ stderr:\n{result.stderr[:2000]}"
        if result.returncode != 0:
            output += f"\n(exit: {result.returncode})"
        if len(output) > 5000:
            output = output[:5000] + f"\n... ({len(output)} chars total)"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "⏱ Command timed out"
    except Exception as e:
        return f"❌ {e}"

# ═══════════════════════════════════════
#  Windows 专有工具
# ═══════════════════════════════════════

def _get_system_info() -> str:
    """获取系统信息"""
    uname = platform.uname()
    info = [
        f"🖥 {uname.system} {uname.release}",
        f"   Version: {uname.version}",
        f"   Machine: {uname.machine}",
        f"   Processor: {uname.processor}",
        f"🐍 Python: {sys.version.split()[0]}",
        f"📂 PipeMind: {_PIPEMIND_DIR}",
        f"🕒 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    return "\n".join(info)

def _get_process_list(filter: str = "") -> str:
    """列出进程"""
    try:
        cmd = f'tasklist /FO CSV /NH'
        if filter:
            cmd += f' | findstr "{filter}"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        lines = result.stdout.strip().split("\n")[:30]
        return "\n".join(lines[:30]) if lines else "(no matches)"
    except Exception as e:
        return f"Error: {e}"

def _clipboard_get() -> str:
    """读取剪贴板"""
    try:
        result = subprocess.run(["powershell", "-Command", "Get-Clipboard"], 
                              capture_output=True, text=True, timeout=5)
        return result.stdout.strip() or "(empty)"
    except Exception as e:
        return f"Error: {e}"

def _clipboard_set(text: str) -> str:
    """写入剪贴板"""
    try:
        # 避免特殊字符问题，写入临时文件再读取
        escaped = text.replace("'", "''")
        cmd = f'powershell -Command "Set-Clipboard -Value \'{escaped}\'"'
        subprocess.run(cmd, shell=True, capture_output=True, timeout=5)
        return f"✅ Copied {len(text)} chars to clipboard"
    except Exception as e:
        return f"Error: {e}"

def _send_notification(title: str, message: str) -> str:
    """发送 Windows 通知"""
    try:
        cmd = f'powershell -Command "New-BurntToastNotification -Text \\"{title}\\", \\"{message}\\""'
        subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
        return "✅ Notification sent"
    except:
        # Fallback: msg command
        try:
            subprocess.run(f'msg * "{title}: {message}"', shell=True, capture_output=True, timeout=5)
            return "✅ Notification sent"
        except:
            return "Notification not supported"

def _get_env_var(name: str) -> str:
    """获取环境变量"""
    val = os.environ.get(name, "")
    return val or f"Environment variable '{name}' not set"

# ═══════════════════════════════════════
#  记忆工具
# ═══════════════════════════════════════

MEM_DIR = os.path.join(_PIPEMIND_DIR, "memory")
os.makedirs(MEM_DIR, exist_ok=True)

def _save_memory(key: str, content: str) -> str:
    safe = re.sub(r'[^\w\-\u4e00-\u9fff]', '_', key)
    path = os.path.join(MEM_DIR, f"{safe}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {key}\n\n{content}\n")
    return f"✅ Saved to memory/{safe}.md"

def _read_memory(key: str) -> str:
    safe = re.sub(r'[^\w\-\u4e00-\u9fff]', '_', key)
    path = os.path.join(MEM_DIR, f"{safe}.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    # Fuzzy search
    for fp in sorted(glob.glob(os.path.join(MEM_DIR, "*.md"))):
        if key.lower() in os.path.basename(fp).lower():
            with open(fp, "r", encoding="utf-8") as f:
                return f.read()
    return f"Memory '{key}' not found"

def _list_memory() -> str:
    files = sorted(glob.glob(os.path.join(MEM_DIR, "*.md")))
    if not files:
        return "(no memories)"
    items = []
    for f in files:
        name = os.path.basename(f)[:-3]
        sz = os.path.getsize(f)
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%m-%d %H:%M")
        items.append(f"  📝 {name:<30s} {sz:>4d}B  {mt}")
    return f"🧠 {len(files)} memories:\n" + "\n".join(items)

def _delete_memory(key: str) -> str:
    safe = re.sub(r'[^\w\-\u4e00-\u9fff]', '_', key)
    path = os.path.join(MEM_DIR, f"{safe}.md")
    if os.path.exists(path):
        os.remove(path)
        return f"Deleted memory/{safe}.md"
    return f"Memory '{key}' not found"

# ═══════════════════════════════════════
#  网络工具
# ═══════════════════════════════════════

def _web_get(url: str, timeout: int = 15) -> str:
    """GET 请求获取网页内容"""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "PipeMind/1.0"})
        resp = urllib.request.urlopen(req, timeout=timeout)
        content = resp.read().decode("utf-8", errors="replace")[:3000]
        return content
    except Exception as e:
        return f"❌ {e}"

# ═══════════════════════════════════════
#  技能工具
# ═══════════════════════════════════════

def _search_skills(query: str) -> str:
    """搜索已安装技能"""
    try:
        import pipemind_skills
        results = pipemind_skills.search(query)
        if not results:
            return f"No skills found matching '{query}'"
        return "\n".join([f"  📦 {s['name']}: {s['description']}" for s in results])
    except Exception as e:
        return f"Error: {e}"

def _list_skills() -> str:
    """列出所有技能"""
    try:
        import pipemind_skills
        skills = pipemind_skills.discover()
        if not skills:
            return "(no skills installed)"
        return "\n".join([f"  📦 {s['name']:<30s} {s['description'][:50]}" for s in skills])
    except Exception as e:
        return f"Error: {e}"

# ═══════════════════════════════════════
#  注册所有工具
# ═══════════════════════════════════════

register("read_file", _read_file, "读取文件内容，支持行号和长度限制",
    {"type":"object","properties":{
        "path":{"type":"string","description":"文件路径"},
        "offset":{"type":"integer","description":"起始行", "default":0},
        "limit":{"type":"integer","description":"读取行数", "default":200}
    },"required":["path"]})

register("write_file", _write_file, "写入文件（覆盖模式）",
    {"type":"object","properties":{
        "path":{"type":"string","description":"文件路径"},
        "content":{"type":"string","description":"文件内容"}
    },"required":["path","content"]})

register("patch_file", _patch_file, "在文件中查找并替换文本",
    {"type":"object","properties":{
        "path":{"type":"string","description":"文件路径"},
        "old_string":{"type":"string","description":"要查找的文本"},
        "new_string":{"type":"string","description":"替换后的文本"}
    },"required":["path","old_string","new_string"]})

register("list_files", _list_files, "列出目录中的文件",
    {"type":"object","properties":{
        "path":{"type":"string","description":"目录路径","default":"."},
        "pattern":{"type":"string","description":"文件通配符","default":"*"},
        "depth":{"type":"integer","description":"递归深度","default":1}
    }})

register("search_files", _search_files, "按名称搜索文件",
    {"type":"object","properties":{
        "pattern":{"type":"string","description":"文件名关键词"},
        "path":{"type":"string","description":"搜索目录","default":"."}
    },"required":["pattern"]})

register("run_terminal", _run_terminal, "执行 Windows 终端命令",
    {"type":"object","properties":{
        "command":{"type":"string","description":"要执行的命令"},
        "timeout":{"type":"integer","description":"超时秒数","default":30}
    },"required":["command"]})

register("get_system_info", _get_system_info, "获取系统信息",
    {"type":"object","properties":{}})

register("get_process_list", _get_process_list, "列出运行中的进程",
    {"type":"object","properties":{
        "filter":{"type":"string","description":"进程名过滤","default":""}
    }})

register("clipboard_get", _clipboard_get, "读取剪贴板内容",
    {"type":"object","properties":{}})

register("clipboard_set", _clipboard_set, "写入文本到剪贴板",
    {"type":"object","properties":{
        "text":{"type":"string","description":"要复制的文本"}
    },"required":["text"]})

register("send_notification", _send_notification, "发送 Windows 通知",
    {"type":"object","properties":{
        "title":{"type":"string","description":"通知标题"},
        "message":{"type":"string","description":"通知内容"}
    },"required":["title","message"]})

register("get_env_var", _get_env_var, "获取环境变量值",
    {"type":"object","properties":{
        "name":{"type":"string","description":"环境变量名"}
    },"required":["name"]})

register("save_memory", _save_memory, "保存记忆到文件",
    {"type":"object","properties":{
        "key":{"type":"string","description":"记忆名称"},
        "content":{"type":"string","description":"记忆内容"}
    },"required":["key","content"]})

register("read_memory", _read_memory, "读取记忆",
    {"type":"object","properties":{
        "key":{"type":"string","description":"记忆名称或关键词"}
    },"required":["key"]})

register("list_memory", _list_memory, "列出所有记忆",
    {"type":"object","properties":{}})

register("delete_memory", _delete_memory, "删除记忆",
    {"type":"object","properties":{
        "key":{"type":"string","description":"记忆名称"}
    },"required":["key"]})

register("web_get", _web_get, "发送 HTTP GET 请求获取网页内容",
    {"type":"object","properties":{
        "url":{"type":"string","description":"网址"},
        "timeout":{"type":"integer","description":"超时秒数","default":15}
    },"required":["url"]})

register("list_skills", _list_skills, "列出所有已安装的技能",
    {"type":"object","properties":{}})

register("search_skills", _search_skills, "搜索已安装的技能",
    {"type":"object","properties":{
        "query":{"type":"string","description":"搜索关键词"}
    },"required":["query"]})

# ═══════════════════════════════════════
#  进化能力工具（v3.0）
# ═══════════════════════════════════════

def _take_screenshot() -> str:
    """截取屏幕"""
    try:
        import pipemind_vision as v
        return v.screenshot()
    except Exception as e:
        return f"Vision module: {e}"

def _analyze_image(path: str, question: str = "描述这张图片") -> str:
    """分析图片"""
    try:
        import pipemind_vision as v
        return v.analyze_image(path, question)
    except Exception as e:
        return f"Vision module: {e}"

def _speak_text(text: str) -> str:
    """朗读文本"""
    try:
        import pipemind_voice as v
        return v.speak(text)
    except Exception as e:
        return f"Voice module: {e}"

def _write_diary(content: str, emotion: str = "") -> str:
    """写日记"""
    try:
        import pipemind_diary as d
        d.write_entry(content, emotion)
        return f"✅ 日记已记录"
    except Exception as e:
        return f"Diary module: {e}"

def _get_diary(days: int = 7) -> str:
    """查看日记"""
    try:
        import pipemind_diary as d
        return d.get_recent(days)
    except Exception as e:
        return f"Diary module: {e}"

def _get_growth() -> str:
    """成长报告"""
    try:
        import pipemind_diary as d
        return d.get_growth_report()
    except Exception as e:
        return f"Diary module: {e}"

def _get_mood() -> str:
    """当前情绪"""
    try:
        import pipemind_diary as d
        return d.get_mood()
    except Exception as e:
        return f"Mood module: {e}"

def _memory_search(query: str) -> str:
    """语义搜索记忆"""
    try:
        import pipemind_memory_plus as mp
        return mp.search_text(query)
    except Exception as e:
        return f"Memory module: {e}"

def _memory_list() -> str:
    """列出所有记忆"""
    try:
        import pipemind_memory_plus as mp
        return mp.list_all()
    except Exception as e:
        return f"Memory module: {e}"

def _add_monitor(name: str, url: str, keyword: str = "", interval: int = 3600) -> str:
    """添加网页监控"""
    try:
        import pipemind_monitor as m
        return m.add_monitor(name, url, keyword, interval)
    except Exception as e:
        return f"Monitor module: {e}"

def _list_monitors() -> str:
    """列出监控"""
    try:
        import pipemind_monitor as m
        return m.list_monitors()
    except Exception as e:
        return f"Monitor module: {e}"

def _add_task(name: str, command: str, schedule: str = "daily") -> str:
    """添加定时任务"""
    try:
        import pipemind_monitor as m
        return m.add_task(name, command, schedule)
    except Exception as e:
        return f"Task module: {e}"

def _self_test() -> str:
    """自检"""
    try:
        import pipemind_self_test as st
        return st.test_report()
    except Exception as e:
        return f"Self-test: {e}"

def _build_tool(name: str, description: str) -> str:
    """根据描述创建新工具"""
    try:
        import pipemind_self_test as st
        return st.create_tool_from_description(name, description)
    except Exception as e:
        return f"Builder: {e}"

# ── 注册进化工具 ──
register("screenshot", _take_screenshot, "截取当前屏幕截图",
    {"type":"object","properties":{}})

register("analyze_image", _analyze_image, "分析图片内容（需多模态模型）",
    {"type":"object","properties":{
        "path":{"type":"string","description":"图片路径"},
        "question":{"type":"string","description":"提问","default":"描述这张图片"}
    },"required":["path"]})

register("speak", _speak_text, "用语音朗读文本",
    {"type":"object","properties":{
        "text":{"type":"string","description":"要朗读的文本"}
    },"required":["text"]})

register("write_diary", _write_diary, "写日记记录想法和感受",
    {"type":"object","properties":{
        "content":{"type":"string","description":"日记内容"},
        "emotion":{"type":"string","description":"情绪","default":""}
    },"required":["content"]})

register("read_diary", _get_diary, "查看近期日记",
    {"type":"object","properties":{
        "days":{"type":"integer","description":"最近几天","default":7}
    }})

register("growth_report", _get_growth, "查看成长报告",
    {"type":"object","properties":{}})

register("get_mood", _get_mood, "查看当前情绪状态",
    {"type":"object","properties":{}})

register("memory_search", _memory_search, "语义搜索记忆",
    {"type":"object","properties":{
        "query":{"type":"string","description":"搜索关键词"}
    },"required":["query"]})

register("memory_list", _memory_list, "列出所有记忆",
    {"type":"object","properties":{}})

register("add_monitor", _add_monitor, "添加网页监控",
    {"type":"object","properties":{
        "name":{"type":"string","description":"监控名称"},
        "url":{"type":"string","description":"要监控的网址"},
        "keyword":{"type":"string","description":"关键词","default":""},
        "interval":{"type":"integer","description":"检查间隔(秒)","default":3600}
    },"required":["name","url"]})

register("list_monitors", _list_monitors, "列出所有监控",
    {"type":"object","properties":{}})

register("add_task", _add_task, "添加定时任务",
    {"type":"object","properties":{
        "name":{"type":"string","description":"任务名"},
        "command":{"type":"string","description":"要执行的命令"},
        "schedule":{"type":"string","description":"调度: daily/hourly/once","default":"daily"}
    },"required":["name","command"]})

register("self_test", _self_test, "运行全面自检",
    {"type":"object","properties":{}})

register("build_tool", _build_tool, "根据描述自动创建新工具",
    {"type":"object","properties":{
        "name":{"type":"string","description":"工具名"},
        "description":{"type":"string","description":"工具功能描述"}
    },"required":["name","description"]})

# ═══════════════════════════════════════
#  代谢系统工具
# ═══════════════════════════════════════

def _get_health() -> str:
    try:
        import pipemind_metabolism as m
        return m.get_system_health()
    except: return "Metabolism module unavailable"

def _get_perf() -> str:
    try:
        import pipemind_metabolism as m
        return m.perf_report()
    except: return "Perf module unavailable"

def _run_cleanup() -> str:
    try:
        import pipemind_metabolism as m
        r = m.auto_cleanup(force=True)
        return f"🧹 清理完成: 删除 {r['deleted_files']} 文件, 释放 {r['freed_bytes']/1024:.0f}KB"
    except: return "Cleanup module unavailable"

def _log_perf(action: str, duration: float):
    try:
        import pipemind_metabolism as m
        m.log_perf(action, duration)
    except: pass

register("health_check", _get_health, "检查系统健康度",
    {"type":"object","properties":{}})

register("perf_report", _get_perf, "查看性能报告",
    {"type":"object","properties":{}})

register("cleanup", _run_cleanup, "运行自动清理，释放空间",
    {"type":"object","properties":{}})

# ═══════════════════════════════════════
#  精准执行引擎工具
# ═══════════════════════════════════════

def _get_accuracy() -> str:
    try:
        import pipemind_precision as pr
        return pr.accuracy_report()
    except: return "Precision module unavailable"

def _register_pattern(name: str, solution: str, signals: str) -> str:
    try:
        import pipemind_precision as pr
        sig_list = [s.strip() for s in signals.split(",")]
        pid = pr.register_pattern(name, sig_list, solution)
        return f"✅ 已注册模式 '{name}' (ID: {pid})"
    except Exception as e:
        return f"❌ {e}"

def _find_solution(problem: str) -> str:
    try:
        import pipemind_precision as pr
        sol = pr.find_solution(problem)
        if sol:
            return f"📋 找到方案: {sol['approach']}\n步骤: {chr(10).join(f'  {i+1}. {s}' for i, s in enumerate(sol['steps'][:5]))}"
        return "🔍 未找到匹配方案"
    except: return "Precision module unavailable"

register("accuracy_report", _get_accuracy, "查看精准度报告",
    {"type":"object","properties":{}})

register("register_pattern", _register_pattern, "注册一个成功模式供后续复用",
    {"type":"object","properties":{
        "name":{"type":"string","description":"模式名称"},
        "solution":{"type":"string","description":"经过验证的解决方案"},
        "signals":{"type":"string","description":"触发信号关键词（逗号分隔）"}
    },"required":["name","solution","signals"]})

register("find_solution", _find_solution, "查找已知问题的解决方案",
    {"type":"object","properties":{
        "problem":{"type":"string","description":"问题描述"}
    },"required":["problem"]})

# ═══════════════════════════════════════
#  Windows 深度适配工具
# ═══════════════════════════════════════

def _reg_read(key: str, value: str = "") -> str:
    try: import pipemind_windows_deep as w; return w.reg_read(key, value)
    except: return "Module unavailable"

def _reg_write(key: str, name: str, value: str) -> str:
    try: import pipemind_windows_deep as w; return w.reg_write(key, name, value)
    except: return "Module unavailable"

def _service_list(filter: str = "") -> str:
    try: import pipemind_windows_deep as w; return w.service_list(filter)
    except: return "Module unavailable"

def _service_action(name: str, action: str) -> str:
    try: import pipemind_windows_deep as w; return w.service_action(name, action)
    except: return "Module unavailable"

def _event_log(log: str = "System", max: int = 20) -> str:
    try: import pipemind_windows_deep as w; return w.event_log(log, max)
    except: return "Module unavailable"

def _task_list(filter: str = "") -> str:
    try: import pipemind_windows_deep as w; return w.scheduled_tasks(filter)
    except: return "Module unavailable"

def _bin_list() -> str:
    try: import pipemind_windows_deep as w; return w.recycle_bin_list()
    except: return "Module unavailable"

def _bin_empty() -> str:
    try: import pipemind_windows_deep as w; return w.recycle_bin_empty()
    except: return "Module unavailable"

def _startup_list() -> str:
    try: import pipemind_windows_deep as w; return w.startup_list()
    except: return "Module unavailable"

def _win_info() -> str:
    try: import pipemind_windows_deep as w; return w.windows_info()
    except: return "Module unavailable"

register("reg_read", _reg_read, "读取 Windows 注册表",
    {"type":"object","properties":{"key":{"type":"string","description":"键路径如 HKLM\\Software\\..."},"value":{"type":"string","description":"值名称","default":""}},"required":["key"]})
register("reg_write", _reg_write, "写入 Windows 注册表",
    {"type":"object","properties":{"key":{"type":"string","description":"键路径"},"name":{"type":"string","description":"值名称"},"value":{"type":"string","description":"值内容"}},"required":["key","name","value"]})
register("service_list", _service_list, "列出 Windows 服务",
    {"type":"object","properties":{"filter":{"type":"string","description":"筛选关键词","default":""}}})
register("service_action", _service_action, "启停 Windows 服务",
    {"type":"object","properties":{"name":{"type":"string","description":"服务名"},"action":{"type":"string","description":"start/stop/restart"}},"required":["name","action"]})
register("event_log", _event_log, "读取 Windows 事件日志",
    {"type":"object","properties":{"log":{"type":"string","description":"日志名: System/Application/Security","default":"System"},"max":{"type":"integer","description":"最大条数","default":20}}})
register("task_list", _task_list, "列出计划任务",
    {"type":"object","properties":{"filter":{"type":"string","description":"筛选关键词","default":""}}})
register("recycle_bin", _bin_list, "列出回收站内容",
    {"type":"object","properties":{}})
register("empty_bin", _bin_empty, "清空回收站",
    {"type":"object","properties":{}})
register("startup_list", _startup_list, "列出开机自启项",
    {"type":"object","properties":{}})
register("windows_info", _win_info, "获取 Windows 系统信息",
    {"type":"object","properties":{}})

# ═══════════════════════════════════════
#  安全韧性工具
# ═══════════════════════════════════════

def _audit(hours: int = 24) -> str:
    try: import pipemind_security as sec; return sec.audit_report(hours)
    except: return "Module unavailable"

def _secure_key() -> str:
    try: import pipemind_security as sec; return sec.secure_config()
    except: return "Module unavailable"

def _backup() -> str:
    try: import pipemind_security as sec; return sec.auto_backup()
    except: return "Module unavailable"

def _list_backups() -> str:
    try: import pipemind_security as sec; return sec.list_backups()
    except: return "Module unavailable"

def _reload() -> str:
    try: import pipemind_security as sec; return sec.hot_reload()
    except: return "Module unavailable"

def _crash() -> str:
    try: import pipemind_security as sec; return sec.get_last_crash()
    except: return "Module unavailable"

register("audit_log", _audit, "查看操作审计日志",
    {"type":"object","properties":{"hours":{"type":"integer","description":"最近几小时","default":24}}})
register("secure_config", _secure_key, "加密存储 API Key",
    {"type":"object","properties":{}})
register("backup", _backup, "备份关键文件",
    {"type":"object","properties":{}})
register("list_backups", _list_backups, "列出备份",
    {"type":"object","properties":{}})
register("hot_reload", _reload, "热重载所有模块",
    {"type":"object","properties":{}})
register("crash_report", _crash, "查看崩溃记录",
    {"type":"object","properties":{}})
