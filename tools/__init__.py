"""PipeMind Tools — 工具扩展目录

在此目录下添加新工具模块，每个模块实现 register_all(register) 函数。
已有 68 个工具在 pipemind_tools.py 中。

用法示例 (tools/my_tool.py):
    def register_all(register):
        register("my_tool", _my_tool, "Description", {...})
        return 1
"""

from pipemind_core import PIPEMIND_DIR, MEM_DIR

_TOOLS = {}

def register(name, fn, description, parameters):
    _TOOLS[name] = {"fn": fn, "desc": description, "params": parameters}

def get_all_schemas() -> list[dict]:
    schemas = []
    for name, tool in _TOOLS.items():
        schemas.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool["desc"],
                "parameters": tool["params"]
            }
        })
    return schemas

def execute(name: str, args: dict) -> str:
    if name not in _TOOLS:
        return f"Error: unknown tool '{name}'"
    try:
        result = _TOOLS[name]["fn"](**args)
        return str(result)[:5000]
    except Exception as e:
        return f"Error: {e}"

def get_all_tools():
    return dict(_TOOLS)

def count():
    return len(_TOOLS)
