"""PipeMind — 语义记忆：升级版记忆系统（关键词 + 模糊搜索 + 自动关联）"""
import os, json, datetime, re, glob

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")
INDEX_FILE = os.path.join(MEM_DIR, "_index.json")


def _load_index() -> dict:
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: pass
    return {"memories": [], "tags": {}}

def _save_index(index: dict):
    os.makedirs(MEM_DIR, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def save(key: str, content: str, tags: list = None) -> str:
    """保存记忆（自动索引）"""
    safe = re.sub(r'[^\w\-\u4e00-\u9fff]', '_', key)
    path = os.path.join(MEM_DIR, f"{safe}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {key}\n\n{content}\n")
    
    # 更新索引
    idx = _load_index()
    entry = {
        "key": key, "file": f"{safe}.md",
        "tags": tags or [],
        "updated": datetime.datetime.now().isoformat(),
        "keywords": list(set(re.findall(r'[\u4e00-\u9fff]{2,}', content + key)))
    }
    # 替换或添加
    idx["memories"] = [e for e in idx["memories"] if e["key"] != key]
    idx["memories"].append(entry)
    
    # 更新标签索引
    for t in entry["tags"]:
        if t not in idx["tags"]:
            idx["tags"][t] = []
        if key not in idx["tags"][t]:
            idx["tags"][t].append(key)
    
    _save_index(idx)
    return f"✅ 已保存: {key} ({len(content)} chars)"


def search(query: str) -> list[dict]:
    """语义搜索（关键词匹配 + 标签匹配 + 全文搜索）"""
    idx = _load_index()
    q = query.lower()
    results = []
    
    # 1. 精确匹配
    for e in idx["memories"]:
        if q in e["key"].lower():
            results.append((e, 100))
    
    # 2. 标签匹配
    for tag, keys in idx["tags"].items():
        if q in tag.lower():
            for k in keys:
                for e in idx["memories"]:
                    if e["key"] == k and (e, 100) not in results:
                        results.append((e, 80))
    
    # 3. 关键词匹配
    for e in idx["memories"]:
        score = sum(1 for kw in e.get("keywords", []) if q in kw.lower())
        if score > 0:
            if not any(r[0]["key"] == e["key"] for r in results):
                results.append((e, score * 20))
    
    # 4. 全文搜索（读文件内容）
    if not results:
        for e in idx["memories"]:
            fp = os.path.join(MEM_DIR, e["file"])
            if os.path.exists(fp):
                try:
                    content = open(fp, "r", encoding="utf-8").read().lower()
                    if q in content:
                        results.append((e, 30))
                except: pass
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:10]


def search_text(query: str) -> str:
    """搜索并返回人类可读结果"""
    results = search(query)
    if not results:
        return f"🔍 未找到与 '{query}' 相关的记忆"
    
    lines = [f"🔍 找到 {len(results)} 条相关记忆:"]
    for e, score in results:
        fp = os.path.join(MEM_DIR, e["file"])
        preview = ""
        if os.path.exists(fp):
            try:
                content = open(fp, "r", encoding="utf-8").read()[:100].replace("\n", " ")
                preview = f" — {content}"
            except: pass
        lines.append(f"  [{score}%] {e['key']}{preview}")
    return "\n".join(lines)


def list_all() -> str:
    """列出所有记忆"""
    idx = _load_index()
    if not idx["memories"]:
        return "(暂无记忆)"
    
    by_tag = {}
    for e in idx["memories"]:
        for t in (e["tags"] or ["未分类"]):
            if t not in by_tag:
                by_tag[t] = []
            by_tag[t].append(e["key"])
    
    lines = [f"🧠 共 {len(idx['memories'])} 条记忆"]
    for tag, keys in sorted(by_tag.items()):
        lines.append(f"\n  📂 {tag} ({len(keys)}):")
        for k in keys[:5]:
            lines.append(f"    • {k}")
        if len(keys) > 5:
            lines.append(f"    ... 还有 {len(keys)-5} 条")
    return "\n".join(lines)


def delete(key: str) -> str:
    """删除记忆"""
    idx = _load_index()
    before = len(idx["memories"])
    idx["memories"] = [e for e in idx["memories"] if e["key"] != key]
    if len(idx["memories"]) < before:
        safe = re.sub(r'[^\w\-\u4e00-\u9fff]', '_', key)
        fp = os.path.join(MEM_DIR, f"{safe}.md")
        if os.path.exists(fp):
            os.remove(fp)
        _save_index(idx)
        return f"✅ 已删除: {key}"
    return f"❌ 未找到: {key}"
