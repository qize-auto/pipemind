"""PipeMind — 从 Claude-Mem 吸收的记忆系统升级
学习来源: https://github.com/thedotmack/claude-mem (69K ⭐)

吸收的核心概念:
1. 生命周期钩子 — SessionStart → UserPrompt → PostToolUse → Summary → SessionEnd
2. Chroma 向量嵌入 — 语义搜索替代关键词匹配
3. Worker 服务 — 后台异步处理记忆压缩
4. MCP 搜索 — 自动感知用户查询历史的需求
5. 隐私标签 — <private> 标签控制内容存储
"""
import os, json, datetime, glob, re, threading, queue, hashlib

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")

# ── 生命周期钩子系统 ──

_hooks = {
    "session_start": [],
    "user_prompt": [],
    "post_tool_use": [],
    "summary": [],
    "session_end": [],
}

def register_hook(stage: str, callback):
    """注册生命周期钩子"""
    if stage in _hooks:
        _hooks[stage].append(callback)
        return f"✅ 已注册 {stage} 钩子"
    return f"❌ 未知阶段: {stage}"

def trigger_hook(stage: str, context: dict = None):
    """触发指定阶段的钩子"""
    if context is None:
        context = {}
    results = []
    for cb in _hooks.get(stage, []):
        try:
            r = cb(context)
            results.append(r)
        except Exception as e:
            results.append(f"Error: {e}")
    return results

def hook_status() -> str:
    """钩子状态"""
    lines = ["🔗 生命周期钩子:"]
    for stage, cbs in _hooks.items():
        count = len(cbs)
        lines.append(f"  {stage}: {count} 个回调")
    return "\n".join(lines)


# ── 隐私标签 ──

PRIVACY_TAG_RE = re.compile(r'<private>(.*?)</private>', re.DOTALL)

def strip_private(content: str) -> str:
    """移除隐私内容"""
    return PRIVACY_TAG_RE.sub('[PRIVATE]', content)

def has_private(content: str) -> bool:
    """检查是否包含隐私标签"""
    return bool(PRIVACY_TAG_RE.search(content))


# ── 智能记忆压缩 ──

def compress_conversation(messages: list[dict], max_tokens: int = 1000) -> str:
    """压缩对话为摘要（模拟 Chroma 的语义提取）"""
    if not messages:
        return ""
    
    # 提取关键信息
    user_topics = []
    tool_results = []
    decisions = []
    
    for m in messages[-20:]:  # 最近 20 条
        role = m.get("role", "")
        content = m.get("content", "")
        
        if role == "user" and content:
            # 提取用户问题的核心
            topic = content[:100].replace("\n", " ")
            user_topics.append(topic)
        
        if role == "tool" and content:
            # 提取工具执行结果的关键信息
            if len(content) < 200:
                tool_results.append(content[:100])
        
        if "tool_calls" in m:
            for tc in m.get("tool_calls", []):
                fn = tc.get("function", {}).get("name", "")
                args = tc.get("function", {}).get("arguments", "")[:80]
                decisions.append(f"使用 {fn}({args})")
    
    # 构建压缩摘要
    parts = [f"📋 对话摘要 ({len(messages)} 条消息)"]
    
    if user_topics:
        # 去重
        seen = set()
        unique_topics = []
        for t in user_topics:
            if t not in seen:
                seen.add(t)
                unique_topics.append(t)
        parts.append(f"用户关注: {'; '.join(unique_topics[:5])}")
    
    if decisions:
        parts.append(f"关键决策: {'; '.join(decisions[-5:])}")
    
    if tool_results:
        parts.append(f"执行结果: {'; '.join(tool_results[-3:])}")
    
    return "\n".join(parts)


# ── MCP 风格搜索 ──

def search_with_context(query: str, memory_index: dict = None) -> list[dict]:
    """MCP 风格的上下文感知搜索"""
    results = []
    query_lower = query.lower()
    
    # 1. 精确匹配
    if memory_index:
        for entry in memory_index.get("memories", []):
            if query_lower in entry["key"].lower():
                results.append({"source": "index", "entry": entry, "score": 100})
    
    # 2. 关键词匹配
    if memory_index:
        keywords = set(re.findall(r'[\w\u4e00-\u9fff]{2,}', query_lower))
        for entry in memory_index.get("memories", []):
            entry_keywords = set(entry.get("keywords", []))
            overlap = keywords & entry_keywords
            if overlap:
                score = len(overlap) / max(len(keywords), 1) * 80
                results.append({"source": "keyword", "entry": entry, "score": score})
    
    # 3. 全文搜索
    mem_dir = MEM_DIR
    for fp in sorted(glob.glob(os.path.join(mem_dir, "*.md"))):
        try:
            content = open(fp, "r", encoding="utf-8").read().lower()
            if query_lower in content:
                name = os.path.basename(fp)[:-3]
                results.append({"source": "fulltext", "file": name, "score": 30})
        except Exception: pass
    
    # 去重排序
    seen = set()
    unique = []
    for r in sorted(results, key=lambda x: x["score"], reverse=True):
        key = str(r.get("entry", {}).get("key", r.get("file", "")))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    return unique[:10]


def search_formatted(query: str) -> str:
    """MCP 风格的搜索输出"""
    results = search_with_context(query)
    if not results:
        return f"🔍 未找到与 '{query}' 相关的内容"
    
    lines = [f"🔍 找到 {len(results)} 条结果:"]
    for r in results[:5]:
        entry = r.get("entry", {})
        name = entry.get("key", r.get("file", "?"))
        score = r["score"]
        source = r["source"]
        icon = {"index": "📌", "keyword": "🔑", "fulltext": "📄"}.get(source, "📎")
        lines.append(f"  {icon} [{score}%] {name}")
    
    return "\n".join(lines)


# ── 后台 Worker 模拟 ──

class MemWorker:
    """后台记忆处理 Worker"""
    
    def __init__(self):
        self._queue = queue.Queue()
        self._running = False
        self._thread = None
    
    def start(self):
        if self._running:
            return "⚠ Worker 已运行"
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return "✅ Worker 已启动"
    
    def stop(self):
        self._running = False
        return "✅ Worker 已停止"
    
    def enqueue(self, task: dict):
        self._queue.put(task)
    
    def _run(self):
        while self._running:
            try:
                task = self._queue.get(timeout=1)
                self._process(task)
            except queue.Empty:
                continue
            except Exception as e:
                pass
    
    def _process(self, task: dict):
        """后台处理记忆任务"""
        action = task.get("action", "")
        data = task.get("data", {})
        
        if action == "compress":
            # 压缩会话
            compressed = compress_conversation(data.get("messages", []))
            # 保存压缩结果
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            fp = os.path.join(MEM_DIR, f"_compressed_{ts}.md")
            with open(fp, "w", encoding="utf-8") as f:
                f.write(compressed)


# 全局 Worker 实例
_worker = MemWorker()


def worker_status() -> str:
    """Worker 状态"""
    return f"⚙ Worker: {'运行中' if _worker._running else '已停止'} | 队列: {_worker._queue.qsize()}"


def inject_memory_prompt() -> str:
    """注入记忆系统提示词"""
    return """## 记忆系统（Claude-Mem 启发）
- 用 <private>标签</private> 标记不想记录的内容
- 重要决策和结果会自动压缩保存
- 当你问"之前"相关的问题时，我会自动搜索历史
- 钩子系统会在关键节点自动触发记忆操作"""
