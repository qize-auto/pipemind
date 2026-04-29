"""PipeMind 系统诊断 — 检查所有子系统状态

用法:
  pipemind doctor              完整诊断
  pipemind doctor --quick      快速检查
  python pipemind_doctor.py    独立运行
"""

import os, sys, datetime, subprocess, json, platform

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")

C = {
    "r": "\033[0m", "b": "\033[1m",
    "green": "\033[92m", "red": "\033[91m",
    "yellow": "\033[93m", "cyan": "\033[96m", "gray": "\033[90m",
}


def _check(label: str, ok: bool, detail: str = "") -> str:
    status = f"{C['green']}✅{C['r']}" if ok else f"{C['red']}❌{C['r']}"
    detail_str = f"  {C['gray']}({detail}){C['r']}" if detail else ""
    return f"  {status} {label}{detail_str}"


def _bold(s):
    return f"{C['b']}{s}{C['r']}"


# ═══════════════════════════════════════════════
# 检查项目
# ═══════════════════════════════════════════════

def check_python() -> list:
    """Python 环境"""
    results = []
    results.append(_check(
        "Python 版本",
        True,
        f"{platform.python_version()} ({platform.architecture()[0]})"
    ))
    # 关键库
    deps = [
        ("flask", "flask"),
        ("pystray", "pystray"),
        ("pillow", "PIL"),
    ]
    for name, mod in deps:
        try:
            __import__(mod)
            results.append(_check(f"  {name}", True))
        except:
            results.append(_check(f"  {name}", False, "pip install"))
    return results


def check_daemon() -> list:
    """守护进程"""
    results = []
    pid_file = os.path.join(MEM_DIR, "_daemon.pid")
    if os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                info = json.load(f)
            uptime = datetime.timedelta(seconds=int(time.time() - info.get("started", 0)))
            results.append(_check(
                "守护进程", True,
                f"PID {info['pid']} · 已运行 {uptime}"
            ))
            # 检查 Web 端口
            port = info.get("port", 9090)
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                results.append(_check(f"  Web 端口 :{port}", True))
            else:
                results.append(_check(f"  Web 端口 :{port}", False, "无法连接"))
            s.close()
        except:
            results.append(_check("守护进程", False, "PID 文件损坏"))
    else:
        results.append(_check("守护进程", False, "未运行"))
    return results


def check_core() -> list:
    """核心模块"""
    results = []
    try:
        from pipemind_core import list_modules, module_stats
        stats = module_stats()
        results.append(_check("核心基座", True, f"{stats['total']} 模块注册"))

        for m in list_modules():
            icon_map = {"running": "🟢", "error": "🔴", "registered": "⚪", "stopped": "⚪"}
            status_icon = icon_map.get(m["status"], "?")
            detail = m.get("started_at", "")[:16] if m.get("started_at") else m["status"]
            ok = m["status"] in ("running", "registered")
            results.append(_check(f"  {status_icon} {m['name']}", ok, detail))
    except Exception as e:
        results.append(_check("核心基座", False, str(e)))
    return results


def check_memory() -> list:
    """记忆系统"""
    results = []
    try:
        import pipemind_memory_evolution as me
        stats = me.get_stats()
        results.append(_check("记忆系统", True, f"{stats['total']} 条知识"))
        for t, c in stats.get("by_type", {}).items():
            results.append(_check(f"  {t}", True, f"{c} 条"))
    except:
        results.append(_check("记忆系统", False, "模块未加载"))
    return results


def check_self_evolution() -> list:
    """本体进化"""
    results = []
    try:
        import pipemind_self_evolution as se
        perf = se.PerformanceTracker.stats(days=7)
        tune = se.SelfTuner.get_config()
        results.append(_check("本体进化", True,
            f"{perf['total']} 对话 · {perf['avg_duration']}s 平均 · {perf['trend']}"))
        results.append(_check(f"  temp={tune['temperature']}", True,
            f"max_tokens={tune['max_tokens']}"))
    except:
        results.append(_check("本体进化", False))
    return results


def check_decision() -> list:
    """决策引擎"""
    results = []
    try:
        import pipemind_decision as dec
        logs = dec.get_decision_log(limit=5)
        recent = len([l for l in logs if l.get("actions")])
        results.append(_check("决策引擎", True, f"最近 {recent} 次行动"))
    except:
        results.append(_check("决策引擎", False))
    return results


def check_daily_learn() -> list:
    """每日学习"""
    results = []
    try:
        import pipemind_daily_learn as dl
        logs = dl.get_learn_log(days=3)
        learned = sum(l.get("total_learned", 0) for l in logs)
        results.append(_check("每日学习", True, f"近3天吸收 {learned} 项"))
    except:
        results.append(_check("每日学习", False))
    return results


def check_disk() -> list:
    """磁盘空间"""
    results = []
    try:
        if sys.platform == "win32":
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(PIPEMIND_DIR), None, None, ctypes.pointer(free_bytes)
            )
            free_gb = free_bytes.value / (1024**3)
            ok = free_gb > 1
            results.append(_check("磁盘空间", ok, f"{free_gb:.1f} GB 剩余"))
        else:
            st = os.statvfs(PIPEMIND_DIR)
            free_gb = (st.f_bavail * st.f_frsize) / (1024**3)
            ok = free_gb > 1
            results.append(_check("磁盘空间", ok, f"{free_gb:.1f} GB 剩余"))
    except:
        results.append(_check("磁盘空间", True, "无法检测"))
    return results


def check_logs() -> list:
    """日志系统"""
    results = []
    try:
        log_dir = os.path.join(MEM_DIR, "_logs")
        if os.path.exists(log_dir):
            count = len(os.listdir(log_dir))
            results.append(_check("日志目录", True, f"{count} 个日志文件"))
        else:
            results.append(_check("日志目录", True, "空（尚未写入）"))
    except:
        results.append(_check("日志目录", False))
    return results


# ═══════════════════════════════════════════════
# 主诊断
# ═══════════════════════════════════════════════

def run_diagnostics(quick: bool = False) -> str:
    """运行全套诊断"""

    checks = [
        ("Python 环境", check_python()),
        ("守护进程", check_daemon()),
        ("核心模块", check_core()),
        ("记忆系统", check_memory()),
        ("本体进化", check_self_evolution()),
        ("决策引擎", check_decision()),
        ("每日学习", check_daily_learn()),
        ("日志系统", check_logs()),
        ("磁盘空间", check_disk()),
    ]

    lines = [
        f"\n  {_bold('🔍 PipeMind 系统诊断')}",
        f"  {C['gray']}{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C['r']}",
        f"  {C['gray']}{PIPEMIND_DIR}{C['r']}\n",
    ]

    total = 0
    passed = 0
    for title, results in checks:
        lines.append(f"  {C['cyan']}▸ {title}{C['r']}")
        for r in results:
            lines.append(r)
        total += len(results)
        passed += sum(1 for r in results if "✅" in r)
        lines.append("")

    # 摘要
    lines.append(f"  {_bold('📊 摘要')}")
    if total == passed:
        lines.append(f"  {C['green']}✅ {passed}/{total} 全部通过{C['r']}")
    else:
        failed = total - passed
        lines.append(f"  {C['yellow']}⚠  {passed}/{total} 通过, {failed} 项异常{C['r']}")

    lines.append("")
    return "\n".join(lines)


def main():
    """CLI 入口"""
    import argparse
    parser = argparse.ArgumentParser(description="PipeMind 系统诊断")
    parser.add_argument("--quick", action="store_true", help="快速检查")
    args = parser.parse_args()
    print(run_diagnostics(args.quick))


if __name__ == "__main__":
    import time
    main()
