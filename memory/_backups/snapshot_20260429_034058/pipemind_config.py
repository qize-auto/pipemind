"""PipeMind — 配置管理器"""
import json, os

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
MEMORY_DIR = os.path.join(CONFIG_DIR, "memory")
SKILLS_DIR = os.path.join(CONFIG_DIR, "skills")
OUTPUT_DIR = os.path.join(CONFIG_DIR, "output")

_DEFAULTS = {
    "model": {
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "model_name": "deepseek-chat",
        "api_key": "",
        "max_tokens": 4096,
        "temperature": 0.7
    },
    "agent": {
        "max_turns": 50,
        "system_prompt": "你是 PipeMind，一个运行在 Windows 上的 AI 智能助手。请用简洁直接的方式回答问题。",
        "personality": ""
    },
    "tools": {
        "enabled": ["terminal", "file", "memory"]
    },
    "memory": {
        "enabled": True,
        "max_history": 100
    },
    "display": {
        "theme": "dark",
        "compact": False
    }
}


def load() -> dict:
    """加载配置"""
    if not os.path.exists(CONFIG_PATH):
        save(_DEFAULTS)
        return dict(_DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        # 合并默认值
        for k, v in _DEFAULTS.items():
            if k not in cfg:
                cfg[k] = v
            elif isinstance(v, dict):
                for k2, v2 in v.items():
                    if k2 not in cfg[k]:
                        cfg[k][k2] = v2
        return cfg
    except:
        return dict(_DEFAULTS)


def save(cfg: dict):
    """保存配置"""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_model_info(cfg: dict = None) -> dict:
    if cfg is None:
        cfg = load()
    return cfg.get("model", _DEFAULTS["model"])


def get_system_prompt(cfg: dict = None) -> str:
    if cfg is None:
        cfg = load()
    return cfg.get("agent", {}).get("system_prompt", _DEFAULTS["agent"]["system_prompt"])
