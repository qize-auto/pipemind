"""PipeMind 子代理系统 — 任务分解 + 并行执行

用法:
  python pipemind_delegate.py --task "描述任务"     # 执行单个任务
  python pipemind_delegate.py --list               # 查看任务状态
"""

import json, os, subprocess, sys, datetime, threading, time, hashlib

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(PIPEMIND_DIR, "memory", "_tasks.json")
MAX_WORKERS = 3

# ── 任务存储 ──────────────────────────────────

def _load_tasks():
    if not os.path.exists(TASKS_FILE):
        return {"tasks": [], "next_id": 1}
    try:
        with open(TASKS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"tasks": [], "next_id": 1}

def _save_tasks(data):
    os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_task(goal, parent_id=None):
    """添加子任务"""
    data = _load_tasks()
    task = {
        "id": data["next_id"],
        "goal": goal,
        "parent_id": parent_id,
        "status": "pending",
        "result": None,
        "created": datetime.datetime.now().isoformat(),
        "completed": None,
    }
    data["tasks"].append(task)
    data["next_id"] += 1
    _save_tasks(data)
    return task["id"]

def update_task(task_id, status, result=None):
    data = _load_tasks()
    for t in data["tasks"]:
        if t["id"] == task_id:
            t["status"] = status
            if result:
                t["result"] = result[:500]
            if status in ("completed", "failed"):
                t["completed"] = datetime.datetime.now().isoformat()
            break
    _save_tasks(data)

def list_tasks(limit=10):
    data = _load_tasks()
    return sorted(data["tasks"], key=lambda x: x["created"], reverse=True)[:limit]

# ── 子代理执行 ────────────────────────────────

def spawn_worker(goal):
    """启动一个子代理进程执行任务"""
    task_id = add_task(goal)
    
    # 构造子代理的 system prompt
    prompt = f"""你是 PipeMind 的子代理。你的任务是独立完成以下目标，不需要请示。

目标: {goal}

限制:
1. 只能使用已有的工具
2. 最多执行 10 轮工具调用
3. 完成后输出最终结果
"""
    
    def _run():
        try:
            # 通过调用主 PipeMind 的 API 来执行子任务
            body = json.dumps({
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": goal}
                ],
                "max_tokens": 2000,
                "temperature": 0.3,
            }).encode()
            
            req = urllib.request.Request(
                "https://api.deepseek.com/v1/chat/completions",
                data=body,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {_load_api_key()}"}
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
            result = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
            update_task(task_id, "completed", result)
        except Exception as e:
            update_task(task_id, "failed", str(e))
    
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return task_id

def _load_api_key():
    """从 config 读取 API key"""
    cfg_path = os.path.join(PIPEMIND_DIR, "config.json")
    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("model", {}).get("api_key", "")
    except:
        return ""

# ── 任务分解 ──────────────────────────────────

def decompose_and_delegate(complex_task):
    """将复杂任务分解为子任务并行执行"""
    # 先用 LLM 分解任务
    prompt = f"""将以下复杂任务分解为 {MAX_WORKERS} 个可以并行执行的子任务。
每个子任务应该可以独立完成。返回 JSON 数组。

任务: {complex_task}

格式: ["子任务1描述", "子任务2描述", ...]"""
    
    try:
        body = json.dumps({
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.3,
        }).encode()
        req = urllib.request.Request(
            "https://api.deepseek.com/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {_load_api_key()}"}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
        content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # 提取 JSON
        import re
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            subtasks = json.loads(match.group())
            task_ids = []
            for sub in subtasks[:MAX_WORKERS]:
                tid = spawn_worker(sub)
                task_ids.append(tid)
            return {"parent_task": complex_task, "subtask_ids": task_ids, "count": len(task_ids)}
    except Exception as e:
        return {"error": str(e)}
    
    return {"error": "分解失败"}

# ── CLI ────────────────────────────────────────

def main():
    import urllib.request  # noqa: needed for spawn_worker
    
    if "--task" in sys.argv:
        idx = sys.argv.index("--task") + 1
        if idx < len(sys.argv):
            goal = " ".join(sys.argv[idx:])
            tid = spawn_worker(goal)
            print(f"📋 任务 #{tid} 已提交: {goal}")
            print(f"   查看状态: python pipemind_delegate.py --list")
    
    elif "--list" in sys.argv:
        tasks = list_tasks()
        if not tasks:
            print("📋 无任务记录")
            return
        print(f"\n📋 最近 {len(tasks)} 个任务:\n")
        for t in tasks:
            icon = {"pending": "⏳", "completed": "✅", "failed": "❌"}.get(t["status"], "❓")
            print(f"  {icon} #{t['id']} {t['goal'][:60]}")
            print(f"     状态: {t['status']} | {t['created'][:16]}")
            if t.get("result"):
                print(f"     结果: {t['result'][:80]}")
            print()
    
    elif "--decompose" in sys.argv:
        idx = sys.argv.index("--decompose") + 1
        if idx < len(sys.argv):
            task = " ".join(sys.argv[idx:])
            result = decompose_and_delegate(task)
            print(f"📋 任务分解: {task}")
            if "subtask_ids" in result:
                print(f"   分解为 {result['count']} 个子任务:")
                for tid in result["subtask_ids"]:
                    print(f"   #{tid}")
            else:
                print(f"   ❌ {result.get('error', '未知错误')}")
    
    else:
        print("用法:")
        print("  python pipemind_delegate.py --task <描述>    提交任务")
        print("  python pipemind_delegate.py --list          查看任务")
        print("  python pipemind_delegate.py --decompose <任务>  分解+并行")

if __name__ == "__main__":
    main()
