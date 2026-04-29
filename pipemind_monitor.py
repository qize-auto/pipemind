"""PipeMind — 网络监控 + 后台任务调度"""
from pipemind_core import PIPEMIND_DIR, MEM_DIR
import json, os, datetime, urllib.request, re, time, threading, queue

MONITOR_FILE = os.path.join(PIPEMIND_DIR, "memory", "_monitors.json")
TASK_FILE = os.path.join(PIPEMIND_DIR, "memory", "_tasks.json")


# ── 监控器 ──

def _load_monitors() -> list:
    if os.path.exists(MONITOR_FILE):
        try:
            with open(MONITOR_FILE, "r") as f:
                return json.load(f)
        except Exception: pass
    return []

def _save_monitors(monitors: list):
    os.makedirs(os.path.dirname(MONITOR_FILE), exist_ok=True)
    with open(MONITOR_FILE, "w") as f:
        json.dump(monitors, f, ensure_ascii=False, indent=2)

def add_monitor(name: str, url: str, keyword: str = "", interval: int = 3600) -> str:
    """添加监控"""
    monitors = _load_monitors()
    monitors.append({
        "name": name, "url": url, "keyword": keyword,
        "interval": interval, "last_check": "", "last_result": "",
        "created": datetime.datetime.now().isoformat()
    })
    _save_monitors(monitors)
    return f"✅ 已添加监控: {name} (每 {interval//60} 分钟检查一次)"

def remove_monitor(name: str) -> str:
    monitors = _load_monitors()
    before = len(monitors)
    monitors = [m for m in monitors if m["name"] != name]
    if len(monitors) < before:
        _save_monitors(monitors)
        return f"✅ 已移除监控: {name}"
    return f"❌ 未找到: {name}"

def list_monitors() -> str:
    monitors = _load_monitors()
    if not monitors:
        return "(无活跃监控)"
    lines = ["📡 活跃监控:"]
    for m in monitors:
        status = "✅" if m["last_result"] else "⏳"
        lines.append(f"  {status} {m['name']} — {m['url'][:50]}")
    return "\n".join(lines)

def check_monitors() -> list[dict]:
    """检查所有监控，返回有变化的"""
    monitors = _load_monitors()
    changes = []
    for m in monitors:
        try:
            req = urllib.request.Request(m["url"], headers={"User-Agent": "PipeMind/1.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            content = resp.read().decode("utf-8", errors="replace")[:5000]
            
            if m["keyword"] and m["keyword"] in content:
                changes.append({"name": m["name"], "found": m["keyword"]})
            
            m["last_check"] = datetime.datetime.now().isoformat()
            m["last_result"] = "ok"
        except Exception as e:
            m["last_result"] = str(e)[:100]
        
    _save_monitors(monitors)
    return changes


# ── 后台任务 ──

def _load_tasks() -> list:
    if os.path.exists(TASK_FILE):
        try:
            with open(TASK_FILE, "r") as f:
                return json.load(f)
        except Exception: pass
    return []

def _save_tasks(tasks: list):
    os.makedirs(os.path.dirname(TASK_FILE), exist_ok=True)
    with open(TASK_FILE, "w") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def add_task(name: str, command: str, schedule: str = "daily") -> str:
    """添加定时任务"""
    tasks = _load_tasks()
    tasks.append({
        "name": name, "command": command, "schedule": schedule,
        "last_run": "", "status": "pending",
        "created": datetime.datetime.now().isoformat()
    })
    _save_tasks(tasks)
    return f"✅ 已添加任务: {name} ({schedule})"

def remove_task(name: str) -> str:
    tasks = _load_tasks()
    before = len(tasks)
    tasks = [t for t in tasks if t["name"] != name]
    if len(tasks) < before:
        _save_tasks(tasks)
        return f"✅ 已移除任务: {name}"
    return f"❌ 未找到: {name}"

def list_tasks() -> str:
    tasks = _load_tasks()
    if not tasks:
        return "(无定时任务)"
    lines = ["⏰ 定时任务:"]
    for t in tasks:
        status = "✅" if t["status"] == "done" else "⏳"
        lines.append(f"  {status} {t['name']} ({t['schedule']})")
    return "\n".join(lines)
