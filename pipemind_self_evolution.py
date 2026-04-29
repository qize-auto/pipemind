"""PipeMind 本体进化 — 自我监控、自我学习、自我优化

扩展 pipemind_evolution.py，新增：
  1. PerformanceTracker — 追踪每次对话的性能指标
  2. AutoLearner — 从使用中自动提炼教训和优化点
  3. SelfTuner — 根据模式调整行为参数
  4. DailyReport — 生成进化日报

数据 (memory/):
  _perf_history.json  — 性能历史 [{time, duration, tools, errors, topic}]
  _auto_lessons.json  — 自动提炼的教训 [{trigger, lesson, confidence}]
  _tuning_state.json  — 当前调优参数 {temperature, max_tokens, ...}
"""

import os, json, datetime, time, statistics, sys

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")

PERF_FILE = os.path.join(MEM_DIR, "_perf_history.json")
AUTO_LESSONS_FILE = os.path.join(MEM_DIR, "_auto_lessons.json")
TUNING_FILE = os.path.join(MEM_DIR, "_tuning_state.json")

MAX_PERF_RECORDS = 500        # 保留最近 500 条性能记录
MAX_AUTO_LESSONS = 100         # 自动学习上限
TUNING_ADJUSTMENT = 0.05       # 每次调优步长


# ═══════════════════════════════════════════════
# 1. 性能追踪
# ═══════════════════════════════════════════════

class PerformanceTracker:
    """追踪对话性能指标"""

    @staticmethod
    def _load():
        if not os.path.exists(PERF_FILE):
            return []
        try:
            with open(PERF_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def _save(records):
        os.makedirs(MEM_DIR, exist_ok=True)
        with open(PERF_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    @staticmethod
    def record(duration: float, tool_count: int, error_count: int,
               conversation_length: int, topic: str = ""):
        """记录一次对话的性能数据"""
        records = PerformanceTracker._load()
        records.append({
            "time": datetime.datetime.now().isoformat(),
            "duration": round(duration, 2),
            "tools": tool_count,
            "errors": error_count,
            "conv_length": conversation_length,
            "topic": topic[:50],
        })
        if len(records) > MAX_PERF_RECORDS:
            records = records[-MAX_PERF_RECORDS:]
        PerformanceTracker._save(records)

    @staticmethod
    def stats(days=7) -> dict:
        """获取近期性能统计"""
        records = PerformanceTracker._load()
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        recent = [r for r in records if r.get("time", "") >= cutoff]

        if not recent:
            return {"total": 0, "avg_duration": 0, "error_rate": 0,
                    "avg_tools": 0, "trend": "insufficient_data"}

        durations = [r["duration"] for r in recent]
        errors = sum(r.get("errors", 0) for r in recent)
        total = len(recent)

        # 趋势：比较最近 2 天和前 5 天
        recent_2d = [r for r in recent if r.get("time", "") >=
                     (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat()]
        older = [r for r in recent if r.get("time", "") <
                 (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat()]

        trend = "stable"
        if recent_2d and older:
            avg_recent = statistics.mean([r["duration"] for r in recent_2d])
            avg_older = statistics.mean([r["duration"] for r in older])
            if avg_recent < avg_older * 0.8:
                trend = "improving"
            elif avg_recent > avg_older * 1.2:
                trend = "degrading"

        return {
            "total": total,
            "avg_duration": round(statistics.mean(durations), 2),
            "max_duration": round(max(durations), 2),
            "min_duration": round(min(durations), 2),
            "error_rate": round(errors / max(total, 1), 3),
            "avg_tools": round(statistics.mean([r.get("tools", 0) for r in recent]), 1),
            "trend": trend,
            "period": f"{days}d",
        }


# ═══════════════════════════════════════════════
# 2. 自动学习
# ═══════════════════════════════════════════════

class AutoLearner:
    """从使用模式中自动学习"""

    @staticmethod
    def _load():
        if not os.path.exists(AUTO_LESSONS_FILE):
            return []
        try:
            with open(AUTO_LESSONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def _save(lessons):
        os.makedirs(MEM_DIR, exist_ok=True)
        with open(AUTO_LESSONS_FILE, "w", encoding="utf-8") as f:
            json.dump(lessons, f, ensure_ascii=False, indent=2)

    @staticmethod
    def learn_from_error(error_type: str, context: str, confidence: float = 0.5):
        """从错误中学到一条教训"""
        lessons = AutoLearner._load()
        lesson = {
            "id": f"al_{int(time.time())}_{len(lessons)}",
            "trigger": error_type,
            "lesson": f"遇到 {error_type} 时尝试：{_suggest_fix(error_type)}",
            "context": context[:100],
            "confidence": confidence,
            "count": 1,
            "learned": datetime.datetime.now().isoformat(),
            "last_seen": datetime.datetime.now().isoformat(),
        }

        # 合并相似教训
        existing = [l for l in lessons if l.get("trigger") == error_type]
        if existing:
            existing[0]["count"] += 1
            existing[0]["last_seen"] = lesson["learned"]
            existing[0]["confidence"] = min(existing[0]["confidence"] + 0.1, 1.0)
            return existing[0]

        lessons.append(lesson)
        if len(lessons) > MAX_AUTO_LESSONS:
            lessons = lessons[-MAX_AUTO_LESSONS:]
        AutoLearner._save(lessons)
        return lesson

    @staticmethod
    def learn_from_success(pattern: str, context: str):
        """从成功中强化一个模式"""
        lessons = AutoLearner._load()
        existing = [l for l in lessons if l.get("trigger") == f"success:{pattern}"]
        if existing:
            existing[0]["count"] += 1
            existing[0]["confidence"] = min(existing[0]["confidence"] + 0.05, 1.0)
            existing[0]["last_seen"] = datetime.datetime.now().isoformat()
        else:
            lessons.append({
                "id": f"al_{int(time.time())}_{len(lessons)}",
                "trigger": f"success:{pattern}",
                "lesson": f"模式有效：{pattern}",
                "context": context[:100],
                "confidence": 0.3,
                "count": 1,
                "learned": datetime.datetime.now().isoformat(),
                "last_seen": datetime.datetime.now().isoformat(),
            })
        if len(lessons) > MAX_AUTO_LESSONS:
            lessons = lessons[-MAX_AUTO_LESSONS:]
        AutoLearner._save(lessons)

    @staticmethod
    def get_injection() -> str:
        """获取可注入系统提示的自学习知识"""
        lessons = AutoLearner._load()
        high_conf = [l for l in lessons if l.get("confidence", 0) > 0.6]
        if not high_conf:
            return ""
        parts = ["## 自我学习（经验总结）"]
        for l in high_conf[-5:]:
            parts.append(f"• {l['lesson']}")
        return "\n".join(parts)


def _suggest_fix(error_type: str) -> str:
    """为常见错误类型建议修复策略"""
    fixes = {
        "timeout": "增加 timeout 或分步执行",
        "api_error": "重试或切换 API 端点",
        "parse_error": "检查返回格式并尝试重新解析",
        "tool_error": "检查工具参数是否正确",
        "rate_limit": "等待后重试，降低请求频率",
        "connection": "检查网络连接和代理设置",
        "auth_error": "检查 API Key 是否有效",
    }
    for key, fix in fixes.items():
        if key in error_type.lower():
            return fix
    return "记录上下文并重试"


# ═══════════════════════════════════════════════
# 3. 自优化调参
# ═══════════════════════════════════════════════

class SelfTuner:
    """根据使用数据自动调整行为参数"""

    DEFAULTS = {
        "temperature": 0.7,
        "max_tokens": 4096,
        "max_tool_calls_per_turn": 3,
        "retry_attempts": 3,
        "context_window": 10,
    }

    @staticmethod
    def _load():
        if not os.path.exists(TUNING_FILE):
            return dict(SelfTuner.DEFAULTS)
        try:
            with open(TUNING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**SelfTuner.DEFAULTS, **data}
        except Exception:
            return dict(SelfTuner.DEFAULTS)

    @staticmethod
    def _save(state):
        os.makedirs(MEM_DIR, exist_ok=True)
        with open(TUNING_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    @staticmethod
    def auto_tune(perf_stats: dict):
        """根据性能统计自动调整参数"""
        state = SelfTuner._load()
        changes = []

        # 如果响应慢 → 降低 max_tokens
        if perf_stats.get("avg_duration", 0) > 30:
            if state["max_tokens"] > 2048:
                state["max_tokens"] -= 512
                changes.append(f"max_tokens: {state['max_tokens'] + 512} → {state['max_tokens']}")

        # 如果错误率高 → 降低 temperature（更确定性）
        if perf_stats.get("error_rate", 0) > 0.2:
            if state["temperature"] > 0.3:
                state["temperature"] = round(state["temperature"] - TUNING_ADJUSTMENT, 2)
                changes.append(f"temperature: {state['temperature'] + TUNING_ADJUSTMENT:.2f} → {state['temperature']:.2f}")

        # 如果工具使用多 → 限制每轮工具调用
        if perf_stats.get("avg_tools", 0) > 5:
            if state["max_tool_calls_per_turn"] > 1:
                state["max_tool_calls_per_turn"] -= 1
                changes.append(f"max_tool_calls: {state['max_tool_calls_per_turn'] + 1} → {state['max_tool_calls_per_turn']}")

        # 如果性能稳定 → 稍微提升 temperature（更多创造力）
        if perf_stats.get("error_rate", 0) < 0.05 and perf_stats.get("avg_duration", 0) < 10:
            if state["temperature"] < 0.9:
                state["temperature"] = round(state["temperature"] + TUNING_ADJUSTMENT, 2)
                changes.append(f"temperature: {state['temperature'] - TUNING_ADJUSTMENT:.2f} → {state['temperature']:.2f} (性能稳定，提升创造力)")

        if changes:
            SelfTuner._save(state)

        return {
            "state": state,
            "changes": changes,
            "tuned": len(changes) > 0,
        }

    @staticmethod
    def get_config() -> dict:
        """获取当前调优参数"""
        return SelfTuner._load()

    @staticmethod
    def reset():
        """重置为默认参数"""
        SelfTuner._save(dict(SelfTuner.DEFAULTS))
        return dict(SelfTuner.DEFAULTS)


# ═══════════════════════════════════════════════
# 4. 进化日报
# ═══════════════════════════════════════════════

def generate_daily_report() -> dict:
    """生成每日进化报告

    由 daemon 每日调用（凌晨 4 点）
    """
    today = datetime.date.today().isoformat()

    # 性能统计
    perf = PerformanceTracker.stats(days=1)

    # 自动调参
    tune_result = SelfTuner.auto_tune(perf)

    # 自动学习统计
    lessons = AutoLearner._load()
    recent_lessons = [l for l in lessons
                     if l.get("learned", "").startswith(today)]

    report = {
        "date": today,
        "performance": perf,
        "tuning": {
            "changes": tune_result["changes"],
            "current": tune_result["state"],
        },
        "learning": {
            "new_lessons": len(recent_lessons),
            "total_lessons": len(lessons),
            "high_confidence": len([l for l in lessons if l.get("confidence", 0) > 0.7]),
        },
        "generated": datetime.datetime.now().isoformat(),
    }

    # 保存日报
    report_dir = os.path.join(MEM_DIR, "_evolution_reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"report_{today}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def get_recent_reports(days=7) -> list:
    """获取最近 N 天的进化报告"""
    report_dir = os.path.join(MEM_DIR, "_evolution_reports")
    if not os.path.exists(report_dir):
        return []
    reports = []
    for i in range(days):
        d = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
        path = os.path.join(report_dir, f"report_{d}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    reports.append(json.load(f))
            except Exception:
                pass
    return reports


# ═══════════════════════════════════════════════
# 5. 集成入口
# ═══════════════════════════════════════════════

def evolution_upgrade(agent_self=None) -> dict:
    """本体进化入口（由 evolution_cycle 或 daemon 调用）

    返回进化摘要，可注入系统提示
    """
    # 1. 性能检查 + 自调优
    perf = PerformanceTracker.stats(days=3)
    tune = SelfTuner.auto_tune(perf)

    # 2. 注入自学习知识
    lessons = AutoLearner.get_injection()

    return {
        "perf": perf,
        "tuning": tune,
        "injection": lessons,
    }


def format_evolution_summary() -> str:
    """生成人类可读的进化摘要"""
    perf = PerformanceTracker.stats(days=7)
    tune = SelfTuner.get_config()
    lessons = AutoLearner._load()
    high_conf = [l for l in lessons if l.get("confidence", 0) > 0.6]

    lines = [
        "🧬 本体进化摘要",
        f"  性能: {perf['total']} 次对话, 平均 {perf['avg_duration']}s, 趋势: {perf['trend']}",
        f"  参数: temp={tune['temperature']}, max_tokens={tune['max_tokens']}, retry={tune['retry_attempts']}",
        f"  经验: {len(high_conf)} 条高置信度教训, 总计 {len(lessons)} 条",
    ]
    if high_conf:
        lines.append("  最新经验:")
        for l in high_conf[-3:]:
            lines.append(f"    • {l['lesson']}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="生成进化日报")
    parser.add_argument("--stats", action="store_true", help="性能统计")
    parser.add_argument("--tune", action="store_true", help="执行自调优")
    parser.add_argument("--reset", action="store_true", help="重置参数")
    args = parser.parse_args()

    if args.report:
        r = generate_daily_report()
        print(f"✅ 日报已生成: {r['date']}")
        print(f"   对话: {r['performance']['total']} 次")
        print(f"   调优: {'; '.join(r['tuning']['changes']) or '无变化'}")

    if args.stats:
        print(format_evolution_summary())

    if args.tune:
        perf = PerformanceTracker.stats(days=3)
        result = SelfTuner.auto_tune(perf)
        print(f"✅ 自调优完成: {'; '.join(result['changes']) or '无变化'}")
        print(f"   当前参数: temp={result['state']['temperature']}, max_tokens={result['state']['max_tokens']}")

    if args.reset:
        SelfTuner.reset()
        print("✅ 已重置为默认参数")
