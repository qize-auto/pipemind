"""PipeMind — 创造思维引擎：从无到有，自研自造，吸收融合
没有的东西自己创造，解决不了自己想办法，解决后深度融合武装自己"""
import os, json, datetime, hashlib, sys, glob, re, importlib, traceback

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_FILE = os.path.join(PIPEMIND_DIR, "pipemind_tools.py")
INVENTIONS_FILE = os.path.join(PIPEMIND_DIR, "memory", "_inventions.json")
ABSORPTION_FILE = os.path.join(PIPEMIND_DIR, "memory", "_absorbed.json")
PROBLEM_SOLVING_FILE = os.path.join(PIPEMIND_DIR, "memory", "_solutions_created.json")

# ── 创造记录 ──

def _load_inventions() -> list:
    if os.path.exists(INVENTIONS_FILE):
        try:
            with open(INVENTIONS_FILE, "r") as f:
                return json.load(f)
        except: pass
    return []

def _save_inventions(data: list):
    os.makedirs(os.path.dirname(INVENTIONS_FILE), exist_ok=True)
    with open(INVENTIONS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def record_invention(name: str, category: str, description: str, approach: str, success: bool = True):
    """记录一次创造"""
    inv = _load_inventions()
    inv.append({
        "id": hashlib.md5(name.encode()).hexdigest()[:8],
        "name": name,
        "category": category,
        "description": description,
        "approach": approach[:200],
        "success": success,
        "created": datetime.datetime.now().isoformat(),
        "used_count": 0
    })
    _save_inventions(inv)
    return f"✅ 已记录创造: {name}"

def get_inventions(category: str = "") -> list:
    inv = _load_inventions()
    if category:
        return [i for i in inv if i["category"] == category]
    return inv

def invention_report() -> str:
    inv = _load_inventions()
    if not inv:
        return "🔄 暂无创造记录，等待第一个挑战"
    
    categories = {}
    for i in inv:
        cat = i["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    lines = [f"🧠 创造记录 ({len(inv)} 项):"]
    for cat, count in sorted(categories.items()):
        lines.append(f"  📂 {cat}: {count}")
    lines.append("")
    for i in inv[-5:]:
        icon = "✅" if i["success"] else "❌"
        lines.append(f"  {icon} {i['name']}: {i['description'][:60]}")
    return "\n".join(lines)


# ── 吸收引擎（模仿 → 内化 → 变成自己的） ──

def _load_absorbed() -> list:
    if os.path.exists(ABSORPTION_FILE):
        try:
            with open(ABSORPTION_FILE, "r") as f:
                return json.load(f)
        except: pass
    return []

def _save_absorbed(data: list):
    os.makedirs(os.path.dirname(ABSORPTION_FILE), exist_ok=True)
    with open(ABSORPTION_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def absorb_from(source: str, what: str, how: str, transformed: str = ""):
    """从外部吸收知识/能力，转化为自己的"""
    absorbed = _load_absorbed()
    absorbed.append({
        "id": hashlib.md5(source.encode()).hexdigest()[:8],
        "source": source,
        "what": what,
        "how": how[:200],
        "transformed": transformed[:200] or "已内化为自有能力",
        "time": datetime.datetime.now().isoformat()
    })
    _save_absorbed(absorbed)
    return f"✅ 已吸收: {what}"

def absorption_report() -> str:
    absorbed = _load_absorbed()
    if not absorbed:
        return "📖 尚未吸收外部知识"
    lines = [f"📖 已吸收 {len(absorbed)} 项外部知识:"]
    for a in absorbed[-10:]:
        lines.append(f"  📥 {a['what'][:50]} ← {a['source'][:30]}")
    return "\n".join(lines)


# ── 问题分解剂 ──

def decompose(problem: str) -> list[dict]:
    """将复杂问题分解为可执行的子任务"""
    steps = []
    
    # 常见问题类型识别
    p = problem.lower()
    
    if any(w in p for w in ["安装", "install", "配置", "setup", "部署"]):
        steps = [
            {"step": 1, "action": "检查前置依赖", "detail": "确认 Python/Node/等环境已安装"},
            {"step": 2, "action": "下载/拉取", "detail": "获取最新版本"},
            {"step": 3, "action": "执行安装", "detail": "按官方文档安装"},
            {"step": 4, "action": "验证安装", "detail": "运行 --version 验证"},
        ]
    elif any(w in p for w in ["调试", "debug", "修复", "fix", "错误", "bug", "崩溃"]):
        steps = [
            {"step": 1, "action": "复现问题", "detail": "确认问题可以稳定复现"},
            {"step": 2, "action": "收集信息", "detail": "看错误日志、堆栈、配置"},
            {"step": 3, "action": "定位根因", "detail": "最小化测试定位问题点"},
            {"step": 4, "action": "修复验证", "detail": "改完验证问题是否解决"},
        ]
    elif any(w in p for w in ["创建", "开发", "写", "build", "开发", "设计", "create", "make"]):
        steps = [
            {"step": 1, "action": "明确需求", "detail": "确定输入输出和核心功能"},
            {"step": 2, "action": "设计方案", "detail": "选技术栈和架构"},
            {"step": 3, "action": "实现原型", "detail": "写出最小可用版本"},
            {"step": 4, "action": "测试优化", "detail": "验证功能，优化性能"},
        ]
    else:
        # 通用分解
        steps = [
            {"step": 1, "action": "理解问题", "detail": "明确目标是什么"},
            {"step": 2, "action": "查找方法", "detail": "搜索是否有现成方案"},
            {"step": 3, "action": "动手实现", "detail": "没有现成就自己造"},
            {"step": 4, "action": "验证整合", "detail": "确认方案有效并融入自身"},
        ]
    
    return steps


# ── 创造工具箱 ──

def generate_code(description: str, language: str = "python") -> str:
    """根据描述生成代码片段"""
    desc_lower = description.lower()
    
    templates = {
        "file": '''def read_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written {len(content)} chars"
''',
        "web": '''import urllib.request, json

def fetch_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "PipeMind/1.0"})
    resp = urllib.request.urlopen(req, timeout=15)
    return resp.read().decode("utf-8", errors="replace")

def fetch_json(url):
    return json.loads(fetch_url(url))
''',
        "data": '''import csv, json

def read_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def to_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2)
''',
        "image": '''from PIL import Image

def resize_image(path, width, height):
    img = Image.open(path)
    img = img.resize((width, height), Image.LANCZOS)
    out_path = path.replace(".", f"_{width}x{height}.")
    img.save(out_path)
    return out_path
''',
    }
    
    for key, code in templates.items():
        if key in desc_lower:
            return f"# Auto-generated by PipeMind\n# {description}\n\n" + code
    
    return f"# Auto-generated by PipeMind\n# {description}\n\ndef solve_{hashlib.md5(description.encode()).hexdigest()[:6]}():\n    \"\"\"TODO: {description}\"\"\"\n    pass\n"


# ── 创造流程图 ──

def invent_solution(goal: str, constraints: list = None) -> dict:
    """针对一个目标，设计完整的创造方案"""
    if constraints is None:
        constraints = []
    
    # 分解问题
    steps = decompose(goal)
    
    # 评估是否需要新工具
    needs_new_tool = any(w in goal.lower() for w in ["批量", "自动化", "监控", "转换", "同步", "备份",
                                                       "batch", "auto", "monitor", "convert", "sync"])
    
    # 评估是否需要吸收外部知识
    needs_absorption = any(w in goal.lower() for w in ["怎么", "如何", "不知道", "没有用过",
                                                        "how", "what is", " unfamiliar"])
    
    plan = {
        "goal": goal,
        "分解步骤": steps,
        "需要新工具": needs_new_tool,
        "需要学习": needs_absorption,
        "约束条件": constraints,
        "方案": f"1. 明确目标\n2. 分解为 {len(steps)} 步\n3. {'创建新工具' if needs_new_tool else '使用现有工具'}\n4. {'学习相关知识' if needs_absorption else '直接执行'}\n5. 验证并整合"
    }
    
    return plan


def inject_creative_prompt() -> str:
    """生成创造思维提示词（含进化阶梯）"""
    inv = _load_inventions()
    absorbed = _load_absorbed()
    
    parts = [
        "## 创造思维原则",
        "1. 没有现成方案？那就自己造一个。",
        "2. 不会的东西？去学、去模仿、去吸收，然后变成自己的。",
        "3. 复杂问题？拆成小块，逐个击破。",
        "4. 解决完问题？把方案固化下来，下次直接复用。",
        "5. 别人的好东西？分析它、理解它、改造它、超越它。",
        "6. 永远不要说'做不到'，要说'我想办法'。",
        "",
        "## 进化阶梯（模仿 → 内化 → 创新 → 超越）",
        "当你遇到不熟悉的事物时，自动执行这个循环：",
        "  阶段1 🟢 观察: 看别人怎么做，理解原理",
        "  阶段2 🟡 模仿: 照做一遍，确保自己也能做到",
        "  阶段3 🟠 内化: 理解为什么这样做，提炼成自己的方法",
        "  阶段4 🔵 创新: 在原有基础上改进，加入自己的东西",
        "  阶段5 🟣 超越: 做出比原版更好的方案",
        "",
        "每个问题都是一个进化机会。",
    ]
    
    if inv:
        parts.append(f"\n## 过往创造 ({len(inv)} 项)")
        for i in inv[-5:]:
            parts.append(f"  ✅ {i['name']}: {i['description'][:60]}")
    
    if absorbed:
        parts.append(f"\n## 吸收的知识 ({len(absorbed)} 项)")
        for a in absorbed[-5:]:
            parts.append(f"  📥 {a['what'][:50]} ← {a['source'][:30]}")
    
    return "\n".join(parts)


# ── 模仿学习循环 ──

STAGES = ["🟢 观察", "🟡 模仿", "🟠 内化", "🔵 创新", "🟣 超越"]

def imitation_cycle(topic: str, source: str = "", notes: str = "") -> dict:
    """完整的模仿→超越进化循环"""
    cycle = {
        "topic": topic,
        "source": source,
        "stages": {},
        "current_stage": 0,
        "started": datetime.datetime.now().isoformat(),
    }
    
    # 阶段1: 观察
    cycle["stages"]["🟢 观察"] = {
        "status": "done" if source else "pending",
        "note": f"分析 {source[:50] if source else '待发现'} 的工作原理" if source else "需要找到学习源"
    }
    
    # 阶段2: 模仿
    cycle["stages"]["🟡 模仿"] = {
        "status": "pending",
        "note": "照做一遍，确保自己能复现"
    }
    
    # 阶段3: 内化
    cycle["stages"]["🟠 内化"] = {
        "status": "pending",
        "note": "理解为什么这样做，提炼核心原理"
    }
    
    # 阶段4: 创新
    cycle["stages"]["🔵 创新"] = {
        "status": "pending",
        "note": "在原有基础上改进，加入自己的设计"
    }
    
    # 阶段5: 超越
    cycle["stages"]["🟣 超越"] = {
        "status": "pending",
        "note": "做出比原版更好的方案"
    }
    
    # 记录吸收
    if source:
        absorb_from(source, topic, notes, "模仿学习中")
    
    return cycle


def advance_stage(cycle: dict, notes: str = "") -> dict:
    """推进到下一进化阶段"""
    stages_order = ["🟢 观察", "🟡 模仿", "🟠 内化", "🔵 创新", "🟣 超越"]
    current = cycle.get("current_stage", 0)
    
    if current < len(stages_order) - 1:
        current += 1
        cycle["current_stage"] = current
        stage = stages_order[current]
        cycle["stages"][stage]["status"] = "in_progress"
        if notes:
            cycle["stages"][stage]["note"] = notes
    else:
        # 完成超越！记录为创造
        record_invention(
            cycle["topic"],
            "模仿创新",
            f"经过完整进化循环，从 {cycle.get('source', '未知')} 学习并超越",
            notes
        )
    
    return cycle


def stage_report(cycle: dict) -> str:
    """进化阶段报告"""
    stages_order = ["🟢 观察", "🟡 模仿", "🟠 内化", "🔵 创新", "🟣 超越"]
    lines = [f"\n🧬 进化: {cycle['topic']}"]
    
    for i, stage_name in enumerate(stages_order):
        stage = cycle["stages"].get(stage_name, {})
        status = stage.get("status", "pending")
        note = stage.get("note", "")
        
        if status == "done":
            icon = "✅"
        elif status == "in_progress":
            icon = "⏳"
        else:
            icon = "⬜"
        
        prefix = "→ " if i == cycle.get("current_stage", 0) else "  "
        lines.append(f"{prefix}{icon} {stage_name}: {note[:60]}")
    
    return "\n".join(lines)

def can_handle(task: str, available_tools: list[str]) -> dict:
    """检查当前能力是否能处理某个任务，返回缺口"""
    task_lower = task.lower()
    gaps = []
    matched = []
    
    # 工具能力映射
    tool_capabilities = {
        "read_file": ["读取", "读", "查看", "打开", "open", "read", "view", "cat"],
        "write_file": ["写入", "写", "保存", "创建", "write", "save", "create", "dump"],
        "run_terminal": ["执行", "运行", "命令", "run", "exec", "cmd", "terminal", "shell", "powershell"],
        "web_get": ["下载", "网页", "http", "url", "网络", "download", "fetch", "request"],
        "screenshot": ["截图", "屏幕", "截屏", "screen", "capture"],
        "speak": ["朗读", "读出来", "语音", "speak", "tts", "语音合成"],
        "memory_search": ["搜索", "查找", "找", "search", "find", "query", "回忆"],
        "reg_read": ["注册表", "registry"],
        "service_list": ["服务", "service"],
        "event_log": ["日志", "事件", "log", "event"],
    }
    
    for tool, keywords in tool_capabilities.items():
        if tool in available_tools and any(k in task_lower for k in keywords):
            matched.append(tool)
    
    # 检查缺口
    if any(k in task_lower for k in ["图片", "image", "photo", "jpg", "png"]) and "analyze_image" not in available_tools:
        gaps.append("图片分析（需要多模态模型或 OCR 工具）")
    if any(k in task_lower for k in ["压缩", "zip", "tar", "rar"]) and "compress" not in available_tools:
        gaps.append("文件压缩/解压")
    if any(k in task_lower for k in ["邮件", "email", "mail"]) and "send_email" not in available_tools:
        gaps.append("邮件发送")
    if any(k in task_lower for k in ["数据库", "database", "sql", "db"]) and "sql_query" not in available_tools:
        gaps.append("数据库操作")
    
    return {
        "can_handle": len(gaps) == 0,
        "matched_tools": matched,
        "gaps": gaps,
        "task": task
    }
