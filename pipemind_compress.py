"""PipeMind 上下文压缩引擎 — 长对话自动压缩，防止 token 超限。

策略：
1. 估算每轮 token（按字符数 1:4 粗略估算）
2. 超过阈值时，将中间轮次压缩为一句话摘要
3. 保留系统提示 + 最近 N 轮完整对话
"""

from pipemind_core import PIPEMIND_DIR, MEM_DIR
import json, os, datetime


# Token 估算：中英文混合按 1 字 ≈ 2 token
ESTIMATE_RATIO = 2.0

# ── 预算 ──────────────────────────────────────

# 硬限制（超过此值强制压缩）
HARD_LIMIT_TOKENS = 12000
# 触发压缩的阈值（超过此值开始压缩）
SOFT_LIMIT_TOKENS = 8000
# 压缩后保留的完整轮次（最近的）
KEEP_RECENT_TURNS = 8
# 压缩摘要的最大长度（字符）
MAX_SUMMARY_CHARS = 300

# ── Token 估算 ────────────────────────────────

def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中英文混用）"""
    if not text:
        return 0
    # 中文字符算 2 token，其他算 0.5
    cn = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other = len(text) - cn
    return int(cn * 2 + other * 0.5)

def estimate_messages_tokens(messages: list) -> int:
    """估算整组消息的 token 数"""
    total = 0
    for m in messages:
        role = m.get("role", "")
        content = m.get("content", "")
        tc = m.get("tool_calls")
        total += 4  # role overhead
        total += estimate_tokens(str(content))
        if tc:
            total += estimate_tokens(str(tc))
    return total

# ── 压缩 ──────────────────────────────────────

def should_compress(messages: list) -> bool:
    """检查是否需要压缩"""
    total = estimate_messages_tokens(messages)
    return total >= SOFT_LIMIT_TOKENS

def compress(messages: list, verbose: bool = False) -> list:
    """压缩过长对话"""
    if not should_compress(messages):
        return messages
    
    # 找到系统提示
    sys_idx = 0
    for i, m in enumerate(messages):
        if m.get("role") == "system":
            sys_idx = i
            break
    
    # 系统提示之后的消息
    conv = messages[sys_idx + 1:]
    
    if len(conv) <= KEEP_RECENT_TURNS * 2:
        # 对话太短，不需要压缩
        return messages
    
    # 分离：保留最近 N 轮，压缩中间的
    keep_count = KEEP_RECENT_TURNS * 2  # user + assistant = 1 轮
    recent = conv[-keep_count:]  # 保留最近的
    to_compress = conv[:-keep_count]  # 压缩中间的
    
    # 只压缩 user/assistant 轮次，跳过 tool 消息
    compressed_lines = []
    user_count = 0
    for m in to_compress:
        role = m.get("role", "")
        content = m.get("content", "")
        if role == "user" and content:
            compressed_lines.append(f"Q: {content[:100]}")
            user_count += 1
            if user_count >= 3:
                break
    
    summary = ""
    if compressed_lines:
        summary = f"[上下文摘要: {' | '.join(compressed_lines)}]"
        # 如果摘要太长就截断
        if len(summary) > MAX_SUMMARY_CHARS:
            summary = summary[:MAX_SUMMARY_CHARS] + "...]"
    
    # 构建压缩后的消息列表
    compressed = messages[:sys_idx + 1]  # 保留系统提示
    
    if summary:
        compressed.append({
            "role": "system",
            "content": f"## 历史摘要\n{summary}\n(以下为当前对话)"
        })
    
    compressed.extend(recent)
    
    total_before = estimate_messages_tokens(messages)
    total_after = estimate_messages_tokens(compressed)
    saved = total_before - total_after
    
    if verbose:
        print(f"  📦 上下文压缩: {total_before} → {total_after} tokens (省 {saved})")
    
    return compressed

# ── 统计 ──────────────────────────────────────

def context_stats(messages: list) -> dict:
    """当前上下文统计"""
    total = estimate_messages_tokens(messages)
    msg_count = len(messages)
    
    # 按角色统计
    roles = {}
    for m in messages:
        r = m.get("role", "?")
        roles[r] = roles.get(r, 0) + 1
    
    return {
        "tokens": total,
        "messages": msg_count,
        "roles": roles,
        "over_soft": total >= SOFT_LIMIT_TOKENS,
        "over_hard": total >= HARD_LIMIT_TOKENS,
        "pct": round(total / HARD_LIMIT_TOKENS * 100, 1),
    }

def format_stats(stats: dict) -> str:
    """格式化的统计报告"""
    bar_len = 20
    filled = int(stats["pct"] / 100 * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    return (
        f"  📊 上下文:\n"
        f"     {stats['tokens']}/{HARD_LIMIT_TOKENS} tokens\n"
        f"     {bar} {stats['pct']}%\n"
        f"     {stats['messages']} 条消息\n"
    )

def compress_cycle(messages, verbose=False):
    """完整压缩周期：检查 → 压缩 → 报告"""
    stats = context_stats(messages)
    
    if stats["over_hard"]:
        if verbose:
            print(f"  ⚠ 接近上限 ({stats['tokens']}/{HARD_LIMIT_TOKENS})，强制压缩")
        return compress(messages, verbose), stats
    
    if stats["over_soft"]:
        if verbose:
            print(f"  📦 触发压缩预算 ({stats['tokens']}/{SOFT_LIMIT_TOKENS})")
        return compress(messages, verbose), stats
    
    return messages, stats

# ── CLI ────────────────────────────────────────

def main():
    import sys
    args = sys.argv[1:]
    
    if "--test" in args:
        # 生成测试数据
        test_msgs = [{"role": "system", "content": "你是 PipeMind"}]
        for i in range(20):
            test_msgs.append({"role": "user", "content": f"这是第{i+1}轮用户问题，内容是关于某某话题的讨论" * 5})
            test_msgs.append({"role": "assistant", "content": f"这是第{i+1}轮的回答，包含了详细的解释和说明" * 8})
        
        stats = context_stats(test_msgs)
        print("压缩前:")
        print(format_stats(stats))
        
        compressed, new_stats = compress_cycle(test_msgs, verbose=True)
        print(f"\n压缩后: {len(compressed)} 条消息")
        if len(compressed) < len(test_msgs):
            print(f"  删除了 {len(test_msgs) - len(compressed)} 条中间消息")
    
    elif "--stats" in args:
        print(f"  软限制: {SOFT_LIMIT_TOKENS} tokens")
        print(f"  硬限制: {HARD_LIMIT_TOKENS} tokens")
        print(f"  保留轮次: {KEEP_RECENT_TURNS}")
        print(f"  摘要长度: {MAX_SUMMARY_CHARS} 字符")
    
    else:
        print("用法:")
        print("  python pipemind_compress.py --test   测试压缩")
        print("  python pipemind_compress.py --stats  查看预算")

if __name__ == "__main__":
    main()
