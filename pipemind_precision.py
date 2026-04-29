"""PipeMind — 精准执行引擎：一次做对，不重复错误
目标导向思维 + 模式识别 + 防错预判 + 验证闭环
"""
import os, json, datetime, hashlib

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
PATTERNS_FILE = os.path.join(PIPEMIND_DIR, "memory", "_patterns.json")
SOLUTIONS_FILE = os.path.join(PIPEMIND_DIR, "memory", "_solutions.json")


# ── 模式识别库 ──

def _load_patterns() -> dict:
    if os.path.exists(PATTERNS_FILE):
        try:
            with open(PATTERNS_FILE, "r") as f:
                return json.load(f)
        except Exception: pass
    return {"patterns": [], "stats": {"total": 0, "success": 0, "fail": 0}}

def _save_patterns(data: dict):
    os.makedirs(os.path.dirname(PATTERNS_FILE), exist_ok=True)
    with open(PATTERNS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def register_pattern(name: str, signals: list, solution: str, risk: str = ""):
    """注册一个已知模式及其解决方案"""
    data = _load_patterns()
    pid = hashlib.md5(name.encode()).hexdigest()[:8]
    data["patterns"].append({
        "id": pid,
        "name": name,
        "signals": signals,       # 触发信号关键词
        "solution": solution,     # 经过验证的解决方案
        "risk": risk,             # 已知风险
        "success_count": 1,
        "fail_count": 0,
        "created": datetime.datetime.now().isoformat(),
        "last_used": datetime.datetime.now().isoformat()
    })
    data["stats"]["total"] += 1
    _save_patterns(data)
    return pid


def match_pattern(context: str) -> list[dict]:
    """根据当前上下文匹配已知模式"""
    data = _load_patterns()
    context_lower = context.lower()
    matches = []
    
    for p in data["patterns"]:
        score = 0
        for signal in p["signals"]:
            if signal.lower() in context_lower:
                score += 1
        if score > 0:
            matches.append((p, score / len(p["signals"])))
    
    matches.sort(key=lambda x: x[1], reverse=True)
    return [m[0] for m in matches[:3]]


def record_outcome(pattern_id: str, success: bool):
    """记录模式执行结果"""
    data = _load_patterns()
    for p in data["patterns"]:
        if p["id"] == pattern_id:
            if success:
                p["success_count"] += 1
                data["stats"]["success"] += 1
            else:
                p["fail_count"] += 1
                data["stats"]["fail"] += 1
            p["last_used"] = datetime.datetime.now().isoformat()
            break
    _save_patterns(data)


def get_best_solution(context: str) -> str | None:
    """根据上下文返回最佳解决方案"""
    matches = match_pattern(context)
    if matches:
        best = matches[0]
        # 只推荐成功率高的模式
        total = best["success_count"] + best["fail_count"]
        if total > 0 and best["success_count"] / total > 0.5:
            return best["solution"]
    return None


# ── 解决方案库 ──

def _load_solutions() -> dict:
    if os.path.exists(SOLUTIONS_FILE):
        try:
            with open(SOLUTIONS_FILE, "r") as f:
                return json.load(f)
        except Exception: pass
    return {"solutions": []}

def _save_solutions(data: dict):
    os.makedirs(os.path.dirname(SOLUTIONS_FILE), exist_ok=True)
    with open(SOLUTIONS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_solution(problem: str, approach: str, steps: list, verification: str = ""):
    """添加一个经过验证的解决方案"""
    data = _load_solutions()
    sid = hashlib.md5(problem.encode()).hexdigest()[:8]
    data["solutions"].append({
        "id": sid,
        "problem": problem,
        "approach": approach,
        "steps": steps,
        "verification": verification,
        "use_count": 0,
        "created": datetime.datetime.now().isoformat()
    })
    _save_solutions(data)
    return sid


def find_solution(problem: str) -> dict | None:
    """查找匹配的解决方案"""
    data = _load_solutions()
    problem_lower = problem.lower()
    best = None
    best_score = 0
    
    for s in data["solutions"]:
        score = 0
        keywords = (s["problem"] + " " + s["approach"]).lower()
        for word in problem_lower.split():
            if word in keywords:
                score += 1
        if score > best_score:
            best_score = score
            best = s
    
    if best and best_score >= 2:
        best["use_count"] += 1
        _save_solutions(data)
        return best
    return None


# ── 预检系统（行动前检查）──

def preflight_check(goal: str, planned_action: str) -> list[str]:
    """行动前预检，返回潜在风险列表"""
    risks = []
    goal_lower = goal.lower()
    action_lower = planned_action.lower()
    
    # 常见风险模式
    risk_patterns = [
        ("删除", ["删除", "删", "rm", "del", "remove"], "确认文件是否需要备份"),
        ("覆盖", ["覆盖", "覆写", "重写", "overwrite"], "确认是否保留原内容"),
        ("网络", ["下载", "curl", "wget", "request"], "网络可能不稳定，加超时和重试"),
        ("安装", ["install", "pip", "npm"], "确认环境兼容性，避免版本冲突"),
        ("写入", ["write", "写入", "保存"], "确认目标目录存在"),
        ("路径", ["path", "路径", "目录"], "Windows 路径用 \\\\ 或 raw string"),
        ("执行", ["exec", "运行", "run", "启动"], "确认 timeout，避免死锁"),
    ]
    
    combined = goal_lower + " " + action_lower
    for risk_name, keywords, advice in risk_patterns:
        if any(k in combined for k in keywords):
            risks.append(f"⚠ {risk_name}: {advice}")
    
    return risks


def optimize_plan(goal: str, steps: list[str]) -> list[str]:
    """优化执行步骤：去冗余、合并、排序"""
    if not steps:
        return steps
    
    # 去重
    seen = set()
    unique = []
    for step in steps:
        key = step.lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(step)
    
    # 识别并移除确认/验证步骤（这些应该在执行后做）
    execution = [s for s in unique if not any(w in s.lower() for w in ["确认", "检查", "验证", "看看"])]
    verification = [s for s in unique if any(w in s.lower() for w in ["确认", "检查", "验证", "看看"])]
    
    return execution + verification  # 先执行，后验证


# ── 命中率统计 ──

def accuracy_report() -> str:
    """精准度报告"""
    patterns = _load_patterns()
    sols = _load_solutions()
    
    total_p = patterns["stats"]["total"]
    success_p = patterns["stats"]["success"]
    fail_p = patterns["stats"]["fail"]
    rate = (success_p / (success_p + fail_p) * 100) if (success_p + fail_p) > 0 else 0
    
    lines = [
        f"🎯 精准度报告",
        f"   已注册模式: {total_p} 个",
        f"   可用方案: {len(sols['solutions'])} 个",
        f"   成功率: {success_p}/{success_p + fail_p} ({rate:.0f}%)" if (success_p + fail_p) > 0 else "   成功率: 暂无数据",
    ]
    
    # 高频率模式
    if patterns["patterns"]:
        sorted_p = sorted(patterns["patterns"], key=lambda x: x["success_count"], reverse=True)
        lines.append(f"\n   最可靠模式:")
        for p in sorted_p[:3]:
            total = p["success_count"] + p["fail_count"]
            r = p["success_count"] / total * 100 if total > 0 else 0
            lines.append(f"   ✅ {p['name']}: {r:.0f}% ({p['success_count']}/{total})")
    
    return "\n".join(lines)


def inject_precision_prompt() -> str:
    """生成精准执行提示词片段，注入 agent 系统提示"""
    patterns = _load_patterns()
    sols = _load_solutions()
    
    parts = [
        "## 精准执行原则",
        "1. 行动前先想三步：目标是什么？最佳路径是什么？可能哪里出错？",
        "2. 选最短路径执行，不要绕弯子",
        "3. 一次做对，不要靠试错迭代",
        "4. 如果发现走错了方向，立刻停下来重新规划",
        "5. 做完后验证结果是否符合预期",
    ]
    
    # 注入已知模式
    if patterns["patterns"]:
        parts.append("\n## 已验证的解决方案")
        for p in patterns["patterns"][:5]:  # 最多 5 条
            total = p["success_count"] + p["fail_count"]
            reliability = "✅" if p["fail_count"] == 0 else ("⚠️" if p["success_count"] > p["fail_count"] else "❌")
            parts.append(f"{reliability} {p['name']}: {p['solution'][:100]}")
    
    return "\n".join(parts)
