"""PipeMind 离线模式 — 本地模型兜底

当 API 不可用时，自动切换到本地模型 (ollama) 处理基础请求。
"""

import os, json, datetime, sys, subprocess, threading, time

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")

_status = {
    "online": True,
    "api_failures": 0,
    "using_local": False,
    "local_model": "",
    "last_api_check": None,
    "cached_responses": 0,
}

# ── 状态检测 ──

def check_api_health() -> bool:
    """检测 API 是否可用"""
    try:
        cfg_file = os.path.join(PIPEMIND_DIR, "config.json")
        if not os.path.exists(cfg_file):
            return False
        cfg = json.load(open(cfg_file, encoding="utf-8"))
        model = cfg.get("model", {})
        api_key = model.get("api_key", "")
        base_url = model.get("base_url", "").rstrip("/")
        model_name = model.get("model_name", "deepseek-chat")

        if not api_key:
            return False

        import urllib.request
        body = json.dumps({
            "model": model_name,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        }).encode()
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        return "choices" in json.loads(resp.read().decode())
    except Exception:
        return False


def get_status() -> dict:
    return dict(_status)


# ── 本地模型 ──

def is_ollama_available() -> bool:
    """检查 ollama 是否可用"""
    try:
        r = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10
        )
        return r.returncode == 0
    except Exception:
        return False


def get_local_models() -> list:
    """获取本地已安装的模型列表"""
    try:
        r = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10
        )
        if r.returncode != 0:
            return []
        models = []
        for line in r.stdout.strip().split("\n")[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except Exception:
        return []


def chat_local(messages: list, model: str = "llama3.2:3b") -> dict:
    """使用本地模型处理请求"""
    try:
        import json
        prompt = "\n".join(m.get("content", "") for m in messages[-3:])

        r = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode == 0:
            return {
                "choices": [{
                    "message": {"role": "assistant", "content": r.stdout.strip()}
                }]
            }
        return {"error": f"ollama 返回错误: {r.stderr[:200]}"}
    except Exception as e:
        return {"error": str(e)}


# ── 自适应切换 ──

def auto_switch():
    """自动检测并切换模式"""
    global _status

    online = check_api_health()
    _status["online"] = online
    _status["last_api_check"] = datetime.datetime.now().isoformat()

    if online:
        _status["api_failures"] = 0
        if _status["using_local"]:
            _status["using_local"] = False
        return "online"
    else:
        _status["api_failures"] += 1
        # 连续失败 2 次才切换
        if _status["api_failures"] >= 2:
            if is_ollama_available():
                _status["using_local"] = True
                models = get_local_models()
                _status["local_model"] = models[0] if models else "llama3.2:3b"
                return f"switched_to_local:{_status['local_model']}"
            else:
                _status["using_local"] = False
                return "offline_no_local"
        return "api_unstable"
