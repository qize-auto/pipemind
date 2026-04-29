"""PipeMind 知识图谱 — 可视化知识库

生成知识节点和关联边的 JSON 数据，供前端渲染。

API:
  /api/knowledge/graph  → 完整图谱 {nodes, edges, stats}
  /api/knowledge/search → 搜索知识
  /api/knowledge/types  → 按类型统计
"""

import os, json, datetime, sys

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")
KNOWLEDGE_FILE = os.path.join(MEM_DIR, "_knowledge.json")
LINKS_FILE = os.path.join(MEM_DIR, "_knowledge_links.json")


def get_graph() -> dict:
    """生成完整图谱数据"""
    knowledge = _load_knowledge()
    links = _load_links()

    type_colors = {
        "fact": "#238636",
        "pattern": "#1f6feb",
        "decision": "#d29922",
    }

    nodes = []
    for k in knowledge[-100:]:  # 最多 100 个节点
        t = k.get("type", "fact")
        nodes.append({
            "id": k.get("id", ""),
            "label": k.get("content", "")[:40],
            "type": t,
            "color": type_colors.get(t, "#58a6ff"),
            "importance": k.get("importance", 3),
            "score": k.get("score", 0),
            "created": k.get("created", "")[:10],
            "last_accessed": k.get("last_accessed", "")[:10],
            "access_count": k.get("access_count", 1),
        })

    # 只保留两端都在节点中的边
    node_ids = {n["id"] for n in nodes}
    edges = []
    for l in links:
        if l.get("from") in node_ids and l.get("to") in node_ids:
            edges.append({
                "from": l["from"],
                "to": l["to"],
                "strength": l.get("strength", 0.5),
            })

    # 统计
    by_type = {}
    for n in nodes:
        by_type[n["type"]] = by_type.get(n["type"], 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_knowledge": len(knowledge),
            "visible": len(nodes),
            "connections": len(edges),
            "by_type": by_type,
            "last_consolidation": _get_last_consolidation(),
        },
    }


def search_knowledge(query: str, limit=20) -> list:
    """搜索知识库"""
    if not query:
        return []
    knowledge = _load_knowledge()
    query_lower = query.lower()
    results = []
    for k in knowledge:
        content = k.get("content", "").lower()
        if query_lower in content:
            results.append({
                "id": k.get("id", ""),
                "content": k.get("content", "")[:100],
                "type": k.get("type", "fact"),
                "importance": k.get("importance", 3),
                "created": k.get("created", "")[:10],
                "score": k.get("score", 0),
            })
        if len(results) >= limit:
            break
    return results


def get_types() -> dict:
    """按类型统计知识"""
    knowledge = _load_knowledge()
    types = {}
    today = datetime.date.today().isoformat()
    for k in knowledge:
        t = k.get("type", "unknown")
        if t not in types:
            types[t] = {"total": 0, "today": 0, "avg_importance": 0}
        types[t]["total"] += 1
        if k.get("created", "").startswith(today):
            types[t]["today"] += 1
        types[t]["avg_importance"] = (
            (types[t]["avg_importance"] * (types[t]["total"] - 1) + k.get("importance", 3))
            / types[t]["total"]
        )
    return types


def get_recent_activity(days=7) -> list:
    """获取近期知识活动"""
    knowledge = _load_knowledge()
    by_date = {}
    for k in knowledge:
        date = k.get("created", "")[:10]
        if date:
            by_date.setdefault(date, {"new": 0, "accessed": 0})
            by_date[date]["new"] += 1
        access_date = k.get("last_accessed", "")[:10]
        if access_date and access_date != date:
            by_date.setdefault(access_date, {"new": 0, "accessed": 0})
            by_date[access_date]["accessed"] += 1

    # 按日期排序
    sorted_dates = sorted(by_date.keys(), reverse=True)[:days]
    return [
        {"date": d, **by_date[d]}
        for d in sorted_dates
    ]


# ── 内部工具 ──

def _load_knowledge():
    if not os.path.exists(KNOWLEDGE_FILE):
        return []
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def _load_links():
    if not os.path.exists(LINKS_FILE):
        return []
    try:
        with open(LINKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def _get_last_consolidation():
    log_path = os.path.join(MEM_DIR, "_consolidation_log.json")
    if not os.path.exists(log_path):
        return None
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            logs = json.load(f)
        return logs[-1].get("time", "")[:16] if logs else None
    except:
        return None


# ── CLI ──

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="知识图谱工具")
    parser.add_argument("--graph", action="store_true", help="输出图谱统计")
    parser.add_argument("--search", type=str, help="搜索知识")
    parser.add_argument("--types", action="store_true", help="类型统计")
    args = parser.parse_args()

    if args.graph:
        g = get_graph()
        print(f"知识总量: {g['stats']['total_knowledge']}")
        print(f"可见节点: {g['stats']['visible']}")
        print(f"关联边数: {g['stats']['connections']}")
        print(f"类型分布: {g['stats']['by_type']}")

    if args.search:
        results = search_knowledge(args.search)
        print(f"搜索 '{args.search}': {len(results)} 条结果\n")
        for r in results:
            print(f"  [{r['type']}] {r['content']} (score={r['score']})")

    if args.types:
        types = get_types()
        for t, s in types.items():
            print(f"  {t}: {s['total']} 条, 今天 +{s['today']}, 平均重要性 {s['avg_importance']:.1f}")
