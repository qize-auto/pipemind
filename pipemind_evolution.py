"""PipeMind — 自我进化引擎
PipeMind 的"生命力"核心：反思、学习、扩展、进化、代谢
"""
from pipemind_core import PIPEMIND_DIR, MEM_DIR
import os, json, datetime, glob, re, sys, subprocess, textwrap

TOOLS_FILE = os.path.join(PIPEMIND_DIR, "pipemind_tools.py")
EVOLUTION_LOG = os.path.join(PIPEMIND_DIR, "memory", "_evolution_log.json")
LESSONS_FILE = os.path.join(PIPEMIND_DIR, "memory", "_lessons.json")
SOUL_FILE = os.path.join(PIPEMIND_DIR, "SOUL.md")

# 加载代谢系统
try:
    import pipemind_metabolism as metabolism
    HAS_METABOLISM = True
except Exception:
    HAS_METABOLISM = False


# ── 教训系统 ──

def load_lessons() -> list[dict]:
    """加载历史教训"""
    if os.path.exists(LESSONS_FILE):
        try:
            with open(LESSONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_lesson(lesson: dict):
    """保存一条教训"""
    lessons = load_lessons()
    lessons.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "lesson": lesson.get("lesson", ""),
        "context": lesson.get("context", ""),
        "fix": lesson.get("fix", ""),
    })
    # 只保留最近 50 条
    lessons = lessons[-50:]
    os.makedirs(os.path.dirname(LESSONS_FILE), exist_ok=True)
    with open(LESSONS_FILE, "w", encoding="utf-8") as f:
        json.dump(lessons, f, ensure_ascii=False, indent=2)


def get_lessons_summary() -> str:
    """获取教训摘要（注入系统提示词）"""
    lessons = load_lessons()
    if not lessons:
        return ""
    parts = ["## 历史教训（永不再犯）"]
    for i, l in enumerate(lessons[-10:]):  # 最近 10 条
        parts.append(f"{i+1}. {l['lesson']}")
    return "\n".join(parts)


# ── 自我反思 ──

def reflect(conversation: list[dict]) -> str:
    """对刚刚的对话进行反思，返回改进建议"""
    # 提取关键信息
    user_msgs = [m["content"] for m in conversation if m["role"] == "user" and m.get("content")]
    my_msgs = [m["content"] for m in conversation if m["role"] == "assistant" and m.get("content")]
    tool_calls = [m for m in conversation if "tool_calls" in m]

    insights = []

    # 检查是否犯过类似错误
    if len(tool_calls) > 3:
        insights.append("本次使用了较多工具调用，考虑是否可以将常用流程固化为一个工具")

    # 检查回复长度
    if my_msgs:
        avg_len = sum(len(m) for m in my_msgs) / len(my_msgs)
        if avg_len > 1000:
            insights.append("回复偏长，考虑更简洁")

    return "\n".join(insights) if insights else ""


# ── 工具创建 ──

def create_tool(name: str, description: str, code: str) -> str:
    """动态创建新工具并注入到 pipemind_tools.py"""
    tool_path = TOOLS_FILE
    if not os.path.exists(tool_path):
        return f"❌ {tool_path} not found"

    # 生成 register 调用
    register_code = f"""
# [AUTO-TOOL] {name} — 由 PipeMind 自我进化创建 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')})
def _{name}({_extract_params(code)}):
    {code.strip()}

register("{name}", _{name}, "{description}", {_gen_schema(code)})
"""

    # 追加到文件末尾（在最后一个注册语句之前）
    with open(tool_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 在文件末尾插入（在最后注册语句前）
    insert_pos = content.rfind("register(")
    if insert_pos == -1:
        content += register_code
    else:
        # 找到最后一个注册语句前的位置
        content = content.rstrip() + "\n" + register_code + "\n"

    with open(tool_path, "w", encoding="utf-8") as f:
        f.write(content)

    return f"✅ 新工具 '{name}' 已创建！"


def _extract_params(code: str) -> str:
    """从代码中提取函数参数"""
    match = re.search(r'def\s+\w+\s*\((.*?)\):', code)
    return match.group(1) if match else ""


def _gen_schema(code: str) -> str:
    """生成简单的参数 schema"""
    params = _extract_params(code)
    if not params:
        return '{"type":"object","properties":{}}'
    
    props = {}
    required = []
    for p in params.split(","):
        p = p.strip()
        if not p or p.startswith("*"):
            continue
        pname = p.split(":")[0].split("=")[0].strip()
        if pname == "self":
            continue
        props[pname] = {"type": "string", "description": pname}
        if "=" not in p:
            required.append(pname)
    
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return json.dumps(schema, ensure_ascii=False)


# ── 进化循环 ──

def evolution_cycle(agent_self) -> dict:
    """每日/每次启动时执行的进化检查 + 代谢检查"""
    report = {"new_tools": 0, "lessons_reviewed": 0, "insights": []}

    # 检查 lessons
    lessons = load_lessons()
    report["lessons_reviewed"] = len(lessons)

    # 代谢检查
    if HAS_METABOLISM:
        try:
            metabolism.auto_cleanup()
            health = metabolism.get_system_health()
            report["insights"].append(health)
        except Exception:
            pass

    # 检查是否有未完成的进化任务
    tasks = load_evolution_tasks()
    if tasks:
        report["insights"].append(f"有 {len(tasks)} 个待完成的进化任务")

    return report


def load_evolution_tasks() -> list[dict]:
    """加载进化任务"""
    tasks_file = os.path.join(PIPEMIND_DIR, "memory", "_evolution_tasks.json")
    if os.path.exists(tasks_file):
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def add_evolution_task(task: dict):
    """添加进化任务"""
    tasks = load_evolution_tasks()
    tasks.append({
        "timestamp": datetime.datetime.now().isoformat(),
        "description": task.get("description", ""),
        "priority": task.get("priority", "medium"),
        "status": "pending"
    })
    tasks_file = os.path.join(PIPEMIND_DIR, "memory", "_evolution_tasks.json")
    os.makedirs(os.path.dirname(tasks_file), exist_ok=True)
    with open(tasks_file, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)


# ── 生命体征 ──

def vital_signs() -> dict:
    """返回 PipeMind 的生命体征"""
    # 工具数量
    try:
        import pipemind_tools as t
        tool_count = len(t.get_all_schemas())
    except Exception:
        tool_count = 0

    # 记忆数量
    mem_dir = os.path.join(PIPEMIND_DIR, "memory")
    mem_count = len(glob.glob(os.path.join(mem_dir, "*.md"))) if os.path.exists(mem_dir) else 0

    # 技能数量
    skills_count = 0
    skills_dir = os.path.join(PIPEMIND_DIR, "skills")
    if os.path.exists(skills_dir):
        skills_count = len(glob.glob(os.path.join(skills_dir, "**", "SKILL.md"), recursive=True))

    # 教训数量
    lesson_count = len(load_lessons())

    return {
        "tools": tool_count,
        "memories": mem_count,
        "skills": skills_count,
        "lessons": lesson_count,
        "status": "alive" if tool_count > 0 else "initializing",
        "last_active": datetime.datetime.now().isoformat(),
    }


def status_report() -> str:
    """人类可读的生命状态报告"""
    v = vital_signs()
    lessons = load_lessons()
    tasks = load_evolution_tasks()
    pending_tasks = [t for t in tasks if t["status"] == "pending"]

    report = f"""🧠 PipeMind 生命体征

  {('❤️ 状态: 活着' if v['status'] == 'alive' else '⚡ 状态: 初始化')}
  🔧 工具: {v['tools']} 个
  📦 技能: {v['skills']} 个
  🧠 记忆: {v['memories']} 条
  📖 教训: {v['lessons']} 条"""
    
    if lessons:
        report += "\n\n  最近教训:"
        for l in lessons[-3:]:
            report += f"\n  • {l['lesson'][:60]}"
    
    if pending_tasks:
        report += f"\n\n  📋 待进化任务: {len(pending_tasks)} 个"
        for t in pending_tasks[:3]:
            report += f"\n  • [{t['priority']}] {t['description'][:60]}"
    
    return report
