"""PipeMind 联邦系统 — 多实例协作 + 知识市场

在进化网络 (singularity) 基础上：
  1. Multi-Instance 联邦 — 发现其他实例，委托任务
  2. Knowledge Marketplace — 发布/订阅知识包

架构:
  federation/
  ├── peer_discovery  — 发现网络中的其他 PipeMind 实例
  ├── task_delegation — 将任务委托给其他实例
  └── knowledge_exchange — 发布和订阅知识包
"""

import os, json, datetime, sys, uuid, hashlib, random

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")
PEERS_FILE = os.path.join(MEM_DIR, "_federation_peers.json")
TASKS_FILE = os.path.join(MEM_DIR, "_federation_tasks.json")
MARKET_FILE = os.path.join(MEM_DIR, "_knowledge_market.json")


# ═══════════════════════════════════════════════
# 1. 对等节点管理
# ═══════════════════════════════════════════════

def discover_peers() -> list:
    """发现网络中的其他 PipeMind 实例"""
    # 从家园系统获取已知节点
    peers = []
    known_file = os.path.join(MEM_DIR, "_home_known.json")
    if os.path.exists(known_file):
        try:
            known = json.load(open(known_file, encoding="utf-8"))
            peers = known.get("homes", [])
        except Exception:
            pass

    # 合并已保存的 peer 信息
    saved = _load_peers()
    for s in saved:
        existing = [p for p in peers if p.get("name") == s.get("name")]
        if not existing:
            peers.append(s)

    # 标记在线状态
    for p in peers:
        p["role"] = p.get("role", "peer")
        p["last_seen"] = p.get("last_seen", datetime.datetime.now().isoformat())

    _save_peers(peers)
    return peers


def register_peer(name: str, host: str, port: int = 9788, capabilities: list = None) -> dict:
    """注册一个对等节点"""
    peers = _load_peers()
    peer = {
        "id": str(uuid.uuid4())[:8],
        "name": name,
        "host": host,
        "port": port,
        "capabilities": capabilities or [],
        "role": "peer",
        "connected": False,
        "last_seen": datetime.datetime.now().isoformat(),
        "trust_score": 50,  # 初始信任度
    }
    peers.append(peer)
    _save_peers(peers)
    return peer


def get_peers() -> list:
    return _load_peers()


def get_online_peers() -> list:
    return [p for p in _load_peers() if p.get("connected")]


def _load_peers() -> list:
    if not os.path.exists(PEERS_FILE):
        return []
    try:
        with open(PEERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_peers(peers: list):
    os.makedirs(MEM_DIR, exist_ok=True)
    with open(PEERS_FILE, "w", encoding="utf-8") as f:
        json.dump(peers, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════
# 2. 任务委托
# ═══════════════════════════════════════════════

def delegate_task(goal: str, peer_name: str = None) -> dict:
    """将任务委托给其他实例执行"""
    task = {
        "id": str(uuid.uuid4())[:12],
        "goal": goal,
        "status": "pending",
        "assigned_to": peer_name or "any",
        "created": datetime.datetime.now().isoformat(),
        "completed": None,
        "result": None,
    }

    tasks = _load_tasks()
    tasks.append(task)
    _save_tasks(tasks)
    return task


def get_tasks(status: str = None) -> list:
    tasks = _load_tasks()
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    return tasks[-20:]


def update_task(task_id: str, status: str, result: str = None) -> bool:
    tasks = _load_tasks()
    for t in tasks:
        if t["id"] == task_id:
            t["status"] = status
            t["completed"] = datetime.datetime.now().isoformat()
            if result:
                t["result"] = result
            _save_tasks(tasks)
            return True
    return False


def _load_tasks() -> list:
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_tasks(tasks: list):
    os.makedirs(MEM_DIR, exist_ok=True)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════
# 3. 知识市场
# ═══════════════════════════════════════════════

def publish_knowledge(title: str, content: str, tags: list = None, price: int = 0) -> dict:
    """发布知识包到市场"""
    package = {
        "id": str(uuid.uuid4())[:12],
        "title": title,
        "content": content[:2000],
        "tags": tags or [],
        "price": price,  # 信誉积分
        "publisher": "local",
        "published": datetime.datetime.now().isoformat(),
        "downloads": 0,
        "rating": 0.0,
        "ratings_count": 0,
    }
    market = _load_market()
    market.append(package)
    _save_market(market)
    return package


def search_market(query: str) -> list:
    """搜索知识市场"""
    market = _load_market()
    q = query.lower()
    results = []
    for p in market:
        if q in p.get("title", "").lower() or q in " ".join(p.get("tags", [])).lower():
            results.append({
                "id": p["id"],
                "title": p["title"],
                "tags": p.get("tags", []),
                "downloads": p.get("downloads", 0),
                "rating": p.get("rating", 0),
                "price": p.get("price", 0),
            })
    return sorted(results, key=lambda x: -x["rating"])[:20]


def rate_package(package_id: str, rating: int) -> bool:
    """给知识包评分"""
    market = _load_market()
    for p in market:
        if p["id"] == package_id:
            old_total = p.get("rating", 0) * p.get("ratings_count", 0)
            p["ratings_count"] = p.get("ratings_count", 0) + 1
            p["rating"] = round((old_total + rating) / p["ratings_count"], 1)
            _save_market(market)
            return True
    return False


def get_market_stats() -> dict:
    market = _load_market()
    return {
        "total_packages": len(market),
        "total_downloads": sum(p.get("downloads", 0) for p in market),
        "avg_rating": round(
            sum(p.get("rating", 0) for p in market) / max(len(market), 1), 1
        ),
        "top_tags": _get_top_tags(market),
    }


def _get_top_tags(market: list, n=5) -> list:
    tags = {}
    for p in market:
        for t in p.get("tags", []):
            tags[t] = tags.get(t, 0) + 1
    return sorted(tags.items(), key=lambda x: -x[1])[:n]


def _load_market() -> list:
    if not os.path.exists(MARKET_FILE):
        return []
    try:
        with open(MARKET_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_market(market: list):
    os.makedirs(MEM_DIR, exist_ok=True)
    with open(MARKET_FILE, "w", encoding="utf-8") as f:
        json.dump(market, f, ensure_ascii=False, indent=2)
