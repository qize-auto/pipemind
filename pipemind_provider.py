"""PipeMind 多 Provider 引擎 — 自动降级 + 失败切换

支持多 API 配置，主线路挂了自动切备用。

用法:
  python pipemind_provider.py --list     # 查看所有 provider
  python pipemind_provider.py --switch   # 切换默认
  python pipemind_provider.py --test     # 测试连通性
"""

import json, os, time, urllib.request, urllib.error, socket

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PIPEMIND_DIR, "config.json")

# ── 默认 Provider 列表 ──────────────────────────

DEFAULT_PROVIDERS = [
    {
        "name": "DeepSeek",
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_key": "",
        "priority": 1,
        "enabled": True,
        "timeout": 60,
    },
    {
        "name": "DeepSeek备用",
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-v3.2",
        "api_key": "",
        "priority": 2,
        "enabled": True,
        "timeout": 60,
    },
]

# ── 加载 Provider ──────────────────────────────

def load_providers():
    """从 config.json 加载 provider 列表"""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except:
        cfg = {}
    
    providers = cfg.get("providers", [])
    
    # 如果没有配置 provider 列表，从 model 段构建
    if not providers:
        model = cfg.get("model", {})
        if model.get("api_key"):
            providers = [{
                "name": "default",
                "provider": model.get("provider", "deepseek"),
                "base_url": model.get("base_url", "https://api.deepseek.com/v1"),
                "model": model.get("model_name", "deepseek-chat"),
                "api_key": model["api_key"],
                "priority": 1,
                "enabled": True,
                "timeout": model.get("timeout", 60),
            }]
    
    return providers

def save_providers(providers):
    """保存 provider 列表到 config.json"""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
    except:
        cfg = {}
    
    cfg["providers"] = providers
    # 同时更新顶层的 model 段（兼容旧代码）
    if providers:
        p = providers[0]
        cfg["model"] = {
            "provider": p.get("provider", "deepseek"),
            "base_url": p.get("base_url", ""),
            "model_name": p.get("model", ""),
            "api_key": p.get("api_key", ""),
            "max_tokens": cfg.get("model", {}).get("max_tokens", 4096),
            "temperature": cfg.get("model", {}).get("temperature", 0.7),
        }
    
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# ── 测试连通性 ──────────────────────────────────

def test_provider(provider):
    """测试单个 provider 的连通性"""
    if not provider.get("api_key"):
        return {"name": provider["name"], "status": "no_key", "latency": 0}
    
    body = json.dumps({
        "model": provider["model"],
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }).encode()
    
    t0 = time.time()
    try:
        req = urllib.request.Request(
            f"{provider['base_url'].rstrip('/')}/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {provider['api_key']}"
            }
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        latency = time.time() - t0
        if "choices" in resp:
            return {"name": provider["name"], "status": "ok", "latency": round(latency, 2)}
        else:
            return {"name": provider["name"], "status": "error", "latency": round(latency, 2),
                    "detail": str(resp.get("error", ""))[:80]}
    except Exception as e:
        latency = time.time() - t0
        return {"name": provider["name"], "status": "fail", "latency": round(latency, 2),
                "detail": str(e)[:80]}

# ── API 调用（含自动降级） ─────────────────────

_current_failover_index = 0

def call_with_failover(messages, tools=None, max_retries=2):
    """调用 API，主 provider 失败自动切到下一个"""
    global _current_failover_index
    
    providers = load_providers()
    enabled = [p for p in providers if p.get("enabled", True) and p.get("api_key")]
    
    if not enabled:
        return {"error": "无可用 Provider，请配置 API Key"}
    
    # 从上次成功的位置开始
    start_idx = _current_failover_index % len(enabled)
    
    for offset in range(len(enabled)):
        idx = (start_idx + offset) % len(enabled)
        p = enabled[idx]
        
        for attempt in range(max_retries + 1):
            try:
                body = json.dumps({
                    "model": p["model"],
                    "messages": messages,
                    "max_tokens": 8192,
                    "temperature": 0.7,
                    "stream": False,
                })
                if tools:
                    body = json.dumps({
                        "model": p["model"],
                        "messages": messages,
                        "tools": tools,
                        "tool_choice": "auto",
                        "max_tokens": 8192,
                        "temperature": 0.7,
                        "stream": False,
                    })
                body = body.encode()
                
                req = urllib.request.Request(
                    f"{p['base_url'].rstrip('/')}/chat/completions",
                    data=body,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {p['api_key']}"
                    }
                )
                resp = json.loads(urllib.request.urlopen(req, timeout=p.get("timeout", 60)).read().decode())
                
                if "choices" in resp:
                    _current_failover_index = idx
                    return resp  # 成功
                elif "error" in resp:
                    err_msg = resp["error"].get("message", str(resp["error"]))
                    if attempt < max_retries and "rate" in err_msg.lower():
                        time.sleep(2 ** attempt)
                        continue
                    # 非重试类错误，尝试下一个 provider
                    break
                
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                break  # 非 429 错误，换 provider
            except (urllib.error.URLError, socket.timeout) as e:
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                break  # 连接失败，换 provider
            except Exception:
                break  # 其他错误，换 provider
    
    return {"error": f"所有 Provider 均失败 (尝试了 {len(enabled)} 个)"}

# ── CLI ────────────────────────────────────────

# ── Ollama 集成 ────────────────────────────────

def detect_ollama():
    """检测本机 ollama 服务是否运行，返回可用模型列表"""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        resp = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
        models = [m["name"] for m in resp.get("models", [])]
        return models
    except:
        return []

def add_ollama_provider():
    """自动检测并添加 ollama 到 provider 列表"""
    models = detect_ollama()
    if not models:
        return {"error": "ollama 未运行或无法连接 (localhost:11434)"}
    
    providers = load_providers()
    existing = [p for p in providers if p.get("provider") == "ollama"]
    
    added = 0
    for model in models:
        name = f"ollama-{model}"
        if not any(p["name"] == name for p in providers):
            providers.append({
                "name": name,
                "provider": "ollama",
                "base_url": "http://localhost:11434/v1",
                "model": model,
                "api_key": "ollama",
                "priority": 99,
                "enabled": True,
                "timeout": 120,
            })
            added += 1
    
    if added:
        save_providers(providers)
    
    return {"models": models, "added": added, "total": len(models)}


def main():
    import sys
    args = sys.argv[1:]
    
    if "--list" in args:
        providers = load_providers()
        print(f"\n📡 Provider 列表 ({len(providers)}):\n")
        for i, p in enumerate(providers):
            status = "🟢" if p.get("enabled", True) and p.get("api_key") else "🔴"
            print(f"  {status} [{i}] {p.get('name', '?')}")
            print(f"      model={p.get('model','?')} | priority={p.get('priority', '?')}")
            has_key = "✓" if p.get("api_key") else "✗"
            print(f"      api_key={has_key} | {p.get('base_url','?')}")
            print()
    
    elif "--switch" in args:
        providers = load_providers()
        print(f"\n选择默认 Provider:\n")
        for i, p in enumerate(providers):
            print(f"  [{i}] {p.get('name', '?')} ({p.get('model','?')})")
        try:
            idx = int(input("\n  编号: ").strip())
            if 0 <= idx < len(providers):
                # 把选中的移到第一位
                selected = providers.pop(idx)
                providers.insert(0, selected)
                save_providers(providers)
                print(f"  ✅ 已切换至: {selected['name']}")
        except:
            print("  ❌ 无效输入")
    
    elif "--test" in args:
        providers = load_providers()
        print(f"\n🔍 测试 {len(providers)} 个 Provider...\n")
        for p in providers:
            result = test_provider(p)
            icon = {"ok": "✅", "no_key": "⚠️", "fail": "❌", "error": "⚠️"}.get(result["status"], "❓")
            print(f"  {icon} {result['name']}: {result['status']} ({result['latency']}s)")
            if result.get("detail"):
                print(f"     {result['detail']}")
        print()
    
    elif "--add-ollama" in args:
        result = add_ollama_provider()
        if "error" in result:
            print(f"\n  ❌ {result['error']}")
            print("  💡 请先启动 ollama: ollama serve")
        else:
            print(f"\n  ✅ ollama 集成完成")
            print(f"     检测到模型: {', '.join(result['models'])}")
            print(f"     新增: {result['added']} / 共 {result['total']}")
            print(f"     ollama 已作为最低优先级后备 (priority=99)")
            print(f"     网络不通时自动切到本地模型")
        print()
    
    else:
        print("用法:")
        print("  python pipemind_provider.py --list        查看 Provider")
        print("  python pipemind_provider.py --switch      切换默认")
        print("  python pipemind_provider.py --test        测试连通性")
        print("  python pipemind_provider.py --add-ollama  集成本地 ollama")

if __name__ == "__main__":
    main()
