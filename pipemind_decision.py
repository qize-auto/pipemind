"""PipeMind 决策引擎 — 自治行动，不只是定时执行

不再等固定时间点做事。每 30 分钟评估一次系统状态，决定要不要行动。

决策逻辑:
  1. 记忆 > 400 条 → 建议归档或精简
  2. 错误率 > 20% → 自动诊断并生成 lesson
  3. 弈辛进程未运行 → 自动重启
  4. 超过 4 小时无对话 → 执行维护
  5. 学习管道有未处理的新知识 → 执行学习
  6. 知识库有高频未归档旧知识 → 主动归档

数据:
  memory/_decision_log.json — 决策历史
"""

from pipemind_core import PIPEMIND_DIR, MEM_DIR
import os, json, datetime, time, threading, sys

DECISION_LOG = os.path.join(MEM_DIR, "_decision_log.json")
INTERVAL = 1800  # 30 分钟

_running = False
_thread = None


# ═══════════════════════════════════════════════
# 1. 状态扫描
# ═══════════════════════════════════════════════

def scan() -> dict:
    """收集所有子系统状态"""
    state = {
        "time": datetime.datetime.now().isoformat(),
        "memory": _scan_memory(),
        "performance": _scan_performance(),
        "yixin": _scan_yixin(),
        "learning": _scan_learning(),
        "chronicle": _scan_chronicle(),
        "system": _scan_system(),
    }
    return state


def _scan_memory() -> dict:
    """记忆系统状态"""
    try:
        import pipemind_memory_evolution as me
        stats = me.get_stats()
        return {
            "total": stats.get("total", 0),
            "by_type": stats.get("by_type", {}),
            "top_importance": stats.get("avg_importance", 0),
        }
    except Exception:
        return {"total": 0}


def _scan_performance() -> dict:
    """性能状态"""
    try:
        import pipemind_self_evolution as se
        p = se.PerformanceTracker.stats(days=1)
        return {
            "today_conversations": p.get("total", 0),
            "avg_duration": p.get("avg_duration", 0),
            "error_rate": p.get("error_rate", 0),
            "trend": p.get("trend", "unknown"),
        }
    except Exception:
        return {}


def _scan_yixin() -> dict:
    """弈辛状态"""
    try:
        import pipemind_wsl_bridge as wsl
        s = wsl.get_monitor().status
        return {
            "running": s.get("running", False),
            "connected": s.get("connected", False),
            "model": s.get("model", "?"),
            "fail_count": s.get("fail_count", 0),
        }
    except Exception:
        return {"running": False}


def _scan_learning() -> dict:
    """学习系统状态"""
    try:
        import pipemind_daily_learn as dl
        logs = dl.get_learn_log(days=1)
        return {
            "today_learned": logs[0].get("total_learned", 0) if logs else 0,
            "has_pending": bool(logs),
        }
    except Exception:
        return {"today_learned": 0}


def _scan_chronicle() -> dict:
    """生命编年史状态"""
    try:
        import pipemind_chronicle as ch
        signals = ch.get_improvement_signals()
        summary = ch.get_summary()
        return {
            "trend": signals.get("trend", "stable"),
            "plateau": signals.get("plateau_metrics", []),
            "declining": signals.get("declining_metrics", []),
            "age_days": summary.get("age_days", 0),
        }
    except Exception:
        return {"trend": "unknown", "plateau": [], "declining": []}


def _scan_system() -> dict:
    """系统基础状态"""
    import os, time
    # 检查 daemon 启动后经过的时间
    pid_file = os.path.join(MEM_DIR, "_daemon.pid")
    uptime = 0
    if os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                info = json.load(f)
            uptime = time.time() - info.get("started", time.time())
        except Exception:
            pass
    return {
        "uptime_hours": round(uptime / 3600, 1) if uptime > 0 else 0,
    }


# ═══════════════════════════════════════════════
# 2. 分析 & 决策
# ═══════════════════════════════════════════════

def analyze(state: dict) -> list[dict]:
    """分析系统状态，生成待办事项"""
    decisions = []

    # 决策 1: 记忆过多 → 建议归档
    mem = state.get("memory", {})
    if mem.get("total", 0) > 400:
        decisions.append({
            "priority": "medium",
            "action": "archive_knowledge",
            "reason": f"知识库已达 {mem['total']} 条，超过建议上限 400",
            "handler": "_handle_archive",
        })

    # 决策 2: 错误率过高 → 诊断
    perf = state.get("performance", {})
    if perf.get("error_rate", 0) > 0.2 and perf.get("today_conversations", 0) > 3:
        decisions.append({
            "priority": "high",
            "action": "diagnose_errors",
            "reason": f"今日错误率 {perf['error_rate']:.0%}，高于阈值 20%",
            "handler": "_handle_diagnose",
        })

    # 决策 3: 弈辛挂了 → 重启
    yixin = state.get("yixin", {})
    if not yixin.get("running", True) and yixin.get("fail_count", 0) > 1:
        decisions.append({
            "priority": "high",
            "action": "restart_yixin",
            "reason": "弈辛进程未运行，连续失败 {yixin['fail_count']} 次",
            "handler": "_handle_yixin_restart",
        })

    # 决策 4: 长时间无对话 → 维护
    perf = state.get("performance", {})
    if perf.get("today_conversations", 1) == 0:
        sys_state = state.get("system", {})
        if sys_state.get("uptime_hours", 0) > 4:
            decisions.append({
                "priority": "low",
                "action": "idle_maintenance",
                "reason": f"守护进程已运行 {sys_state['uptime_hours']} 小时，今日无对话",
                "handler": "_handle_maintenance",
            })

    # 决策 5: 有未学习的知识
    learn = state.get("learning", {})
    if learn.get("has_pending") and not learn.get("today_learned"):
        decisions.append({
            "priority": "low",
            "action": "run_learning",
            "reason": "有待处理的学习任务",
            "handler": "_handle_learn",
        })

    # 决策 6: 编年史检测到平台期 → 建议做点什么
    chronicle = state.get("chronicle", {})
    if chronicle.get("plateau"):
        decisions.append({
            "priority": "medium",
            "action": "break_plateau",
            "reason": f"检测到平台期: {', '.join(chronicle['plateau'])}",
            "handler": "_handle_break_plateau",
        })

    # 决策 7: 编年史检测到下降趋势 → 诊断
    if chronicle.get("declining"):
        decisions.append({
            "priority": "high",
            "action": "investigate_decline",
            "reason": f"检测到下降趋势: {', '.join(chronicle['declining'])}",
            "handler": "_handle_investigate_decline",
        })

    return decisions


# ═══════════════════════════════════════════════
# 3. 行动执行
# ═══════════════════════════════════════════════

def _handle_archive():
    """归档旧知识"""
    try:
        import pipemind_memory_evolution as me
        n = me.forget_old()
        return f"已归档 {n} 条旧知识"
    except Exception as e:
        return f"归档失败: {e}"


def _handle_diagnose():
    """诊断错误"""
    try:
        import pipemind_self_evolution as se
        stats = se.PerformanceTracker.stats(days=1)
        se.AutoLearner.learn_from_error(
            "high_error_rate",
            f"Auto-diagnosed: {stats['error_rate']:.0%} error rate, "
            f"avg {stats['avg_duration']}s response time",
            confidence=0.5,
        )
        return f"已记录错误诊断: 错误率 {stats['error_rate']:.0%}"
    except Exception as e:
        return f"诊断失败: {e}"


def _handle_yixin_restart():
    """重启弈辛"""
    try:
        import pipemind_wsl_bridge as wsl
        ok = wsl.YixinControl.restart()
        return f"弈辛重启: {'成功' if ok else '失败'}"
    except Exception as e:
        return f"重启弈辛失败: {e}"


def _handle_maintenance():
    """执行维护"""
    actions = []
    try:
        import pipemind_memory_evolution as me
        n = me.forget_old()
        actions.append(f"归档 {n} 条")
    except Exception:
        pass
    try:
        import pipemind_session as pms
        pms.cleanup()
        actions.append("清理会话")
    except Exception:
        pass
    return "维护完成: " + "; ".join(actions) if actions else "无维护项"


def _handle_learn():
    """执行学习"""
    try:
        import pipemind_daily_learn as dl
        result = dl.daily_learn()
        return f"学习完成: {result.get('total_learned', 0)} 项"
    except Exception as e:
        return f"学习失败: {e}"


def _handle_break_plateau():
    """突破平台期：执行自我改进周期（dry-run）"""
    try:
        import pipemind_self_improve as si
        cycle = si.run_improvement_cycle(dry_run=True)
        return f"自我改进: {cycle.get('total', 0)} 条建议, 寻找突破方向"
    except Exception as e:
        return f"自我改进失败: {e}"


def _handle_investigate_decline():
    """诊断下降趋势"""
    try:
        import pipemind_self_evolution as se
        stats = se.PerformanceTracker.stats(days=3)
        se.AutoLearner.learn_from_error(
            "performance_decline",
            f"Auto-diagnosed decline: {stats.get('trend', 'unknown')} trend, "
            f"{stats.get('avg_duration', 0)}s avg response",
            confidence=0.4,
        )
        return f"已记录下降趋势诊断: {stats.get('trend', 'unknown')}"
    except Exception as e:
        return f"诊断失败: {e}"


def _execute_decision(decision: dict) -> dict:
    """执行一条决策"""
    handler_name = decision.get("handler", "")
    handler = globals().get(handler_name)
    if not handler:
        return {"action": decision["action"], "result": "无处理函数", "success": False}

    result = handler()
    return {
        "action": decision["action"],
        "reason": decision["reason"],
        "result": result,
        "success": "失败" not in result,
    }


# ═══════════════════════════════════════════════
# 4. 完整决策周期
# ═══════════════════════════════════════════════

def decision_cycle() -> dict:
    """执行一次完整的决策周期"""
    cycle = {
        "time": datetime.datetime.now().isoformat(),
        "state": {},
        "decisions": [],
        "actions": [],
    }

    # 1. 扫描
    state = scan()
    cycle["state"] = {
        "memory": state["memory"].get("total", 0),
        "perf": state["performance"].get("trend", "?"),
        "yixin": "running" if state["yixin"].get("running") else "stopped",
        "conversations_today": state["performance"].get("today_conversations", 0),
        "error_rate": state["performance"].get("error_rate", 0),
    }

    # 2. 分析
    decisions = analyze(state)
    cycle["decisions"] = [d["action"] for d in decisions]

    # 3. 执行（最多 2 条，避免过度行动）
    for d in decisions[:2]:
        result = _execute_decision(d)
        cycle["actions"].append(result)

    # 记录
    os.makedirs(MEM_DIR, exist_ok=True)
    logs = []
    if os.path.exists(DECISION_LOG):
        try:
            with open(DECISION_LOG, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            pass
    logs.append(cycle)
    if len(logs) > 100:
        logs = logs[-100:]
    with open(DECISION_LOG, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    return cycle


# ═══════════════════════════════════════════════
# 5. 后台线程
# ═══════════════════════════════════════════════

def start_decision_engine():
    """启动决策引擎后台线程"""
    global _running, _thread
    if _running:
        return
    _running = True
    _thread = threading.Thread(target=_engine_loop, daemon=True)
    _thread.start()


def stop_decision_engine():
    global _running
    _running = False


def _engine_loop():
    """每 30 分钟执行一次决策周期"""
    # 启动后先执行一次
    time.sleep(60)  # 给系统一点时间初始化
    try:
        result = decision_cycle()
        if result["actions"]:
            print(f"  🤖 决策: {len(result['actions'])} 项行动")
            for a in result["actions"]:
                print(f"     · {a['action']}: {a['result']}")
    except Exception as e:
        print(f"  ⚠ 决策周期失败: {e}")

    while _running:
        time.sleep(INTERVAL)
        try:
            result = decision_cycle()
            if result["actions"]:
                print(f"  🤖 决策: {len(result['actions'])} 项行动")
                for a in result["actions"]:
                    print(f"     · {a['action']}: {a['result']}")
        except Exception as e:
            print(f"  ⚠ 决策周期失败: {e}")


# ═══════════════════════════════════════════════
# 6. 查询接口
# ═══════════════════════════════════════════════

def get_decision_log(limit=20) -> list:
    """获取最近决策记录"""
    if not os.path.exists(DECISION_LOG):
        return []
    try:
        with open(DECISION_LOG, "r", encoding="utf-8") as f:
            logs = json.load(f)
        return logs[-limit:]
    except Exception:
        return []


def get_current_state() -> dict:
    """获取当前系统状态摘要"""
    return scan()
