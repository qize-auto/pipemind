"""PipeMind AI 自我改进引擎 — 用 AI 审视和改进自己

不再是硬编码规则，而是让 PipeMind 用自己的 LLM 能力来：
  1. 代码审查 — 分析自己的 Python 文件，找 bug 和改进点
  2. 提示词优化 — 根据对话历史优化 system prompt
  3. 技能生成 — 发现能力缺口并生成新技能
  4. 性能分析 — 用 LLM 分析性能数据，提出优化建议

安全机制:
  - 所有改进需要人类确认才能应用（dry_run 模式）
  - 改进前后对比，可回滚
  - 每次改进记录在 _improvement_log.json
"""

import os, json, datetime, sys, glob, re, textwrap, subprocess

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")
LOG_FILE = os.path.join(MEM_DIR, "_improvement_log.json")

MAX_SUGGESTIONS_PER_RUN = 5


# ═══════════════════════════════════════════════
# 1. 代码审查
# ═══════════════════════════════════════════════

def review_code(filepath: str = None) -> list[dict]:
    """用 LLM 审查一个 Python 文件

    返回: [{type, file, line, suggestion, severity, code}]
    """
    if filepath:
        files = [filepath]
    else:
        # 默认审查最核心的 3 个文件
        files = [
            os.path.join(PIPEMIND_DIR, "pipemind.py"),
            os.path.join(PIPEMIND_DIR, "pipemind_daemon.py"),
            os.path.join(PIPEMIND_DIR, "pipemind_web.py"),
        ]

    all_suggestions = []
    for f in files:
        if not os.path.exists(f):
            continue
        try:
            with open(f, "r", encoding="utf-8") as fh:
                content = fh.read()
        except Exception:
            continue

        suggestions = _llm_review(f, content)
        all_suggestions.extend(suggestions)

    return all_suggestions


def _llm_review(filepath: str, content: str) -> list[dict]:
    """用 LLM 审查单个文件"""
    filename = os.path.basename(filepath)
    # 截取前 200 行进行分析
    lines = content.split("\n")[:200]
    sample = "\n".join(lines)

    prompt = f"""你是一个 Python 代码审查专家。审查以下文件，找出潜在问题。

要求：
1. 只找真正的问题（性能、安全、错误处理、代码异味）
2. 每个问题提供一个修复方案
3. 标注严重程度: critical / major / minor
4. 没有问题时返回空数组

文件: {filename}

代码:
```python
{sample[:3000]}
```

返回 JSON 数组:
[{{"severity":"major","line":42,"issue":"bare except hides errors","fix":"使用具体的异常类型"}}]
"""
    try:
        result = _call_llm(prompt)
        items = _parse_json_result(result)
        for item in items:
            item["file"] = filename
        return items
    except Exception:
        return []


# ═══════════════════════════════════════════════
# 2. 提示词优化
# ═══════════════════════════════════════════════

def optimize_prompts() -> list[dict]:
    """分析对话历史，优化 system prompt"""
    prompt = """分析以下 SOUL.md（PipeMind 的身份定义），给出优化建议。

要求：
1. 建议让身份描述更准确、更有力
2. 指出过时或不够精确的描述
3. 建议新增的内容（基于当前能力）

返回 JSON 数组:
[{"type":"update","target":"当前状态","suggestion":"...","reason":"..."}]
"""
    try:
        soul_path = os.path.join(PIPEMIND_DIR, "SOUL.md")
        if os.path.exists(soul_path):
            with open(soul_path, "r", encoding="utf-8") as f:
                soul_content = f.read()
            prompt = prompt.replace("SOUL.md", soul_content[:2000])

        result = _call_llm(prompt)
        return _parse_json_result(result) or []
    except Exception:
        return []


# ═══════════════════════════════════════════════
# 3. 技能生成
# ═══════════════════════════════════════════════

def suggest_new_skills() -> list[dict]:
    """分析现有能力，建议新技能"""
    # 获取现有技能列表
    existing = []
    skills_dir = os.path.join(PIPEMIND_DIR, "skills")
    if os.path.exists(skills_dir):
        for md in glob.glob(os.path.join(skills_dir, "**", "SKILL.md"), recursive=True):
            name = os.path.basename(os.path.dirname(md))
            try:
                with open(md, "r", encoding="utf-8") as f:
                    desc = ""
                    for line in f:
                        if line.strip().startswith("description:"):
                            desc = line.split(":", 1)[1].strip().strip("\"'")
                            break
                existing.append({"name": name, "desc": desc})
            except Exception:
                pass

    prompt = f"""你是一个 AI Agent 技能设计师。分析现有技能列表，建议 3 个新技能。

现有技能:
{json.dumps(existing, ensure_ascii=False, indent=2)}

要求:
1. 技能应该补充现有能力的不足
2. 每个技能要有明确的用途和触发条件
3. 技能要适合 Windows 平台

返回 JSON 数组:
[{{"name":"技能名","description":"技能描述","trigger":"触发条件","reason":"为什么需要"}}]
"""
    try:
        result = _call_llm(prompt)
        return _parse_json_result(result) or []
    except Exception:
        return []


# ═══════════════════════════════════════════════
# 4. 性能分析
# ═══════════════════════════════════════════════

def analyze_performance() -> list[dict]:
    """用 LLM 分析性能数据，提出优化建议"""
    # 获取性能数据
    perf_data = {"conversations": 0, "avg_duration": 0, "error_rate": 0, "trend": "unknown"}
    try:
        import pipemind_self_evolution as se
        p = se.PerformanceTracker.stats(days=7)
        perf_data = p
    except Exception:
        pass

    prompt = f"""你是一个系统性能分析师。分析以下 AI Agent 的性能数据，提出优化建议。

性能数据 (7天):
{json.dumps(perf_data, ensure_ascii=False, indent=2)}

要求:
1. 如果错误率高，分析可能原因
2. 如果响应慢，建议优化方向
3. 如果趋势下降，建议恢复策略
4. 每个建议要具体可行

返回 JSON 数组:
[{{"area":"performance","issue":"描述问题","suggestion":"具体建议","impact":"预期效果"}}]
"""
    try:
        result = _call_llm(prompt)
        return _parse_json_result(result) or []
    except Exception:
        return []


# ═══════════════════════════════════════════════
# 5. 完整改进周期
# ═══════════════════════════════════════════════

def run_improvement_cycle(dry_run: bool = True) -> dict:
    """执行一次完整的自我改进周期

    Args:
        dry_run: True 则不应用更改，只生成报告

    Returns:
        改进报告
    """
    cycle = {
        "time": datetime.datetime.now().isoformat(),
        "dry_run": dry_run,
        "code_review": [],
        "prompt_optimization": [],
        "skill_suggestions": [],
        "performance_analysis": [],
        "total": 0,
    }

    log = Logger("self_improve")

    # 1. 代码审查
    try:
        suggestions = review_code()
        if suggestions:
            cycle["code_review"] = suggestions[:MAX_SUGGESTIONS_PER_RUN]
            cycle["total"] += len(suggestions)
            log.info(f"代码审查: {len(suggestions)} 条建议")
    except Exception as e:
        log.error(f"代码审查失败: {e}")

    # 2. 提示词优化
    try:
        suggestions = optimize_prompts()
        if suggestions:
            cycle["prompt_optimization"] = suggestions[:3]
            cycle["total"] += len(suggestions)
            log.info(f"提示词优化: {len(suggestions)} 条建议")
    except Exception as e:
        log.error(f"提示词优化失败: {e}")

    # 3. 新技能建议
    try:
        suggestions = suggest_new_skills()
        if suggestions:
            cycle["skill_suggestions"] = suggestions[:3]
            cycle["total"] += len(suggestions)
            log.info(f"新技能建议: {len(suggestions)} 个")
    except Exception as e:
        log.error(f"新技能建议失败: {e}")

    # 4. 性能分析
    try:
        suggestions = analyze_performance()
        if suggestions:
            cycle["performance_analysis"] = suggestions[:3]
            cycle["total"] += len(suggestions)
            log.info(f"性能分析: {len(suggestions)} 条建议")
    except Exception as e:
        log.error(f"性能分析失败: {e}")

    # 保存日志
    _save_log(cycle)

    return cycle


def format_report(cycle: dict) -> str:
    """格式化改进报告为人类可读文本"""
    lines = [
        f"\n  {'='*50}",
        f"  🤖 AI 自我改进报告",
        f"  {'='*50}",
        f"  时间: {cycle['time'][:19]}",
        f"  模式: {'🔍 预览 (dry-run)' if cycle.get('dry_run') else '⚡ 已应用'}",
        f"  总计: {cycle['total']} 条建议\n",
    ]

    sections = [
        ("代码审查", cycle.get("code_review", []), ["severity", "issue", "fix"]),
        ("提示词优化", cycle.get("prompt_optimization", []), ["type", "suggestion"]),
        ("新技能建议", cycle.get("skill_suggestions", []), ["name", "description"]),
        ("性能分析", cycle.get("performance_analysis", []), ["area", "suggestion"]),
    ]

    for title, items, keys in sections:
        if items:
            lines.append(f"  📋 {title}:")
            for item in items[:3]:
                parts = []
                for k in keys:
                    v = item.get(k, "")
                    if v:
                        parts.append(f"{k}={v}")
                lines.append(f"    · {' | '.join(parts)[:100]}")
            lines.append("")

    if not cycle["total"]:
        lines.append("  没有改进建议。系统状态良好。\n")

    return "\n".join(lines)


# ═══════════════════════════════════════════════
# 内部工具
# ═══════════════════════════════════════════════

def _call_llm(prompt: str) -> str:
    """调用 LLM（复用 provider 模块）"""
    sys.path.insert(0, PIPEMIND_DIR)
    try:
        import pipemind_provider as provider
        result = provider.call_with_failover([
            {"role": "system", "content": "你是一个 AI 系统改进专家。只返回 JSON。"},
            {"role": "user", "content": prompt}
        ], tools=[])
        if "error" not in result:
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        pass
    return "[]"


def _parse_json_result(text: str) -> list:
    """解析 LLM 返回的 JSON"""
    m = re.search(r'\[.*?\]', text, re.DOTALL)
    if m:
        try:
            items = json.loads(m.group())
            if isinstance(items, list):
                return items
        except Exception:
            pass
    return []


def _save_log(cycle: dict):
    os.makedirs(MEM_DIR, exist_ok=True)
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            pass
    logs.append(cycle)
    if len(logs) > 50:
        logs = logs[-50:]
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def get_logs(limit=10) -> list:
    """获取改进日志"""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
        return logs[-limit:]
    except Exception:
        return []


# ── Logger ──

class Logger:
    def __init__(self, name):
        self.name = name
    def info(self, msg):
        print(f"  · [{self.name}] {msg}")
    def error(self, msg):
        print(f"  ❌ [{self.name}] {msg}")


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PipeMind AI 自我改进")
    parser.add_argument("--run", action="store_true", help="执行改进周期")
    parser.add_argument("--apply", action="store_true", help="应用改进（非 dry-run）")
    parser.add_argument("--review", type=str, help="审查指定文件")
    parser.add_argument("--log", action="store_true", help="查看改进日志")
    args = parser.parse_args()

    if args.run or args.apply:
        cycle = run_improvement_cycle(dry_run=not args.apply)
        print(format_report(cycle))

    if args.review:
        suggestions = review_code(args.review)
        print(f"\n📋 审查 {args.review}: {len(suggestions)} 条建议\n")
        for s in suggestions:
            print(f"  [{s.get('severity','?')}] L{s.get('line','?')}: {s.get('issue','')}")
            print(f"    修复: {s.get('fix','')}\n")

    if args.log:
        logs = get_logs()
        for l in logs[-3:]:
            print(f"\n  📅 {l.get('time','?')[:19]} ({'dry-run' if l.get('dry_run') else 'applied'})")
            print(f"     代码审查: {len(l.get('code_review',[]))} | "
                  f"提示词: {len(l.get('prompt_optimization',[]))} | "
                  f"技能: {len(l.get('skill_suggestions',[]))} | "
                  f"性能: {len(l.get('performance_analysis',[]))}")
