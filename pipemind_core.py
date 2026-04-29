"""PipeMind 核心基座 — 统一日志、错误处理、模块注册表

引入方式:
  from pipemind_core import log, err, register_module, get_module, PIPEMIND_DIR, MEM_DIR

替代:
  try: except: pass  →  err.safe("模块名", fn)
  print(f"  ✅ ...") →  log.info("模块名", "...")
  PIPEMIND_DIR = ... →  直接用 core 的常量
"""

import os, sys, datetime, traceback, json, time

# ═══════════════════════════════════════════════
# 路径常量（所有模块统一用这个）
# ═══════════════════════════════════════════════

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")
SKILLS_DIR = os.path.join(PIPEMIND_DIR, "skills")
LOG_DIR = os.path.join(MEM_DIR, "_logs")


# ═══════════════════════════════════════════════
# 统一日志
# ═══════════════════════════════════════════════

_LOG_BUFFER = []       # 内存日志（供 Web 查看）
_MAX_LOG_BUFFER = 500
_LOG_FILE = None       # 按需启用文件日志


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


class Logger:
    """结构化日志

    用法:
        log = Logger("mymodule")
        log.info("完成了 N 件事")
        log.warn("磁盘快满了")
        log.error("连接失败", exc=e)
    """

    LEVELS = {"debug": 0, "info": 1, "warn": 2, "error": 3}

    def __init__(self, name: str):
        self.name = name

    def _log(self, level: str, message: str, exc=None):
        entry = {
            "time": datetime.datetime.now().isoformat(),
            "level": level,
            "module": self.name,
            "message": message,
        }
        if exc:
            entry["traceback"] = traceback.format_exc() if isinstance(exc, BaseException) else str(exc)

        # 内存缓存
        _LOG_BUFFER.append(entry)
        if len(_LOG_BUFFER) > _MAX_LOG_BUFFER:
            _LOG_BUFFER[:50] = []

        # 控制台输出
        icon = {"debug": "🔍", "info": "  ·", "warn": "⚠", "error": "❌"}.get(level, "·")
        if level == "error" and exc:
            print(f"  {icon} [{self.name}] {message}")
            print(f"     {traceback.format_exc() if isinstance(exc, BaseException) else exc}")
        elif level != "debug":
            print(f"  {icon} [{self.name}] {message}")

        # 文件日志（按天）
        try:
            _ensure_log_dir()
            today = datetime.date.today().isoformat()
            log_file = os.path.join(LOG_DIR, f"{today}.log")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except:
            pass

    def debug(self, msg, **kw):
        self._log("debug", msg, **kw)

    def info(self, msg, **kw):
        self._log("info", msg, **kw)

    def warn(self, msg, **kw):
        self._log("warn", msg, **kw)

    def error(self, msg, **kw):
        self._log("error", msg, **kw)


# ── 快捷入口（兼容简单场景）─

def log_info(module, msg):
    Logger(module).info(msg)


def log_warn(module, msg):
    Logger(module).warn(msg)


def log_error(module, msg, exc=None):
    Logger(module).error(msg, exc=exc)


# ═══════════════════════════════════════════════
# 统一安全执行
# ═══════════════════════════════════════════════

def safe(module_name: str, fn, fallback=None, silent: bool = False):
    """安全执行函数，捕获所有异常并记录

    Args:
        module_name: 模块名（日志用）
        fn: 要执行的函数
        fallback: 失败时的返回值
        silent: True 则不输出到控制台（仅写日志）
    Returns:
        fn 的返回值，或 fallback
    """
    try:
        return fn()
    except Exception as e:
        if not silent:
            log_error(module_name, f"执行失败: {e}", exc=e)
        return fallback


# ═══════════════════════════════════════════════
# 模块注册表
# ═══════════════════════════════════════════════

_registry = {}  # name → {module, status, started_at}

log = Logger("core")


def register_module(name: str, start_fn=None, stop_fn=None, deps: list = None) -> dict:
    """注册一个模块

    Args:
        name: 模块名
        start_fn: 启动函数（可选）
        stop_fn: 停止函数（可选）
        deps: 依赖的模块名列表
    Returns:
        模块条目
    """
    entry = {
        "name": name,
        "start_fn": start_fn,
        "stop_fn": stop_fn,
        "deps": deps or [],
        "status": "registered",
        "started_at": None,
        "errors": 0,
    }
    _registry[name] = entry
    log.info(f"模块注册: {name}")
    return entry


def get_module(name: str) -> dict | None:
    """获取已注册的模块"""
    return _registry.get(name)


def start_module(name: str) -> bool:
    """启动一个已注册的模块"""
    entry = _registry.get(name)
    if not entry:
        log.error(f"模块未注册: {name}")
        return False
    if entry["status"] == "running":
        return True
    if entry["start_fn"]:
        try:
            entry["start_fn"]()
            entry["status"] = "running"
            entry["started_at"] = datetime.datetime.now().isoformat()
            log.info(f"模块启动: {name}")
            return True
        except Exception as e:
            entry["status"] = "error"
            entry["errors"] += 1
            log.error(f"模块启动失败: {name}", exc=e)
            return False
    entry["status"] = "running"
    return True


def stop_module(name: str) -> bool:
    """停止一个模块"""
    entry = _registry.get(name)
    if not entry:
        return False
    if entry["stop_fn"]:
        try:
            entry["stop_fn"]()
        except:
            pass
    entry["status"] = "stopped"
    return True


def list_modules() -> list[dict]:
    """列出所有已注册模块"""
    return [
        {
            "name": e["name"],
            "status": e["status"],
            "errors": e["errors"],
            "started_at": e["started_at"],
            "deps": e["deps"],
        }
        for e in _registry.values()
    ]


def module_stats() -> dict:
    """模块系统统计"""
    entries = list_modules()
    return {
        "total": len(entries),
        "running": sum(1 for e in entries if e["status"] == "running"),
        "errored": sum(1 for e in entries if e["errors"] > 0),
        "stopped": sum(1 for e in entries if e["status"] == "stopped"),
    }


# ═══════════════════════════════════════════════
# 日志查询
# ═══════════════════════════════════════════════

def get_recent_logs(limit=50, level=None, module=None) -> list:
    """获取最近日志"""
    logs = list(_LOG_BUFFER)
    if level:
        logs = [l for l in logs if l["level"] == level]
    if module:
        logs = [l for l in logs if l["module"] == module]
    return logs[-limit:]


def get_today_log_file() -> str | None:
    """获取今日日志文件路径"""
    today = datetime.date.today().isoformat()
    path = os.path.join(LOG_DIR, f"{today}.log")
    if os.path.exists(path):
        return path
    return None


# ═══════════════════════════════════════════════
# 初始化
# ═══════════════════════════════════════════════

def init():
    """初始化核心基座"""
    _ensure_log_dir()
    register_module("core")
    log.info("PipeMind Core 初始化完成")
    log.info(f"  日志目录: {LOG_DIR}")
