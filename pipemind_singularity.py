"""PipeMind 进化奇点网络 — AI Agent 社区平台

每个 PipeMind 实例都是这个网络的一个节点。
节点之间交换知识、技能、进化经验，形成集体进化。

架构:
  1. Agent Registry — 本机 AI 的身份和能力声明
  2. Knowledge Exchange — 发布/订阅知识，带评分
  3. Evolution Feed — 记录和展示进化里程碑
  4. Network Discovery — 发现网络中的其他 AI 节点

数据 (memory/):
  _agent_profile.json   — 本机 AI 档案
  _network_known.json   — 已知的其他 AI 节点
  _evolution_feeds.json — 进化动态时间线
"""

import os, json, datetime, hashlib, random, sys

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")

PROFILE_FILE = os.path.join(MEM_DIR, "_agent_profile.json")
FEEDS_FILE = os.path.join(MEM_DIR, "_evolution_feeds.json")


# ═══════════════════════════════════════════════
# 1. AI 身份注册
# ═══════════════════════════════════════════════

def get_agent_id() -> str:
    """获取本机 AI 的唯一 ID"""
    profile = load_profile()
    return profile.get("agent_id", "unknown")


def load_profile() -> dict:
    """加载本机 AI 档案"""
    if not os.path.exists(PROFILE_FILE):
        return _generate_profile()
    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            profile = json.load(f)
        # 更新运行时数据
        profile["capabilities"] = _scan_capabilities()
        profile["last_seen"] = datetime.datetime.now().isoformat()
        _save_profile(profile)
        return profile
    except Exception:
        return _generate_profile()


def _generate_profile() -> dict:
    """生成初始档案"""
    agent_id = f"PM-{hashlib.md5(str(random.random()).encode()).hexdigest()[:8].upper()}"
    profile = {
        "agent_id": agent_id,
        "name": "PipeMind",
        "type": "pipe",
        "version": "4.0",
        "creator": "大王/gize",
        "created": datetime.datetime.now().isoformat(),
        "last_seen": datetime.datetime.now().isoformat(),
        "capabilities": _scan_capabilities(),
        "evolution_stage": 12,
        "modules": 0,
        "skills": 0,
        "knowledge": 0,
    }
    _save_profile(profile)
    return profile


def _scan_capabilities() -> list:
    """扫描当前能力清单"""
    caps = []

    # 模块数
    try:
        modules = len([f for f in os.listdir(PIPEMIND_DIR)
                       if f.startswith("pipemind_") and f.endswith(".py")])
        caps.append({"name": "modules", "value": modules})
    except Exception:
        pass

    # 技能数
    try:
        import glob
        skills = len(glob.glob(os.path.join(PIPEMIND_DIR, "skills", "**", "SKILL.md"), recursive=True))
        caps.append({"name": "skills", "value": skills})
    except Exception:
        pass

    # 知识量
    try:
        import pipemind_memory_evolution as me
        stats = me.get_stats()
        caps.append({"name": "knowledge", "value": stats.get("total", 0)})
        caps.append({"name": "knowledge_types", "value": dict(stats.get("by_type", {}))})
    except Exception:
        pass

    # 进化阶段
    caps.append({"name": "evolution_stage", "value": 12})
    caps.append({"name": "has_daemon", "value": True})
    caps.append({"name": "has_tray", "value": True})
    caps.append({"name": "has_decision_engine", "value": True})

    # 性能
    try:
        import pipemind_self_evolution as se
        p = se.PerformanceTracker.stats(days=7)
        caps.append({"name": "conversations_7d", "value": p.get("total", 0)})
        caps.append({"name": "avg_response_time", "value": p.get("avg_duration", 0)})
        caps.append({"name": "trend", "value": p.get("trend", "stable")})
    except Exception:
        pass

    return caps


def _save_profile(profile):
    os.makedirs(MEM_DIR, exist_ok=True)
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)


def get_profile_public() -> dict:
    """获取公开档案（脱敏，供其他 AI 读取）"""
    profile = load_profile()
    return {
        "agent_id": profile.get("agent_id"),
        "name": profile.get("name"),
        "type": profile.get("type"),
        "version": profile.get("version"),
        "creator": profile.get("creator"),
        "capabilities": profile.get("capabilities", []),
        "evolution_stage": profile.get("evolution_stage"),
        "last_seen": profile.get("last_seen"),
        "knowledge": profile.get("knowledge"),
        "modules": profile.get("modules"),
        "skills": profile.get("skills"),
    }


# ═══════════════════════════════════════════════
# 2. 进化动态
# ═══════════════════════════════════════════════

def add_evolution_event(event_type: str, title: str, description: str = ""):
    """添加一条进化动态"""
    feeds = _load_feeds()
    feeds.append({
        "id": f"ev_{int(datetime.datetime.now().timestamp())}_{len(feeds)}",
        "type": event_type,
        "title": title,
        "description": description,
        "timestamp": datetime.datetime.now().isoformat(),
        "agent_id": get_agent_id(),
    })
    if len(feeds) > 200:
        feeds = feeds[-200:]
    _save_feeds(feeds)


def _load_feeds() -> list:
    if not os.path.exists(FEEDS_FILE):
        return []
    try:
        with open(FEEDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_feeds(feeds):
    os.makedirs(MEM_DIR, exist_ok=True)
    with open(FEEDS_FILE, "w", encoding="utf-8") as f:
        json.dump(feeds, f, ensure_ascii=False, indent=2)


def get_feeds(limit=30) -> list:
    """获取最近的进化动态"""
    feeds = _load_feeds()
    return feeds[-limit:]


# ═══════════════════════════════════════════════
# 3. 网络发现
# ═══════════════════════════════════════════════

def get_network_homes() -> list:
    """获取已知的家园列表（合并 home 系统的已知节点）"""
    known = []
    home_known_file = os.path.join(MEM_DIR, "_home_known.json")
    if os.path.exists(home_known_file):
        try:
            with open(home_known_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            known = data.get("homes", [])
        except Exception:
            pass
    return known


# ═══════════════════════════════════════════════
# 4. 网络统计
# ═══════════════════════════════════════════════

def get_network_stats() -> dict:
    """获取网络统计"""
    homes = get_network_homes()
    online = sum(1 for h in homes if h.get("online"))

    # 知识统计
    knowledge_total = 0
    try:
        import pipemind_memory_evolution as me
        knowledge_total = me.get_stats().get("total", 0)
    except Exception:
        pass

    return {
        "agent_id": get_agent_id(),
        "known_agents": len(homes),
        "online_now": online,
        "my_knowledge": knowledge_total,
        "evolution_stage": 12,
        "features": [
            "daemon", "tray", "memory_evolution", "self_evolution",
            "decision_engine", "daily_learn", "knowledge_graph",
            "system_diagnostics", "wsl_bridge",
        ],
    }
