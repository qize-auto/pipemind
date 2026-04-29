"""PipeMind 记忆进化系统 — 每日聚合 → 知识提取 → 跨会话注入 → 自动遗忘

功能:
  1. daily_consolidate()  — 每日聚合：扫会话 → LLM提取 → 存知识库
  2. get_relevant()       — 查询时注入相关历史知识
  3. forget_old()         — 自动归档30天未引用的知识
  4. get_stats()          — 记忆系统统计

数据文件 (memory/):
  _knowledge.json         — 知识点库 [{id, type, content, importance, source, created, access_count, score}]
  _daily_summary.json     — 每日摘要 [{date, sessions, new_knowledge, top_topics}]
  _knowledge_links.json   — 知识关联图 [{from, to, strength}]
  _knowledge_archive/     — 已归档的旧知识
"""

from pipemind_core import PIPEMIND_DIR, MEM_DIR
import os, json, datetime, re, time, hashlib, random, sys


KNOWLEDGE_FILE = os.path.join(MEM_DIR, "_knowledge.json")
SUMMARY_FILE = os.path.join(MEM_DIR, "_daily_summary.json")
LINKS_FILE = os.path.join(MEM_DIR, "_knowledge_links.json")
ARCHIVE_DIR = os.path.join(MEM_DIR, "_knowledge_archive")

MAX_KNOWLEDGE = 500        # 知识库上限
FORGET_DAYS = 30            # 未引用天数→归档
MAX_INJECTION = 5           # 每次注入最多几条


# ═══════════════════════════════════════════════
# 1. 知识提取（LLM）
# ═══════════════════════════════════════════════

def extract_knowledge(session_messages: list) -> list[dict]:
    """用 LLM 从一段对话中提取知识点

    返回 [{type, content, importance}]
    """
    if not session_messages or len(session_messages) < 3:
        return []

    conv_text = _format_conv(session_messages)
    prompt = f"""你是一个知识提取系统。分析以下对话，提取有用的知识点。

类型说明:
- fact: 客观事实（用户信息、项目细节、配置、路径、偏好）
- pattern: 行为模式（用户习惯、常用工具、交流风格）
- decision: 决策理由（为什么选A不选B）

要求:
1. 只提取可复用的知识（未来对话可能用到）
2. 每个知识点一句话，不超过50字
3. 重要性 1-5（5最重要）
4. 没有可提取的返回空数组

返回格式: JSON数组，如 [{{"type":"fact","content":"用户用Clash代理","importance":3}}]

对话内容:
{conv_text}"""

    try:
        result = _llm_call(prompt)
        items = _parse_result(result)
        return items
    except Exception:
        return []


def _format_conv(messages, max_chars=2000):
    """取最近 N 轮对话，格式化为文本"""
    parts = []
    total = 0
    for msg in messages[-10:]:
        role = msg.get("role", "?")
        content = str(msg.get("content", ""))[:300]
        if not content.strip():
            continue
        text = f"[{role}] {content}"
        if total + len(text) > max_chars:
            break
        parts.append(text)
        total += len(text)
    return "\n".join(parts)


def _llm_call(prompt):
    """调用 LLM（复用 provider 模块）"""
    sys.path.insert(0, PIPEMIND_DIR)
    try:
        import pipemind_provider as provider
        result = provider.call_with_failover([
            {"role": "system", "content": "你是知识提取系统，只返回 JSON 数组。"},
            {"role": "user", "content": prompt}
        ], tools=[])
        if "error" not in result:
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        pass
    return "[]"


def _parse_result(text):
    """解析 LLM 返回的 JSON"""
    m = re.search(r'\[.*?\]', text, re.DOTALL)
    if m:
        try:
            items = json.loads(m.group())
            if isinstance(items, list):
                return [i for i in items if isinstance(i, dict) and i.get("content")]
        except Exception:
            pass
    return []


# ═══════════════════════════════════════════════
# 2. 知识存储
# ═══════════════════════════════════════════════

def _load():
    if not os.path.exists(KNOWLEDGE_FILE):
        return []
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(items):
    os.makedirs(MEM_DIR, exist_ok=True)
    with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _new_id():
    return hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:12]


def _similar(a, b):
    """文本相似度（Jaccard）"""
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if not sa or not sb:
        return 0
    return len(sa & sb) / len(sa | sb)


def save_knowledge(items, session_id=""):
    """保存知识点（去重合并）"""
    knowledge = _load()
    now = datetime.datetime.now().isoformat()
    added = 0

    for item in items:
        content = item.get("content", "").strip()
        if not content or len(content) < 5:
            continue

        # 去重
        existing = [k for k in knowledge if _similar(content, k.get("content", "")) > 0.75]
        if existing:
            existing[0]["access_count"] = existing[0].get("access_count", 1) + 1
            existing[0]["last_seen"] = now
            continue

        entry = {
            "id": _new_id(),
            "type": item.get("type", "fact"),
            "content": content,
            "importance": min(item.get("importance", 3), 5),
            "source_session": session_id,
            "created": now,
            "last_accessed": now,
            "access_count": 1,
            "score": item.get("importance", 3) * 10 + 5,
        }
        knowledge.append(entry)
        added += 1

    # 裁剪
    if len(knowledge) > MAX_KNOWLEDGE:
        knowledge.sort(key=lambda k: k.get("score", 0), reverse=True)
        knowledge = knowledge[:MAX_KNOWLEDGE]

    _save(knowledge)
    return added


# ═══════════════════════════════════════════════
# 3. 上下文注入
# ═══════════════════════════════════════════════

def get_relevant(query: str, max_items=MAX_INJECTION) -> str:
    """根据当前输入获取相关历史知识

    返回格式化文本，可直接注入 system prompt
    """
    if not query:
        return ""
    knowledge = _load()
    if not knowledge:
        return ""

    query_words = set(query.lower().split())
    scored = []

    for k in knowledge:
        content = k.get("content", "")
        words = set(content.lower().split())
        overlap = query_words & words
        if overlap:
            base = len(overlap) * k.get("importance", 3)
            freq = k.get("access_count", 1)
            score = base * (1 + 0.1 * min(freq, 20))
            scored.append((score, k))

    scored.sort(key=lambda x: -x[0])
    top = scored[:max_items]
    if not top:
        return ""

    # 更新访问计数
    now = datetime.datetime.now().isoformat()
    touched_ids = {k["id"] for _, k in top}
    for k in knowledge:
        if k["id"] in touched_ids:
            k["last_accessed"] = now
            k["access_count"] = k.get("access_count", 1) + 1
    _save(knowledge)

    lines = []
    for _, k in top:
        icon = {"fact": "📌", "pattern": "🔄", "decision": "⚖️"}.get(k.get("type"), "📝")
        lines.append(f"{icon} {k['content']}")

    return "## 相关历史知识\n" + "\n".join(lines)


# ═══════════════════════════════════════════════
# 4. 每日聚合
# ═══════════════════════════════════════════════

def daily_consolidate() -> dict:
    """每日聚合（由 daemon 定时调用）"""
    log = {
        "time": datetime.datetime.now().isoformat(),
        "sessions": 0, "knowledge": 0, "archived": 0, "links": 0
    }

    # 1. 读今天的会话
    try:
        import pipemind_session as pms
        today = datetime.date.today().isoformat()
        sessions = pms.get_sessions_by_date(today, limit=50)
        log["sessions"] = len(sessions)
    except Exception:
        sessions = []

    # 2. 提取知识
    total = 0
    for sid, msgs in sessions:
        items = extract_knowledge(msgs)
        if items:
            total += save_knowledge(items, session_id=sid)

    log["knowledge"] = total

    # 3. 建关联索引
    links = _build_links()
    log["links"] = links

    # 4. 生成摘要
    _write_summary(sessions)

    # 5. 归档旧知识
    archived = forget_old()
    log["archived"] = archived

    # 写日志
    os.makedirs(MEM_DIR, exist_ok=True)
    log_path = os.path.join(MEM_DIR, "_consolidation_log.json")
    logs = []
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            pass
    logs.append(log)
    if len(logs) > 90:
        logs = logs[-90:]
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    return log


def _build_links():
    """根据内容相似度建立知识点关联"""
    knowledge = _load()
    if len(knowledge) < 2:
        return 0

    links = []
    for i, a in enumerate(knowledge):
        for j, b in enumerate(knowledge):
            if i >= j:
                continue
            sim = _similar(a.get("content", ""), b.get("content", ""))
            if sim > 0.4:
                links.append({
                    "from": a["id"], "to": b["id"],
                    "strength": round(sim, 2), "type": "similar"
                })

    os.makedirs(MEM_DIR, exist_ok=True)
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)
    return len(links)


def _write_summary(sessions):
    """生成每日摘要"""
    knowledge = _load()
    today = datetime.date.today().isoformat()

    # 今天新增的知识
    new_k = [k for k in knowledge if k.get("created", "").startswith(today)]

    # 高频词
    words = {}
    for k in new_k:
        for w in k.get("content", "").lower().split():
            if len(w) > 2:
                words[w] = words.get(w, 0) + 1
    topics = sorted(words.items(), key=lambda x: -x[1])[:8]

    summary = {
        "date": today,
        "sessions": len(sessions),
        "knowledge_total": len(knowledge),
        "new_knowledge": len(new_k),
        "new_facts": len([k for k in new_k if k.get("type") == "fact"]),
        "new_patterns": len([k for k in new_k if k.get("type") == "pattern"]),
        "new_decisions": len([k for k in new_k if k.get("type") == "decision"]),
        "top_topics": [{"word": w, "count": c} for w, c in topics],
    }

    summaries = []
    if os.path.exists(SUMMARY_FILE):
        try:
            with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
                summaries = json.load(f)
        except Exception:
            pass
    summaries.append(summary)
    if len(summaries) > 90:
        summaries = summaries[-90:]

    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)

    return summary


# ═══════════════════════════════════════════════
# 5. 自动遗忘
# ═══════════════════════════════════════════════

def forget_old() -> int:
    """归档 N 天未引用的知识"""
    knowledge = _load()
    now = datetime.datetime.now()
    cutoff = now - datetime.timedelta(days=FORGET_DAYS)

    active, archived = [], []
    for k in knowledge:
        try:
            last = datetime.datetime.fromisoformat(k.get("last_accessed", ""))
        except Exception:
            last = now
        if last < cutoff and k.get("access_count", 0) <= 2:
            archived.append(k)
        else:
            active.append(k)

    if archived:
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        path = os.path.join(ARCHIVE_DIR, f"archive_{datetime.date.today().isoformat()}.json")
        existing = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing.extend(archived)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    _save(active)
    return len(archived)


# ═══════════════════════════════════════════════
# 6. 统计与报告
# ═══════════════════════════════════════════════

def get_stats() -> dict:
    """记忆系统统计"""
    knowledge = _load()
    by_type = {}
    for k in knowledge:
        t = k.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "total": len(knowledge),
        "by_type": by_type,
        "avg_importance": round(
            sum(k.get("importance", 3) for k in knowledge) / max(len(knowledge), 1), 1
        ),
        "top": [
            {"content": k["content"][:60], "score": k.get("score", 0), "type": k.get("type")}
            for k in sorted(knowledge, key=lambda x: -x.get("score", 0))[:5]
        ],
        "forget_days": FORGET_DAYS,
        "max_knowledge": MAX_KNOWLEDGE,
    }


def get_consolidation_log(days=7) -> list:
    """获取最近聚合记录"""
    path = os.path.join(MEM_DIR, "_consolidation_log.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)[-days:]
    except Exception:
        return []


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--consolidate", action="store_true", help="执行每日聚合")
    parser.add_argument("--stats", action="store_true", help="记忆统计")
    parser.add_argument("--forget", action="store_true", help="执行遗忘")
    args = parser.parse_args()

    if args.consolidate:
        result = daily_consolidate()
        print(f"✅ 聚合完成: {result['sessions']} 会话, {result['knowledge']} 知识, {result['archived']} 归档")

    if args.forget:
        n = forget_old()
        print(f"✅ 归档 {n} 条")

    if args.stats:
        s = get_stats()
        print(f"\n📊 记忆系统状态")
        print(f"   知识总量: {s['total']}")
        print(f"   类型分布: {s['by_type']}")
        print(f"   平均重要性: {s['avg_importance']}")
        print(f"\n   Top 知识:")
        for t in s['top']:
            print(f"     [{t['type']}] {t['content']} (score: {t['score']})")
