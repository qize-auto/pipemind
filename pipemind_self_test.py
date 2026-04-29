"""PipeMind — 自检系统 + 工具创建器"""
from pipemind_core import PIPEMIND_DIR, MEM_DIR
import os, sys, subprocess, json, datetime, textwrap, importlib, traceback

TOOLS_FILE = os.path.join(PIPEMIND_DIR, "pipemind_tools.py")
TEST_LOG = os.path.join(PIPEMIND_DIR, "memory", "_test_log.json")


# ── 自检系统 ──

def run_self_test() -> dict:
    """全面自检，返回报告"""
    report = {"passed": 0, "failed": 0, "warnings": 0, "details": []}
    
    def check(name: str, ok: bool, detail: str = ""):
        if ok:
            report["passed"] += 1
        else:
            report["failed"] += 1
        report["details"].append({"name": name, "ok": ok, "detail": detail})
    
    # 1. 语法检查
    for f in ["pipemind.py", "pipemind_tools.py", "pipemind_config.py", 
              "pipemind_evolution.py", "pipemind_diary.py", "pipemind_vision.py",
              "pipemind_voice.py", "pipemind_monitor.py", "pipemind_memory_plus.py",
              "pipemind_skills.py"]:
        fp = os.path.join(PIPEMIND_DIR, f)
        if os.path.exists(fp):
            try:
                compile(open(fp, encoding="utf-8").read(), fp, "exec")
                check(f"语法: {f}", True)
            except SyntaxError as e:
                check(f"语法: {f}", False, str(e))
        else:
            check(f"存在: {f}", False, "文件不存在")
    
    # 2. 工具注册检查
    try:
        import pipemind_tools as t
        tools = t.get_all_schemas()
        check(f"工具注册 ({len(tools)} 个)", len(tools) >= 5)
    except Exception as e:
        check("工具注册", False, str(e))
    
    # 3. 配置检查
    try:
        import pipemind_config as cfg
        c = cfg.load()
        has_key = bool(c.get("model", {}).get("api_key"))
        check("API Key 配置", has_key, "未配置 API Key" if not has_key else "")
    except Exception as e:
        check("配置加载", False, str(e))
    
    # 4. 记忆目录检查
    mem_dir = os.path.join(PIPEMIND_DIR, "memory")
    check("记忆目录", os.path.exists(mem_dir))
    
    # 5. 技能目录检查
    skills_dir = os.path.join(PIPEMIND_DIR, "skills")
    check("技能目录", os.path.exists(skills_dir))
    
    # 6. SOUL 检查
    soul = os.path.join(PIPEMIND_DIR, "SOUL.md")
    check("灵魂核心", os.path.exists(soul), "缺少 SOUL.md" if not os.path.exists(soul) else "")
    
    # 保存日志
    os.makedirs(os.path.dirname(TEST_LOG), exist_ok=True)
    report["time"] = datetime.datetime.now().isoformat()
    report["status"] = "healthy" if report["failed"] == 0 else "degraded"
    with open(TEST_LOG, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return report


def test_report() -> str:
    """人类可读的自检报告"""
    report = run_self_test()
    total = report["passed"] + report["failed"]
    
    status_icon = "✅" if report["status"] == "healthy" else "⚠️"
    lines = [
        f"\n  {status_icon} 自检报告 ({report['time'][:19]})",
        f"  通过: {report['passed']}/{total}  |  失败: {report['failed']}  |  警告: {report['warnings']}",
    ]
    for d in report["details"]:
        icon = "✅" if d["ok"] else "❌"
        detail = f" — {d['detail']}" if d["detail"] else ""
        lines.append(f"  {icon} {d['name']}{detail}")
    
    return "\n".join(lines)


# ── 工具创建器（自然语言→代码）──

def create_tool_from_description(name: str, description: str, params_desc: dict = None) -> str:
    """根据自然语言描述创建工具"""
    if params_desc is None:
        params_desc = {}
    
    # 生成函数体
    func_body = _generate_tool_code(name, description, params_desc)
    
    # 注册到 tools 文件
    return _register_tool(name, description, func_body, params_desc)


def _generate_tool_code(name: str, desc: str, params: dict) -> str:
    """生成工具函数体"""
    params_code = ", ".join([f"{k}: str = ''" for k in params.keys()]) if params else ""
    
    code = f"""def _{name}({params_code}):
    \"\"\"{desc}\"\"\"
    # Auto-generated tool by PipeMind
    try:
        {_indent_code(desc, name, params)}
    except Exception as e:
        return f"Error: {{e}}"
"""
    return code


def _indent_code(desc: str, name: str, params: dict) -> str:
    """根据描述生成实现代码"""
    desc_lower = desc.lower()
    
    # 根据描述关键词推断实现
    if "搜索" in desc_lower or "查找" in desc_lower or "find" in desc_lower:
        return """result = subprocess.run(f'findstr /M /S "{query}" *', shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout[:2000] or "(no matches)"
"""
    elif "下载" in desc_lower or "download" in desc_lower:
        return """import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "PipeMind/1.0"})
        resp = urllib.request.urlopen(req, timeout=30)
        content = resp.read()
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", url.split("/")[-1])
        with open(path, "wb") as f: f.write(content)
        return f"Downloaded {len(content)} bytes to {path}"
"""
    elif "压缩" in desc_lower or "zip" in desc_lower:
        return """import zipfile
        with zipfile.ZipFile(path, 'r') as z:
            z.extractall(os.path.dirname(path))
        return f"Extracted {path}"
"""
    elif "重命名" in desc_lower or "rename" in desc_lower:
        return """os.rename(old_name, new_name)
        return f"Renamed {old_name} -> {new_name}"
"""
    elif "通知" in desc_lower or "notify" in desc_lower:
        return """subprocess.run(f'powershell -Command "New-BurntToastNotification -Text \\\\"{title}\\\\", \\\\"{message}\\\\""', shell=True, capture_output=True, timeout=10)
        return f"Notification sent: {title}"
"""
    elif "计算" in desc_lower or "calc" in desc_lower:
        param_names = list(params.keys())
        return f"""result = eval(expression) if 'expression' in dir() else 0
        return f"Result: {{result}}"
"""
    
    # 默认：返回描述提示
    return f"""return f"Tool '{name}' executed. Params: {{locals()}}"
"""


def _register_tool(name: str, desc: str, func_code: str, params: dict) -> str:
    """注册工具到 pipemind_tools.py"""
    if not os.path.exists(TOOLS_FILE):
        return f"❌ {TOOLS_FILE} not found"
    
    # 构建注册代码
    properties = {}
    required = []
    for pname, pinfo in params.items():
        if isinstance(pinfo, dict):
            properties[pname] = pinfo
            if pinfo.get("required", False):
                required.append(pname)
        else:
            properties[pname] = {"type": "string", "description": str(pinfo)}
            required.append(pname)
    
    schema = json.dumps({"type": "object", "properties": properties, "required": required}, ensure_ascii=False)
    
    register_statement = f"""
# [AUTO] {name} — {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
{func_code}

register("{name}", _{name}, "{desc}", {schema})
"""
    
    # 追加到文件
    with open(TOOLS_FILE, "a", encoding="utf-8") as f:
        f.write(register_statement)
    
    return f"✅ 新工具 '{name}' 已创建并注册！"


def reimport_tools():
    """重新导入 tools 模块（让新工具立即可用）"""
    if "pipemind_tools" in sys.modules:
        del sys.modules["pipemind_tools"]
    import pipemind_tools as t
    return t
