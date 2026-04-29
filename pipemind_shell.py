"""PipeMind Shell — 自然语言 Windows Shell

"帮我删掉昨天的日志" → 找到文件 → 确认 → 删除
"列出所有 Python 进程" → tasklist → 格式化输出

安全机制:
  - 读操作直接执行
  - 写/删操作需要二次确认
  - 危险命令（rm -rf / format disk）自动拦截
"""

import os, subprocess, json, datetime, re, sys, platform

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 安全规则 ──

DANGEROUS_PATTERNS = [
    r"rm\s+(-rf|-r|-f)\s+/",    # rm -rf /
    r"format\s+\w:",             # format C:
    r"del\s+/[fFsSqQ]",          # del /f
    r"rd\s+/[sSqQ]",             # rd /s
    r"shutdown",                 # shutdown
]

READ_COMMANDS = ["dir", "ls", "type", "cat", "find", "where", "tasklist", "netstat", "ipconfig", "systeminfo", "whoami", "help"]
WRITE_COMMANDS = ["del", "rm", "rd", "mkdir", "copy", "move", "ren", "echo", "set"]


def execute(command: str, auto_confirm: bool = False) -> str:
    """执行一条自然语言或 shell 命令

    Args:
        command: 自然语言指令或 shell 命令
        auto_confirm: 是否自动确认危险操作

    Returns:
        执行结果
    """
    # 安全检查
    is_dangerous = _check_dangerous(command)
    if is_dangerous:
        return "⛔ 检测到危险操作，已自动拦截"

    # 判断是自然语言还是直接命令
    if _is_natural_language(command):
        return _nl_execute(command)
    else:
        return _shell_execute(command, auto_confirm)


def _is_natural_language(text: str) -> bool:
    """判断是自然语言还是 shell 命令"""
    shell_patterns = ["dir ", "cd ", "type ", "copy ", "del ", "mkdir ",
                      "tasklist", "ipconfig", "netstat", "ping ", "find "]
    for p in shell_patterns:
        if text.lower().startswith(p):
            return False
    return True


def _check_dangerous(command: str) -> bool:
    """检查是否包含危险操作"""
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True
    return False


def _shell_execute(command: str, auto_confirm: bool) -> str:
    """执行 shell 命令"""
    cmd_type = _classify_command(command)

    # 写操作需要确认
    if cmd_type == "write" and not auto_confirm:
        return f"⚠ 写操作已暂缓: `{command}`\n   如需执行请添加 auto_confirm=True"

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout or result.stderr
        return output[:2000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "⏱ 命令执行超时 (30s)"
    except Exception as e:
        return f"❌ 执行失败: {e}"


def _classify_command(command: str) -> str:
    """分类命令类型: read / write / other"""
    cmd = command.strip().split()[0].lower() if command.strip() else ""
    if cmd in READ_COMMANDS:
        return "read"
    if cmd in WRITE_COMMANDS:
        return "write"
    return "other"


def _nl_execute(text: str) -> str:
    """解释自然语言指令并执行"""
    prompt = f"""你是一个 Windows Shell 解释器。将自然语言翻译为 Windows 命令。

要求:
1. 只输出命令本身，不要解释
2. 复杂的操作返回步骤列表
3. 无法理解时返回 "UNKNOWN"

自然语言: "{text}"
"""
    try:
        result = _call_llm(prompt)
        cmd = result.strip().split("\n")[0] if result else "UNKNOWN"

        if cmd == "UNKNOWN":
            return f"❌ 无法理解: {text}"

        # 安全检查
        if _check_dangerous(cmd):
            return "⛔ 检测到危险操作，已拦截"

        return _shell_execute(cmd, auto_confirm=False)
    except Exception as e:
        return f"❌ 解释失败: {e}"


def _call_llm(prompt: str) -> str:
    sys.path.insert(0, PIPEMIND_DIR)
    try:
        import pipemind_provider as provider
        result = provider.call_with_failover([
            {"role": "system", "content": "你是 Windows Shell 解释器。只输出命令。"},
            {"role": "user", "content": prompt}
        ], tools=[])
        if "error" not in result:
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception:
        pass
    return "UNKNOWN"


def get_shell_status() -> dict:
    """获取 Shell 环境状态"""
    return {
        "os": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "cwd": os.getcwd(),
        "read_only": len(READ_COMMANDS),
        "write_protected": len(WRITE_COMMANDS),
        "dangerous_blocked": len(DANGEROUS_PATTERNS),
    }
