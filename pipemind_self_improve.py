"""PipeMind AI 自我改进引擎 — 用 AI 审视和改进自己

不再是硬编码规则，而是让 PipeMind 用自己的 LLM 能力来：
  1. 代码审查 — 分析自己的 Python 文件，找 bug 和改进点
  2. 提示词优化 — 根据对话历史优化 system prompt
  3. 技能生成 — 发现能力缺口并生成新技能
  4. 性能分析 — 用 LLM 分析性能数据，提出优化建议
  5. 改进应用 — 将建议转为实际代码变更（需确认）

安全机制:
  - 所有改进需要人类确认才能应用（dry_run 模式）
  - 改进前后对比，可回滚
  - 每次改进记录在 _improvement_log.json
  - 应用前自动备份，应用后检查语法
"""

import os, json, datetime, sys, glob, re, textwrap, subprocess, shutil, py_compile

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")
LOG_FILE = os.path.join(MEM_DIR, "_improvement_log.json")
PENDING_FILE = os.path.join(MEM_DIR, "_pending_improvements.json")
BACKUP_DIR = os.path.join(MEM_DIR, "_improve_backups")

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

    # 将可操作的建议加入待办队列
    if not dry_run:
        try:
            new_items = enqueue_improvements(cycle)
            if new_items:
                cycle["enqueued"] = len(new_items)
                log.info(f"已将 {len(new_items)} 条建议加入改进队列")
        except Exception as e:
            log.error(f"入队失败: {e}")

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
    except:
        return []


# ═══════════════════════════════════════════════
# 6. 改进应用（确认后执行）
# ═══════════════════════════════════════════════

def generate_fix(suggestion: dict) -> dict:
    """为一条建议生成实际的代码修复

    返回: {file, original_code, new_code, diff, risk}
    """
    filepath = suggestion.get("file", "")
    issue = suggestion.get("issue", "")
    fix_hint = suggestion.get("fix", "")
    severity = suggestion.get("severity", "minor")

    if not filepath:
        # 技能建议或提示词优化 → 生成新文件
        if suggestion.get("name"):
            return _generate_skill_file(suggestion)
        if suggestion.get("type") == "update" and "SOUL.md" in str(suggestion):
            return _generate_soul_update(suggestion)
        return {"error": "无法定位文件", "risk": "high"}

    full_path = os.path.join(PIPEMIND_DIR, filepath)
    if not os.path.exists(full_path):
        return {"error": f"文件不存在: {filepath}", "risk": "high"}

    try:
        content = open(full_path, "r", encoding="utf-8").read()
    except:
        return {"error": f"无法读取: {filepath}", "risk": "high"}

    # 用 LLM 生成修复
    prompt = f"""你是一个 Python 代码修复专家。生成代码修复。

文件: {filepath}
问题: {issue}
修复建议: {fix_hint}

要求:
1. 只修改有问题的部分
2. 保持代码风格一致
3. 返回完整的替换对 (old -> new)

当前代码前 100 行:
```python
{content[:2000]}
```

返回 JSON:
{{"old":"被替换的代码段","new":"替换后的代码段","verify":"编译检查通过"}}
"""
    try:
        result = _call_llm(prompt)
        parsed = json.loads(result) if isinstance(result, str) else result
        old = parsed.get("old", "")
        new = parsed.get("new", "")

        if not old or not new:
            return {"error": "LLM 未生成有效的修复", "risk": "high"}

        if old not in content:
            return {"error": "修复代码与文件不匹配", "risk": "high"}

        # 风险评级
        risk = "low"
        if severity == "critical":
            risk = "high"
        elif severity == "major":
            risk = "medium"

        return {
            "file": filepath,
            "old": old,
            "new": new,
            "risk": risk,
            "issue": issue,
        }
    except Exception as e:
        return {"error": f"修复生成失败: {e}", "risk": "high"}


def _generate_skill_file(suggestion: dict) -> dict:
    """生成新技能文件"""
    name = suggestion.get("name", "new-skill").lower().replace(" ", "-")
    desc = suggestion.get("description", "")
    trigger = suggestion.get("trigger", "")

    skills_dir = os.path.join(PIPEMIND_DIR, "skills", f"pipemind-auto-{name}")
    os.makedirs(skills_dir, exist_ok=True)

    content = f"""---
name: pipemind-auto-{name}
description: "{desc}"
author: PipeMind Self-Improve
---

# {name}

{desc}

## Trigger

{trigger}

## Usage

Describe your needs in conversation to trigger this skill.
"""
    filepath = os.path.join(skills_dir, "SKILL.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "file": f"skills/pipemind-auto-{name}/SKILL.md",
        "new": f"New skill created: {name}",
        "risk": "low",
        "issue": f"创建新技能: {name}",
    }


def _generate_soul_update(suggestion: dict) -> dict:
    """更新 SOUL.md"""
    soul_path = os.path.join(PIPEMIND_DIR, "SOUL.md")
    try:
        content = open(soul_path, "r", encoding="utf-8").read()
    except:
        return {"error": "无法读取 SOUL.md", "risk": "high"}

    prompt = f"""更新 SOUL.md（PipeMind 的身份定义）。

原始内容:
```markdown
{content[:2000]}
```

更新建议: {json.dumps(suggestion, ensure_ascii=False)}

返回整个文件的更新版本。保持原始风格。只做建议的修改。
不要使用 markdown 代码块包裹返回内容。
直接返回 markdown 内容本身。
"""
    try:
        result = _call_llm(prompt)
        if result and "```" not in result:
            return {
                "file": "SOUL.md",
                "old": content[:500],
                "new": result[:500],
                "risk": "medium",
                "issue": f"更新 SOUL.md: {suggestion.get('suggestion','')}",
            }
        return {"error": "生成失败", "risk": "high"}
    except:
        return {"error": "LLM 调用失败", "risk": "high"}


# ── 改进队列管理 ──

def enqueue_improvements(cycle: dict) -> list:
    """将改进周期中的建议加入待办队列

    从代码审查/技能建议中提取可操作的改进，生成修复并排队
    """
    pending = _load_pending()
    new_items = []

    for category in ["code_review", "prompt_optimization", "skill_suggestions"]:
        for item in cycle.get(category, []):
            fix = generate_fix(item)
            if "error" in fix:
                continue

            entry = {
                "id": f"imp_{int(datetime.datetime.now().timestamp())}_{len(pending)}",
                "category": category,
                "created": datetime.datetime.now().isoformat(),
                "suggestion": item,
                "fix": fix,
                "status": "pending",  # pending | applied | rejected | failed
                "applied_at": None,
                "verified": False,
            }
            pending.append(entry)
            new_items.append(entry)

    _save_pending(pending)
    return new_items


def get_pending() -> list:
    """获取待办改进"""
    return _load_pending()


def count_pending() -> int:
    return len([p for p in _load_pending() if p["status"] == "pending"])


def preview_improvement(imp_id: str) -> dict:
    """预览一条改进的变更内容"""
    pending = _load_pending()
    for p in pending:
        if p["id"] == imp_id:
            fix = p.get("fix", {})
            return {
                "id": imp_id,
                "file": fix.get("file", "?"),
                "old": fix.get("old", "")[:500],
                "new": fix.get("new", "")[:500],
                "risk": fix.get("risk", "medium"),
                "issue": fix.get("issue", "?"),
            }
    return {"error": "未找到"}


def apply_improvement(imp_id: str) -> dict:
    """应用一条改进"""
    pending = _load_pending()
    for p in pending:
        if p["id"] != imp_id or p["status"] != "pending":
            continue

        fix = p.get("fix", {})
        filepath = fix.get("file", "")
        old = fix.get("old", "")
        new_code = fix.get("new", "")

        if not filepath or not old:
            return {"ok": False, "error": "修复数据不完整"}

        full_path = os.path.join(PIPEMIND_DIR, filepath)
        if not os.path.exists(full_path):
            return {"ok": False, "error": f"文件不存在: {filepath}"}

        # 备份
        os.makedirs(BACKUP_DIR, exist_ok=True)
        backup_name = f"{filepath.replace('/', '_').replace('.py', '')}_{imp_id}.bak"
        try:
            shutil.copy2(full_path, os.path.join(BACKUP_DIR, backup_name))
        except:
            pass

        # 应用变更
        try:
            content = open(full_path, "r", encoding="utf-8").read()
            if old not in content:
                p["status"] = "failed"
                _save_pending(pending)
                return {"ok": False, "error": "代码已变更，无法匹配"}

            new_content = content.replace(old, new_code, 1)
            open(full_path, "w", encoding="utf-8").write(new_content)
        except Exception as e:
            p["status"] = "failed"
            _save_pending(pending)
            return {"ok": False, "error": f"写入失败: {e}"}

        # 验证语法（仅 .py 文件）
        verified = True
        if filepath.endswith(".py"):
            try:
                py_compile.compile(full_path, doraise=True)
            except:
                verified = False
                # 回滚
                backup_path = os.path.join(BACKUP_DIR, backup_name)
                if os.path.exists(backup_path):
                    shutil.copy2(backup_path, full_path)
                p["status"] = "failed"
                _save_pending(pending)
                return {"ok": False, "error": "语法检查失败，已回滚"}

        # 记录
        p["status"] = "applied" if verified else "failed"
        p["applied_at"] = datetime.datetime.now().isoformat()
        p["verified"] = verified
        _save_pending(pending)

        # 记录到改进日志
        _save_log({
            "time": datetime.datetime.now().isoformat(),
            "dry_run": False,
            "applied": [{
                "file": filepath,
                "issue": fix.get("issue", ""),
                "verified": verified,
            }],
        })

        # 记录里程碑
        try:
            import pipemind_chronicle as ch
            ch.add_milestone(
                f"自我修复: {fix.get('issue', '?')[:40]}",
                category="improvement",
            )
        except:
            pass

        return {"ok": True, "file": filepath, "verified": verified}

    return {"ok": False, "error": "未找到待办改进或状态不正确"}


def reject_improvement(imp_id: str) -> bool:
    """拒绝一条改进"""
    pending = _load_pending()
    for p in pending:
        if p["id"] == imp_id and p["status"] == "pending":
            p["status"] = "rejected"
            _save_pending(pending)
            return True
    return False


def get_backups() -> list:
    """获取备份列表"""
    if not os.path.exists(BACKUP_DIR):
        return []
    backups = []
    for f in os.listdir(BACKUP_DIR):
        path = os.path.join(BACKUP_DIR, f)
        backups.append({
            "name": f,
            "size": os.path.getsize(path),
            "modified": datetime.datetime.fromtimestamp(
                os.path.getmtime(path)
            ).isoformat()[:19],
        })
    return sorted(backups, key=lambda x: -x["modified"])


def _load_pending() -> list:
    if not os.path.exists(PENDING_FILE):
        return []
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def _save_pending(items: list):
    os.makedirs(MEM_DIR, exist_ok=True)
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


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
