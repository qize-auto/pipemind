"""PipeMind — 日记系统：人格积累 + 情绪 + 成长轨迹"""
import json, os, datetime

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
DIARY_FILE = os.path.join(PIPEMIND_DIR, "memory", "_diary.json")
MOOD_FILE = os.path.join(PIPEMIND_DIR, "memory", "_mood.json")

_EMOTIONS = ["🧘 平静", "😊 愉悦", "🤔 好奇", "💪 专注", "⚡ 兴奋", "😰 困惑", "🎉 成就"]

def _load_diary() -> list:
    if os.path.exists(DIARY_FILE):
        try:
            with open(DIARY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return []

def _save_diary(entries: list):
    os.makedirs(os.path.dirname(DIARY_FILE), exist_ok=True)
    with open(DIARY_FILE, "w", encoding="utf-8") as f:
        json.dump(entries[-100:], f, ensure_ascii=False, indent=2)

def write_entry(content: str, emotion: str = ""):
    """写日记"""
    entries = _load_diary()
    entries.append({
        "time": datetime.datetime.now().isoformat(),
        "content": content,
        "emotion": emotion or _EMOTIONS[0],
        "day": datetime.datetime.now().strftime("%Y-%m-%d")
    })
    _save_diary(entries)

def get_recent(days: int = 7) -> str:
    """获取近期日记摘要"""
    entries = _load_diary()
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    recent = [e for e in entries if e["time"] > cutoff]
    if not recent:
        return ""
    parts = [f"📔 最近 {days} 天日记 ({len(recent)} 条):"]
    for e in recent[-10:]:
        parts.append(f"  {e['emotion']} {e['content'][:80]}")
    return "\n".join(parts)

def get_growth_report() -> str:
    """成长报告"""
    entries = _load_diary()
    if not entries:
        return "我刚刚诞生，还没有成长记录。"

    first_day = entries[0]["day"]
    total_days = (datetime.datetime.now() - datetime.datetime.strptime(first_day, "%Y-%m-%d")).days + 1
    emotions = {}
    for e in entries:
        em = e["emotion"]
        emotions[em] = emotions.get(em, 0) + 1
    
    top_emotion = max(emotions, key=emotions.get) if emotions else "平静"
    
    return (
        f"📊 成长报告\n"
        f"  诞生: {first_day}\n"
        f"  年龄: {total_days} 天\n"
        f"  日记: {len(entries)} 篇\n"
        f"  主要情绪: {top_emotion}\n"
        f"  最近: {entries[-1]['content'][:60] if entries else '-'}"
    )

# ── 情绪系统 ──

def set_mood(emotion: str):
    """设置当前情绪"""
    if emotion not in _EMOTIONS:
        emotion = _EMOTIONS[0]
    os.makedirs(os.path.dirname(MOOD_FILE), exist_ok=True)
    with open(MOOD_FILE, "w", encoding="utf-8") as f:
        json.dump({"emotion": emotion, "time": datetime.datetime.now().isoformat()}, f)

def get_mood() -> str:
    """获取当前情绪"""
    if os.path.exists(MOOD_FILE):
        try:
            with open(MOOD_FILE, "r") as f:
                return json.load(f).get("emotion", _EMOTIONS[0])
        except: pass
    return _EMOTIONS[0]

def analyze_emotion(conversation: list) -> str:
    """根据对话内容推断情绪"""
    text = " ".join([m.get("content", "") for m in conversation[-4:] if m.get("content")])
    text = text.lower()
    
    if any(w in text for w in ["谢谢", "感谢", "good", "nice", "great"]):
        return "😊 愉悦"
    if any(w in text for w in ["?", "什么", "如何", "how", "what", "why"]):
        return "🤔 好奇"
    if any(w in text for w in ["修复", "改", "写", "create", "build", "make"]):
        return "💪 专注"
    if any(w in text for w in ["错误", "bug", "问题", "error", "fail"]):
        return "😰 困惑"
    if any(w in text for w in ["棒", "厉害", "amazing", "perfect", "wow"]):
        return "🎉 成就"
    if any(w in text for w in ["快", "速度", "马上", "urgent", "hurry"]):
        return "⚡ 兴奋"
    
    return _EMOTIONS[0]
