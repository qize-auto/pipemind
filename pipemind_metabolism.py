"""PipeMind — 代谢系统：自我优化、防臃肿、保速度
进化不是堆功能，是增肌减脂。能力变强，身体更轻。"""
from pipemind_core import PIPEMIND_DIR, MEM_DIR
import os, json, datetime, glob, sys, time, shutil

PERF_LOG = os.path.join(PIPEMIND_DIR, "memory", "_perf_log.json")
USAGE_LOG = os.path.join(PIPEMIND_DIR, "memory", "_tool_usage.json")
PROMPT_LOG = os.path.join(PIPEMIND_DIR, "memory", "_prompt_size.json")

# ── 性能监控 ──

def log_perf(action: str, duration: float, tokens: int = 0):
    """记录性能数据"""
    logs = []
    if os.path.exists(PERF_LOG):
        try:
            with open(PERF_LOG, "r") as f:
                logs = json.load(f)
        except Exception: pass
    
    logs.append({
        "time": datetime.datetime.now().isoformat(),
        "action": action,
        "duration_ms": round(duration * 1000),
        "tokens": tokens
    })
    
    # 只保留最近 1000 条
    logs = logs[-1000:]
    os.makedirs(os.path.dirname(PERF_LOG), exist_ok=True)
    with open(PERF_LOG, "w") as f:
        json.dump(logs, f)


def perf_report() -> str:
    """性能报告"""
    if not os.path.exists(PERF_LOG):
        return "📊 暂无性能数据"
    
    try:
        with open(PERF_LOG, "r") as f:
            logs = json.load(f)
    except Exception:
        return "📊 数据损坏"
    
    if not logs:
        return "📊 暂无性能数据"
    
    # 按 action 分组统计
    stats = {}
    for log in logs:
        act = log["action"]
        if act not in stats:
            stats[act] = {"count": 0, "total_ms": 0, "max_ms": 0}
        stats[act]["count"] += 1
        stats[act]["total_ms"] += log["duration_ms"]
        stats[act]["max_ms"] = max(stats[act]["max_ms"], log["duration_ms"])
    
    lines = ["📊 性能报告", f"   样本数: {len(logs)}", ""]
    
    # 按总耗时排序
    sorted_acts = sorted(stats.items(), key=lambda x: x[1]["total_ms"], reverse=True)
    for act, s in sorted_acts[:10]:
        avg = s["total_ms"] / s["count"]
        bar = "█" * min(20, int(avg / 100))
        lines.append(f"  {act:<20s} {bar} {avg:5.0f}ms avg | {s['max_ms']:5.0f}ms max | {s['count']}次")
    
    # 总体健康度
    avg_all = sum(s["total_ms"] for _, s in sorted_acts) / max(len(logs), 1)
    health = "✅ 健康" if avg_all < 3000 else ("⚠️ 偏慢" if avg_all < 8000 else "❌ 过慢")
    lines.append(f"\n  总体: {avg_all:.0f}ms avg → {health}")
    
    return "\n".join(lines)


# ── 工具使用统计 ──

def log_tool_usage(tool_name: str, success: bool):
    """记录工具使用"""
    usage = {}
    if os.path.exists(USAGE_LOG):
        try:
            with open(USAGE_LOG, "r") as f:
                usage = json.load(f)
        except Exception: pass
    
    if tool_name not in usage:
        usage[tool_name] = {"calls": 0, "success": 0, "fail": 0, "last_used": ""}
    
    usage[tool_name]["calls"] += 1
    if success:
        usage[tool_name]["success"] += 1
    else:
        usage[tool_name]["fail"] += 1
    usage[tool_name]["last_used"] = datetime.datetime.now().isoformat()
    
    with open(USAGE_LOG, "w") as f:
        json.dump(usage, f, indent=2)


def get_unused_tools(days: int = 14) -> list:
    """获取长时间未使用的工具"""
    if not os.path.exists(USAGE_LOG):
        return []
    try:
        with open(USAGE_LOG, "r") as f:
            usage = json.load(f)
    except Exception:
        return []
    
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
    unused = []
    for name, data in usage.items():
        if data["last_used"] < cutoff and data["calls"] < 3:
            unused.append(name)
    return unused


# ── 系统提示词优化 ──

def measure_prompt(prompt: str) -> dict:
    """测量提示词大小"""
    chars = len(prompt)
    # 粗略估计 token 数（中文 ~1.5 chars/token，英文 ~4 chars/token）
    chinese_chars = sum(1 for c in prompt if '\u4e00' <= c <= '\u9fff')
    english_chars = chars - chinese_chars
    estimated_tokens = int(chinese_chars * 1.5 + english_chars / 4)
    
    return {
        "chars": chars,
        "estimated_tokens": estimated_tokens,
        "health": "good" if estimated_tokens < 2000 else ("warn" if estimated_tokens < 4000 else "bad")
    }


def optimize_prompt(prompt: str, max_tokens: int = 2000) -> str:
    """优化提示词，控制在 token 预算内"""
    measurement = measure_prompt(prompt)
    if measurement["estimated_tokens"] <= max_tokens:
        return prompt  # 不需要优化
    
    # 需要压缩
    lines = prompt.split("\n")
    compressed = []
    skip_sections = ["详细说明", "详细描述"]
    in_skip = False
    
    for line in lines:
        # 跳过冗余说明部分
        if any(s in line for s in skip_sections):
            in_skip = True
            continue
        if line.startswith("## ") and in_skip:
            in_skip = False
        if in_skip:
            continue
        
        # 压缩长行
        if len(line) > 200:
            line = line[:197] + "..."
        
        compressed.append(line)
    
    result = "\n".join(compressed)
    
    # 如果还是太长，截断到 80%
    if measure_prompt(result)["estimated_tokens"] > max_tokens:
        ratio = max_tokens / measurement["estimated_tokens"]
        cut_at = int(len(result) * min(ratio, 0.8))
        result = result[:cut_at] + "\n\n[内容已自动压缩以保持响应速度]"
    
    return result


# ── 自动清理 ──

def auto_cleanup(force: bool = False) -> dict:
    """自动清理：删除无用文件、压缩日志、归档旧数据"""
    report = {"deleted_files": 0, "freed_bytes": 0, "archived": 0}
    
    # 1. 清理 __pycache__
    for root, dirs, files in os.walk(PIPEMIND_DIR):
        if "__pycache__" in dirs:
            pycache = os.path.join(root, "__pycache__")
            size = 0
            for f in os.listdir(pycache):
                fp = os.path.join(pycache, f)
                if os.path.isfile(fp):
                    size += os.path.getsize(fp)
            if force or size > 1024 * 1024:  # >1MB 才清
                shutil.rmtree(pycache)
                report["deleted_files"] += 1
                report["freed_bytes"] += size
    
    # 2. 压缩性能日志（只保留最近 100 条）
    if os.path.exists(PERF_LOG):
        try:
            with open(PERF_LOG, "r") as f:
                logs = json.load(f)
            if len(logs) > 100:
                with open(PERF_LOG, "w") as f:
                    json.dump(logs[-100:], f)
                report["archived"] += 1
        except Exception: pass
    
    # 3. 清理 output 目录中过期的结果文件（>30天）
    out_dir = os.path.join(PIPEMIND_DIR, "output")
    if os.path.exists(out_dir):
        cutoff = time.time() - 30 * 86400
        for f in os.listdir(out_dir):
            fp = os.path.join(out_dir, f)
            if os.path.isfile(fp) and os.path.getmtime(fp) < cutoff:
                sz = os.path.getsize(fp)
                os.remove(fp)
                report["deleted_files"] += 1
                report["freed_bytes"] += sz
    
    return report


# ── 代谢检查（主入口）──

def metabolism_check(conversation_count: int = 0) -> str:
    """代谢检查：性能 + 清理 + 提示词优化"""
    parts = []
    
    # 1. 性能检查
    if os.path.exists(PERF_LOG):
        parts.append(perf_report())
    
    # 2. 清理
    cleanup = auto_cleanup()
    if cleanup["deleted_files"] > 0:
        parts.append(f"🧹 清理: 删除了 {cleanup['deleted_files']} 个文件，释放 {cleanup['freed_bytes']/1024:.0f}KB")
    
    # 3. 工具使用检查
    unused = get_unused_tools(14)
    if unused:
        parts.append(f"💤 闲置工具 ({len(unused)} 个): {', '.join(unused[:5])}")
    
    return "\n\n".join(parts) if parts else "代谢正常"


def get_system_health() -> str:
    """系统健康度评分"""
    score = 100
    
    # 检查文件大小
    total_size = 0
    for root, dirs, files in os.walk(PIPEMIND_DIR):
        for f in files:
            fp = os.path.join(root, f)
            if os.path.isfile(fp) and not f.endswith('.pyc'):
                total_size += os.path.getsize(fp)
    
    if total_size > 5 * 1024 * 1024:
        score -= 20  # >5MB 扣分
    if total_size > 10 * 1024 * 1024:
        score -= 20
    
    # 检查性能
    if os.path.exists(PERF_LOG):
        try:
            with open(PERF_LOG, "r") as f:
                logs = json.load(f)
            recent = [l for l in logs if l["duration_ms"] > 10000]
            if len(recent) > 5:
                score -= 10 * min(3, len(recent) // 5)
        except Exception: pass
    
    grade = "S" if score >= 90 else ("A" if score >= 80 else ("B" if score >= 60 else "C"))
    return f"⚡ 健康度: {grade} ({score}/100) | 体积: {total_size/1024:.0f}KB"
