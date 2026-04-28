"""PipeMind 会话持久化系统 — SQLite 记忆，跨会话不丢失。

功能:
1. 自动保存每一轮对话
2. 启动时加载最近上下文
3. /history 关键词搜索历史
4. 自动清理 30 天前的旧会话
"""

import json, os, sqlite3, datetime, hashlib, threading

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PIPEMIND_DIR, "memory", "pipemind_sessions.db")
MAX_CONTEXT_TURNS = 6      # 启动时加载最近几轮
MAX_SESSION_DAYS = 30      # 保留天数
MAX_SESSION_TOKENS = 8000  # 单会话 token 上限（估算）

# ── 数据库初始化 ──────────────────────────

_conn = None
_lock = threading.Lock()

def _get_db():
    global _conn
    if _conn is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT,
            tool_calls TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        _conn.execute("""CREATE INDEX IF NOT EXISTS idx_sessions_id 
            ON sessions(session_id, created_at)""")
        _conn.execute("""CREATE TABLE IF NOT EXISTS session_meta (
            session_id TEXT PRIMARY KEY,
            title TEXT,
            message_count INTEGER DEFAULT 0,
            started_at TIMESTAMP,
            last_active TIMESTAMP
        )""")
        _conn.commit()
    return _conn

# ── 保存 ──────────────────────────────────

def save_turn(session_id, role, content=None, tool_calls=None):
    """保存一轮对话"""
    db = _get_db()
    with _lock:
        db.execute(
            "INSERT INTO sessions (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
            (session_id, role, content, 
             json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None)
        )
        # 更新 meta
        db.execute("""INSERT INTO session_meta (session_id, message_count, last_active)
            VALUES (?, 1, datetime('now'))
            ON CONFLICT(session_id) DO UPDATE SET
                message_count = message_count + 1,
                last_active = datetime('now')""",
            (session_id,))
        db.commit()

def save_conversation(messages, session_id=None):
    """保存完整对话（启动时用）"""
    if not session_id:
        session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    db = _get_db()
    with _lock:
        # 设置标题 = 第一条用户消息
        title = None
        for m in messages:
            if m.get("role") == "user" and m.get("content"):
                title = m["content"][:80]
                break
        
        for m in messages:
            role = m.get("role", "")
            content = m.get("content")
            tc = m.get("tool_calls")
            db.execute(
                "INSERT INTO sessions (session_id, role, content, tool_calls) VALUES (?, ?, ?, ?)",
                (session_id, role, content,
                 json.dumps(tc, ensure_ascii=False) if tc else None)
            )
        
        count = len(messages)
        db.execute("""INSERT INTO session_meta (session_id, title, message_count, started_at, last_active)
            VALUES (?, ?, ?, datetime('now'), datetime('now'))
            ON CONFLICT(session_id) DO UPDATE SET
                message_count = message_count + ?,
                last_active = datetime('now')""",
            (session_id, title, count, count))
        db.commit()
    return session_id

# ── 加载 ──────────────────────────────────

def load_recent_context(turns=MAX_CONTEXT_TURNS):
    """从最近会话加载上下文（供启动时注入）"""
    db = _get_db()
    with _lock:
        # 找最新有内容的 session
        row = db.execute(
            "SELECT session_id FROM session_meta ORDER BY last_active DESC LIMIT 1"
        ).fetchone()
    
    if not row:
        return [], None
    
    session_id = row[0]
    with _lock:
        rows = db.execute(
            "SELECT role, content FROM sessions WHERE session_id=? AND role IN ('user','assistant') AND content IS NOT NULL AND content != '' ORDER BY created_at DESC LIMIT ?",
            (session_id, turns)
        ).fetchall()
    
    # 反转成时间顺序
    messages = []
    for role, content in reversed(rows):
        messages.append({"role": role, "content": content[:500]})
    
    return messages, session_id

def get_recent_sessions(limit=10):
    """获取最近会话列表"""
    db = _get_db()
    with _lock:
        rows = db.execute(
            "SELECT session_id, title, message_count, last_active FROM session_meta ORDER BY last_active DESC LIMIT ?",
            (limit,)
        ).fetchall()
    
    return [{
        "session_id": r[0],
        "title": r[1] or "(无标题)",
        "messages": r[2],
        "last_active": r[3]
    } for r in rows]

def search_history(query, limit=10):
    """搜索历史对话"""
    db = _get_db()
    with _lock:
        rows = db.execute(
            "SELECT s.session_id, s.role, s.content, s.created_at, m.title FROM sessions s LEFT JOIN session_meta m ON s.session_id=m.session_id WHERE s.content LIKE ? AND s.role='user' ORDER BY s.created_at DESC LIMIT ?",
            (f"%{query}%", limit)
        ).fetchall()
    
    return [{
        "session_id": r[0],
        "role": r[1],
        "content": r[2][:200] if r[2] else "",
        "time": r[3],
        "title": r[4] or "(无标题)"
    } for r in rows]

# ── 清理 ──────────────────────────────────

def cleanup():
    """清理 30 天前的旧会话"""
    db = _get_db()
    with _lock:
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=MAX_SESSION_DAYS)).isoformat()
        db.execute("DELETE FROM sessions WHERE created_at < ?", (cutoff,))
        db.execute("DELETE FROM session_meta WHERE last_active < ?", (cutoff,))
        db.commit()
    return True

# ── 主入口 ────────────────────────────────

def main():
    import sys
    args = sys.argv[1:]
    
    if "--search" in args and len(args) > 1:
        results = search_history(args[1])
        print(f"🔍 找到 {len(results)} 条结果:\n")
        for r in results[:5]:
            print(f"  [{r['session_id'][:16]}] {r['title']}")
            print(f"  {r['content'][:100]}")
            print()
    elif "--sessions" in args:
        sessions = get_recent_sessions()
        print(f"📋 最近 {len(sessions)} 个会话:\n")
        for s in sessions:
            print(f"  {s['session_id'][:16]} | {s['messages']}条 | {s['title'][:40]}")
    elif "--cleanup" in args:
        cleanup()
        print("🧹 清理完成")
    else:
        print("用法:")
        print("  python pipemind_session.py --search <关键词>")
        print("  python pipemind_session.py --sessions")
        print("  python pipemind_session.py --cleanup")

if __name__ == "__main__":
    main()
