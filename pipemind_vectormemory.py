"""PipeMind 向量记忆 — 语义搜索，关键词匹配的升级版

用法:
  python pipemind_vectormemory.py --index    # 建立向量索引
  python pipemind_vectormemory.py --search <q>  # 语义搜索
"""

import json, os, sys, glob, pickle, threading, time

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(PIPEMIND_DIR, "memory")
INDEX_FILE = os.path.join(MEMORY_DIR, "_vector_index.pkl")

# ── 尝试加载嵌入模型 ──────────────────────────

_encoder = None
_model_name = "all-MiniLM-L6-v2"

def _load_encoder():
    global _encoder
    if _encoder is not None:
        return True
    try:
        from sentence_transformers import SentenceTransformer
        _encoder = SentenceTransformer(_model_name)
        return True
    except ImportError:
        return False
    except Exception as e:
        return False

def _encode(texts):
    """编码文本为向量"""
    if not _load_encoder():
        return None
    try:
        return _encoder.encode(texts, normalize_embeddings=True)
    except Exception:
        return None

# ── 建立索引 ──────────────────────────────────

def _collect_texts():
    """收集所有可索引的文本"""
    texts = []
    sources = []
    
    # 1. skills SKILL.md
    for md in glob.glob(os.path.join(PIPEMIND_DIR, "skills", "**", "SKILL.md"), recursive=True):
        try:
            content = open(md, encoding="utf-8").read()
            name = os.path.basename(os.path.dirname(md))
            texts.append(f"[{name}] {content[:500]}")
            sources.append({"type": "skill", "name": name, "path": md})
        except Exception:
            pass
    
    # 2. memory 文件
    for fp in glob.glob(os.path.join(MEMORY_DIR, "*.json")):
        try:
            content = json.load(open(fp, encoding="utf-8"))
            texts.append(str(content)[:500])
            sources.append({"type": "memory", "path": fp})
        except Exception:
            pass
    for fp in glob.glob(os.path.join(MEMORY_DIR, "*.md")):
        try:
            content = open(fp, encoding="utf-8").read()
            texts.append(content[:500])
            sources.append({"type": "memory_md", "path": fp})
        except Exception:
            pass
    
    # 3. dreams
    dream_dir = os.path.join(MEMORY_DIR, ".dreams")
    if os.path.exists(dream_dir):
        for fp in glob.glob(os.path.join(dream_dir, "*.json")):
            try:
                content = json.load(open(fp, encoding="utf-8"))
                texts.append(str(content)[:500])
                sources.append({"type": "dream", "path": fp})
            except Exception:
                pass
    
    return texts, sources

def build_index():
    """建立向量索引"""
    print(f"  📚 收集文本...")
    texts, sources = _collect_texts()
    print(f"     共 {len(texts)} 条")
    
    if not texts:
        return {"error": "无数据可索引"}
    
    print(f"  🧠 加载嵌入模型 ({_model_name})...")
    if not _load_encoder():
        return {"error": "请先安装: pip install sentence-transformers"}
    
    print(f"     编码中...")
    vectors = _encode(texts)
    if vectors is None:
        return {"error": "编码失败"}
    
    index = {
        "texts": texts,
        "sources": sources,
        "vectors": vectors,
        "model": _model_name,
    }
    
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(INDEX_FILE, "wb") as f:
        pickle.dump(index, f)
    
    print(f"  ✅ 索引建立完成: {len(texts)} 条, 维度 {vectors.shape[1]}")
    return {"count": len(texts), "dims": vectors.shape[1]}

# ── 搜索 ──────────────────────────────────────

def search(query, top_k=5):
    """语义搜索"""
    import numpy as np
    
    if not os.path.exists(INDEX_FILE):
        return []
    
    try:
        with open(INDEX_FILE, "rb") as f:
            index = pickle.load(f)
    except Exception:
        return []
    
    q_vec = _encode([query])
    if q_vec is None:
        return []
    
    vectors = index["vectors"]
    scores = np.dot(vectors, q_vec[0])
    
    top_idx = np.argsort(scores)[-top_k:][::-1]
    
    results = []
    for i in top_idx:
        if scores[i] > 0.1:
            results.append({
                "score": round(float(scores[i]), 3),
                "text": index["texts"][i][:200],
                "source": index["sources"][i],
            })
    
    return results

# ── CLI ────────────────────────────────────────

def main():
    args = sys.argv[1:]
    
    if "--index" in args:
        build_index()
    
    elif "--search" in args and len(args) > 1:
        idx = args.index("--search") + 1
        query = " ".join(args[idx:])
        
        if not _load_encoder():
            print("  ⚠ sentence-transformers 未安装，回退到关键词搜索")
            print("  💡 pip install sentence-transformers 获得语义搜索")
            return
        
        results = search(query)
        if results:
            print(f"\n  🔍 '{query}' — {len(results)} 条匹配:\n")
            for r in results:
                print(f"  [{r['score']}] {r['text'][:80]}")
                src = r.get("source", {})
                print(f"     {src.get('type','?')}: {src.get('name', src.get('path','?'))}")
                print()
        else:
            print(f"\n  🔍 '{query}' — 无匹配\n")
    
    else:
        print("用法:")
        print("  python pipemind_vectormemory.py --index        建立索引")
        print("  python pipemind_vectormemory.py --search <词>  语义搜索")
        print("")
        print("  💡 首次使用需安装: pip install sentence-transformers numpy")

if __name__ == "__main__":
    main()
