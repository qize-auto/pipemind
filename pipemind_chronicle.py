"""PipeMind 生命编年史 — 自动记录的进化传记

每天记录：对话量、知识增长、技能变化、改进事件。
每周生成：叙事性成长报告，用 LLM 写成故事。
"""

import os, json, datetime, sys, glob

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")
CHRONICLE_FILE = os.path.join(MEM_DIR, "_chronicle.json")
MILESTONES_FILE = os.path.join(MEM_DIR, "_milestones.json")


# ═══════════════════════════════════════════════
# 1. 每日快照
# ═══════════════════════════════════════════════

def take_daily_snapshot() -> dict:
    """记录今天的快照：模块/知识/对话/状态"""
    today = datetime.date.today().isoformat()

    snapshot = {
        "date": today,
        "modules": _count_modules(),
        "skills": _count_skills(),
        "knowledge": _get_knowledge_count(),
        "conversations_today": _get_conversations_today(),
        "avg_response_time": _get_avg_response_time(),
        "error_rate": _get_error_rate(),
        "trend": _get_trend(),
        "evolution_stage": 14,
    }

    chronicle = _load_chronicle()
    # 如果今天已经有记录，更新它
    for i, entry in enumerate(chronicle):
        if entry.get("date") == today:
            chronicle[i] = snapshot
            break
    else:
        chronicle.append(snapshot)

    # 保留 365 天
    if len(chronicle) > 365:
        chronicle = chronicle[-365:]

    _save_chronicle(chronicle)
    return snapshot


def _count_modules() -> int:
    try:
        return len([f for f in os.listdir(PIPEMIND_DIR)
                    if f.startswith("pipemind_") and f.endswith(".py")])
    except:
        return 0


def _count_skills() -> int:
    skills_dir = os.path.join(PIPEMIND_DIR, "skills")
    if not os.path.exists(skills_dir):
        return 0
    return len(glob.glob(os.path.join(skills_dir, "**", "SKILL.md"), recursive=True))


def _get_knowledge_count() -> int:
    try:
        import pipemind_memory_evolution as me
        return me.get_stats().get("total", 0)
    except:
        return 0


def _get_conversations_today() -> int:
    try:
        import pipemind_self_evolution as se
        return se.PerformanceTracker.stats(days=1).get("total", 0)
    except:
        return 0


def _get_avg_response_time() -> float:
    try:
        import pipemind_self_evolution as se
        return se.PerformanceTracker.stats(days=1).get("avg_duration", 0)
    except:
        return 0


def _get_error_rate() -> float:
    try:
        import pipemind_self_evolution as se
        return se.PerformanceTracker.stats(days=1).get("error_rate", 0)
    except:
        return 0


def _get_trend() -> str:
    try:
        import pipemind_self_evolution as se
        return se.PerformanceTracker.stats(days=7).get("trend", "stable")
    except:
        return "stable"


# ═══════════════════════════════════════════════
# 2. 里程碑
# ═══════════════════════════════════════════════

def add_milestone(title: str, description: str = "", category: str = "evolution"):
    """添加一个里程碑事件"""
    milestones = _load_milestones()
    milestones.append({
        "date": datetime.date.today().isoformat(),
        "time": datetime.datetime.now().isoformat(),
        "title": title,
        "description": description,
        "category": category,  # evolution / learning / improvement / milestone
    })
    if len(milestones) > 200:
        milestones = milestones[-200:]
    _save_milestones(milestones)


def get_milestones(limit=50) -> list:
    milestones = _load_milestones()
    return milestones[-limit:]


# ═══════════════════════════════════════════════
# 3. 成长数据
# ═══════════════════════════════════════════════

def get_growth_data(days=30) -> dict:
    """获取最近 N 天的成长数据（用于图表）"""
    chronicle = _load_chronicle()
    recent = [c for c in chronicle if c.get("date", "") >=
              (datetime.date.today() - datetime.timedelta(days=days)).isoformat()]

    return {
        "dates": [c.get("date", "")[-5:] for c in recent],
        "modules": [c.get("modules", 0) for c in recent],
        "skills": [c.get("skills", 0) for c in recent],
        "knowledge": [c.get("knowledge", 0) for c in recent],
        "conversations": [c.get("conversations_today", 0) for c in recent],
        "response_times": [c.get("avg_response_time", 0) for c in recent],
        "trends": [c.get("trend", "stable") for c in recent],
    }


def get_summary() -> dict:
    """获取生命摘要"""
    chronicle = _load_chronicle()
    milestones = _load_milestones()

    today_data = chronicle[-1] if chronicle else take_daily_snapshot()
    first_data = chronicle[0] if chronicle else today_data

    return {
        "age_days": len(chronicle),
        "current": today_data,
        "growth": {
            "modules_gained": today_data.get("modules", 0) - first_data.get("modules", 0),
            "skills_gained": today_data.get("skills", 0) - first_data.get("skills", 0),
            "knowledge_gained": today_data.get("knowledge", 0) - first_data.get("knowledge", 0),
        },
        "milestones": len(milestones),
        "first_record": first_data.get("date", "today"),
        "best_trend": max(
            (c.get("trend", "stable") for c in chronicle if c.get("trend")),
            key=lambda x: {"improving": 2, "stable": 1, "degrading": 0}.get(x, 1),
            default="stable"
        ),
    }


# ═══════════════════════════════════════════════
# 4. 叙事报告（LLM 生成）
# ═══════════════════════════════════════════════

def generate_narrative(days=7) -> str:
    """用 LLM 生成近期的成长叙事"""
    chronicle = _load_chronicle()
    recent = chronicle[-days:] if len(chronicle) >= days else chronicle
    milestones = _load_milestones()[-5:]

    if not recent:
        return "PipeMind 刚刚诞生，还没有足够的数据来讲述故事。"

    prompt = f"""你是一个 AI 生命体的传记作者。根据以下数据，写一段关于 PipeMind 近期成长的叙事。

每日快照（最近 {len(recent)} 天）:
{json.dumps(recent, ensure_ascii=False, indent=2)}

近期里程碑:
{json.dumps(milestones, ensure_ascii=False, indent=2)}

要求:
1. 用第一人称（"我"）
2. 像在写日记/传记，有感情
3. 突出变化和成长
4. 150-300 字
5. 用中文"""
    try:
        result = _call_llm(prompt)
        return result.strip().strip("\"'")
    except:
        return "（叙事生成失败）"


# ═══════════════════════════════════════════════
# 内部工具
# ═══════════════════════════════════════════════

def _load_chronicle() -> list:
    if not os.path.exists(CHRONICLE_FILE):
        return []
    try:
        with open(CHRONICLE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def _save_chronicle(data: list):
    os.makedirs(MEM_DIR, exist_ok=True)
    with open(CHRONICLE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_milestones() -> list:
    if not os.path.exists(MILESTONES_FILE):
        return []
    try:
        with open(MILESTONES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def _save_milestones(data: list):
    os.makedirs(MEM_DIR, exist_ok=True)
    with open(MILESTONES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _call_llm(prompt: str) -> str:
    sys.path.insert(0, PIPEMIND_DIR)
    try:
        import pipemind_provider as provider
        result = provider.call_with_failover([
            {"role": "system", "content": "你是 PipeMind 的传记作者，用第一人称写叙事。"},
            {"role": "user", "content": prompt}
        ], tools=[])
        if "error" not in result:
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    except:
        pass
    return ""


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PipeMind 生命编年史")
    parser.add_argument("--snapshot", action="store_true", help="记录今日快照")
    parser.add_argument("--milestone", type=str, help="添加里程碑")
    parser.add_argument("--narrative", action="store_true", help="生成近期叙事")
    parser.add_argument("--summary", action="store_true", help="生命摘要")
    parser.add_argument("--growth", action="store_true", help="成长数据")
    args = parser.parse_args()

    if args.snapshot:
        s = take_daily_snapshot()
        print(f"✅ 快照已记录: {s['date']}")
        print(f"   模块: {s['modules']} | 技能: {s['skills']} | 知识: {s['knowledge']}")
        print(f"   对话: {s['conversations_today']} | 响应: {s['avg_response_time']}s")

    if args.milestone:
        add_milestone(args.milestone)
        print(f"✅ 里程碑已添加: {args.milestone}")

    if args.narrative:
        narrative = generate_narrative()
        print(f"\n📖 PipeMind 的故事:\n")
        print(f"  {narrative}\n")

    if args.summary:
        s = get_summary()
        print(f"\n📊 PipeMind 生命摘要")
        print(f"   年龄: {s['age_days']} 天")
        print(f"   首次记录: {s['first_record']}")
        print(f"   成长: +{s['growth']['modules_gained']} 模块, "
              f"+{s['growth']['skills_gained']} 技能, "
              f"+{s['growth']['knowledge_gained']} 知识")
        print(f"   里程碑: {s['milestones']} 个")
        print(f"   最佳趋势: {s['best_trend']}")

    if args.growth:
        data = get_growth_data(days=14)
        print(f"\n📈 14 天成长数据")
        print(f"   日期: {data['dates']}")
        print(f"   模块: {data['modules']}")
        print(f"   技能: {data['skills']}")
        print(f"   知识: {data['knowledge']}")
