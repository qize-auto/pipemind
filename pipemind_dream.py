"""PipeMind 梦境系统 — 历史反思 + nudge 提醒 + 行为闭环

移植自弈辛 dreaming-system v3，适配 Windows 原生环境。

用法:
  python pipemind_dream.py          # 完整做梦循环
  python pipemind_dream.py --nudge  # 查看当前提醒
  python pipemind_dream.py --forget # 清除过期 nudge
"""

from pipemind_core import PIPEMIND_DIR, MEM_DIR
import json, os, glob, datetime, hashlib, random

DREAM_DIR = os.path.join(PIPEMIND_DIR, "memory", ".dreams")
NUDGE_FILE = os.path.join(PIPEMIND_DIR, "pipemind_nudge.json")
MEMORY_DIR = os.path.join(PIPEMIND_DIR, "memory")
OUTPUT_DIR = os.path.join(PIPEMIND_DIR, "output")

NUDGE_TTL_HOURS = 72  # 3 天过期
MAX_NUDGES = 3

# ── Nudge 管理 ──────────────────────────────────

def _load_nudges():
    if not os.path.exists(NUDGE_FILE):
        return {"nudges": []}
    try:
        with open(NUDGE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"nudges": []}

def _save_nudges(data):
    os.makedirs(os.path.dirname(NUDGE_FILE), exist_ok=True)
    with open(NUDGE_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _expire_old():
    data = _load_nudges()
    now = datetime.datetime.now()
    active = []
    for n in data["nudges"]:
        if n.get("verified"): continue
        expires = n.get("expires", "")
        if expires:
            try:
                if datetime.datetime.fromisoformat(expires) < now:
                    continue
            except Exception:
                pass
        active.append(n)
    data["nudges"] = active
    _save_nudges(data)
    return active

def add_nudge(lesson, source="dream", ttl=72):
    """加一条 nudge，同类自动续期"""
    data = _load_nudges()
    now = datetime.datetime.now()
    expires = (now + datetime.timedelta(hours=ttl)).isoformat()
    key = lesson[:40]
    for n in data["nudges"]:
        if n.get("lesson", "")[:40] == key:
            n["expires"] = expires
            _save_nudges(data)
            return "updated"
    data["nudges"].append({
        "lesson": lesson, "source": source,
        "created": now.isoformat(), "expires": expires,
        "verified": False
    })
    data["nudges"] = data["nudges"][-MAX_NUDGES:]
    _save_nudges(data)
    return "added"

def show_nudges():
    active = _expire_old()
    if not active:
        print("🧠 当前无活跃提醒")
        return
    print(f"🧠 {len(active)} 条活跃提醒:")
    for n in active:
        exp = n.get("expires", "")[:16] if n.get("expires") else "?"
        print(f"  · {n['lesson'][:60]} (至{exp})")

# ── Light Sleep（摄入） ──────────────────────────

def light_sleep():
    """从 memory 和对话记录中提取信号"""
    os.makedirs(DREAM_DIR, exist_ok=True)
    
    signals = []
    
    # 1. 从 memory 文件中提取
    for fp in sorted(glob.glob(os.path.join(MEMORY_DIR, "*.md")), reverse=True)[:10]:
        try:
            content = open(fp, encoding="utf-8").read()
            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                for kw, typ in [("错误", "failure"), ("失败", "failure"),
                                ("注意", "pattern"), ("记住", "pattern"),
                                ("下次", "pattern"), ("教训", "lesson"),
                                ("学会", "lesson"), ("明白", "lesson")]:
                    if kw in line and len(line) > 10:
                        signals.append({"type": typ, "snippet": line[:120],
                                        "source": os.path.basename(fp)})
                        break
        except Exception:
            pass
    
    # 2. 从 lessons 中提取
    lessons_file = os.path.join(MEMORY_DIR, "_patterns.json")
    if os.path.exists(lessons_file):
        try:
            lessons = json.load(open(lessons_file, encoding="utf-8"))
            for l in (lessons if isinstance(lessons, list) else lessons.get("lessons", [])):
                if isinstance(l, dict) and "lesson" in l:
                    signals.append({"type": "lesson",
                                    "snippet": str(l["lesson"])[:120],
                                    "source": "lessons"})
        except Exception:
            pass
    
    # 3. 写入今天的光信号
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    signal_file = os.path.join(DREAM_DIR, f"light_{today}.json")
    existing = {"signals": []}
    if os.path.exists(signal_file):
        try:
            existing = json.load(open(signal_file, encoding="utf-8"))
        except Exception:
            pass
    
    # 去重
    seen = set()
    for s in existing.get("signals", []):
        seen.add(hashlib.md5(s["snippet"].encode()).hexdigest())
    
    for s in signals:
        h = hashlib.md5(s["snippet"].encode()).hexdigest()
        if h not in seen:
            existing.setdefault("signals", []).append(s)
            seen.add(h)
    
    with open(signal_file, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print(f"🌙 Light Sleep: {len(signals)} 条信号 (新 {len(signals) - len(existing['signals'] + [''])} 条)")
    return signals

# ── REM Sleep（反思） ────────────────────────────

def rem_sleep():
    """从 light signals 中提炼教训 → 生成 nudge"""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    signal_file = os.path.join(DREAM_DIR, f"light_{today}.json")
    if not os.path.exists(signal_file):
        print("🌙 无信号数据，跳过 REM")
        return
    
    signals = json.load(open(signal_file, encoding="utf-8")).get("signals", [])
    
    # 按内容分类
    by_type = {}
    for s in signals:
        by_type.setdefault(s["type"], []).append(s["snippet"])
    
    lessons = by_type.get("lesson", [])
    failures = by_type.get("failure", [])
    patterns = by_type.get("pattern", [])
    
    # 提取教训 → nudge
    promoted = 0
    for lesson in lessons:
        add_nudge(lesson, source="dream")
        promoted += 1
    
    # 复发频率 ≥ 2 的 failure → nudge
    from collections import Counter
    failure_counter = Counter(failures)
    for snippet, count in failure_counter.most_common(3):
        if count >= 2:
            add_nudge(f"复发{count}次: {snippet}", source="dream")
            promoted += 1
    
    print(f"💭 REM Sleep: {len(lessons)} lessons, {len(failures)} failures, {len(patterns)} patterns")
    print(f"   晋升 {promoted} 条 nudge")
    return promoted

# ── Deep Sleep（晋升 + 行为闭环） ──────────────────

def deep_sleep():
    """检查 nudge 有效性，写梦日记"""
    active = _expire_old()
    if not active:
        print("😴 Deep Sleep: 无活跃 nudge，跳过")
        return
    
    # 写梦日记
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    diary_path = os.path.join(OUTPUT_DIR, f"dream_{today}.md")
    
    entries = []
    entries.append(f"# PipeMind 梦日记 — {today}\n")
    entries.append(f"今晚有 {len(active)} 件事在心头:\n")
    for n in active:
        entries.append(f"- {n['lesson'][:80]}")
    entries.append("")
    
    with open(diary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(entries))
    
    print(f"📖 Deep Sleep: {len(active)} 条活跃 nudge")
    print(f"   梦日记: {diary_path}")

# ── 主入口 ───────────────────────────────────────

def main():
    import sys
    args = set(sys.argv[1:])
    
    if "--nudge" in args:
        show_nudges()
        return
    
    if "--forget" in args:
        data = _load_nudges()
        data["nudges"] = []
        _save_nudges(data)
        print("🧹 所有 nudge 已清除")
        return
    
    # 完整做梦循环
    print("🌙 PipeMind 梦境启动")
    print("=" * 40)
    light_sleep()
    rem_sleep()
    deep_sleep()
    show_nudges()
    print("=" * 40)
    print("💤 梦境完成")

if __name__ == "__main__":
    main()
