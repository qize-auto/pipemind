"""PipeMind 免疫系统 — 模块自我监控与自我修复

当某个模块出现异常时：
  1. 隔离 — 标记为 error 状态，防止级联故障
  2. 诊断 — 用 LLM 分析错误原因
  3. 修复 — 生成修复方案并尝试应用
  4. 恢复 — 重启模块，验证正常
  5. 学习 — 将错误模式加入经验库

集成:
  - core 的模块注册表 (检测异常)
  - 决策引擎 (触发修复周期)
  - 自我改进引擎 (生成修复代码)
  - 编年史 (记录事件)
"""

import os, json, datetime, sys, traceback, time, threading

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")
IMMUNE_LOG = os.path.join(MEM_DIR, "_immune_log.json")
QUARANTINE_LOG = os.path.join(MEM_DIR, "_quarantine.json")


class ImmuneSystem:
    """免疫系统 — 守护 PipeMind 自身健康"""

    def __init__(self):
        self._running = False
        self._thread = None
        self._check_interval = 300  # 5 分钟
        self._quarantine = {}  # module → {failures, since, last_error}
        self._max_retries = 3

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    # ── 核心循环 ──

    def _loop(self):
        while self._running:
            try:
                self._health_check()
            except Exception:
                pass
            time.sleep(self._check_interval)

    def _health_check(self):
        """检查所有已注册模块的健康状况"""
        try:
            from pipemind_core import list_modules, module_stats
            modules = list_modules()
            stats = module_stats()
        except Exception:
            return

        for m in modules:
            name = m.get("name", "")
            status = m.get("status", "")
            errors = m.get("errors", 0)

            if status == "error" or errors > 0:
                self._handle_sick_module(name, m)

        # 记录整体健康状态
        if stats.get("errored", 0) > 0:
            self._log_event("health_alert",
                f"{stats['errored']}/{stats['total']} 模块异常",
                {"stats": stats})

    # ── 诊断与修复 ──

    def _handle_sick_module(self, name: str, info: dict):
        """处理异常模块"""
        # 检查是否在隔离区
        quarantine = self._load_quarantine()
        if name in quarantine:
            q = quarantine[name]
            q["failures"] += 1
            q["last_seen"] = datetime.datetime.now().isoformat()
            if q["failures"] >= self._max_retries:
                self._log_event("quarantine_escalated",
                    f"{name} 已被隔离 (失败 {q['failures']} 次)",
                    {"module": name, "failures": q["failures"]})
                self._save_quarantine(quarantine)
                return
        else:
            quarantine[name] = {
                "failures": 1,
                "since": datetime.datetime.now().isoformat(),
                "last_seen": datetime.datetime.now().isoformat(),
                "last_error": str(info.get("errors", "unknown")),
            }
            self._save_quarantine(quarantine)

        # 诊断
        diagnosis = self._diagnose(name, info)
        self._log_event("diagnosis", f"{name}: {diagnosis.get('summary','?')}", diagnosis)

        # 尝试修复
        if diagnosis.get("actionable"):
            result = self._heal(name, diagnosis)
            self._log_event("healing",
                f"{name}: {'✅ 已修复' if result else '❌ 修复失败'}", {"result": result})

    def _diagnose(self, name: str, info: dict) -> dict:
        """诊断模块异常"""
        errors = info.get("errors", 0)
        status = info.get("status", "unknown")

        prompt = f"""你是一个系统诊断 AI。分析模块异常，给出修复建议。

模块: {name}
状态: {status}
错误次数: {errors}

可能的原因:
1. 模块依赖缺失
2. 配置文件损坏
3. 运行时异常
4. 资源耗尽

返回 JSON (中文):
{{"summary":"一句话诊断","cause":"可能原因","actionable":true/false,"fix":"修复建议"}}
"""
        try:
            result = self._call_llm(prompt)
            parsed = json.loads(result) if isinstance(result, str) else result
            return parsed if isinstance(parsed, dict) else {"summary": "诊断失败", "actionable": False}
        except Exception:
            return {"summary": "诊断失败", "actionable": False}

    def _heal(self, name: str, diagnosis: dict) -> bool:
        """尝试修复模块"""
        try:
            from pipemind_core import start_module
            # 简单重启
            ok = start_module(name)
            if ok:
                self._log_event("healed", f"{name} 重启成功")
                # 从隔离区移除
                q = self._load_quarantine()
                if name in q:
                    del q[name]
                    self._save_quarantine(q)
                return True
            return False
        except Exception:
            return False

    # ── LLM 接口 ──

    def _call_llm(self, prompt: str) -> str:
        sys.path.insert(0, PIPEMIND_DIR)
        try:
            import pipemind_provider as provider
            result = provider.call_with_failover([
                {"role": "system", "content": "你是 PipeMind 免疫系统。诊断并修复模块异常。"},
                {"role": "user", "content": prompt}
            ], tools=[])
            if "error" not in result:
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            pass
        return "{}"

    # ── 日志与隔离区 ──

    def _log_event(self, kind: str, message: str, data: dict = None):
        event = {
            "time": datetime.datetime.now().isoformat(),
            "kind": kind,
            "message": message,
        }
        if data:
            event["data"] = data
        os.makedirs(MEM_DIR, exist_ok=True)
        logs = []
        if os.path.exists(IMMUNE_LOG):
            try:
                with open(IMMUNE_LOG, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                pass
        logs.append(event)
        if len(logs) > 200:
            logs = logs[-200:]
        with open(IMMUNE_LOG, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    def _load_quarantine(self) -> dict:
        if not os.path.exists(QUARANTINE_LOG):
            return {}
        try:
            with open(QUARANTINE_LOG, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_quarantine(self, data: dict):
        with open(QUARANTINE_LOG, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ── 全局实例 ──

_immune = ImmuneSystem()


def get_immune():
    return _immune


def get_logs(limit=30) -> list:
    if not os.path.exists(IMMUNE_LOG):
        return []
    try:
        with open(IMMUNE_LOG, "r", encoding="utf-8") as f:
            logs = json.load(f)
        return logs[-limit:]
    except Exception:
        return []


def get_quarantine() -> dict:
    return _immune._load_quarantine()


def get_health_summary() -> dict:
    """获取系统健康摘要"""
    q = get_quarantine()
    return {
        "quarantined": list(q.keys()),
        "healthy_modules": None,  # filled by caller
        "last_check": None,
    }


# ── CLI ──

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PipeMind 免疫系统")
    parser.add_argument("--status", action="store_true", help="免疫状态")
    parser.add_argument("--quarantine", action="store_true", help="隔离区")
    parser.add_argument("--logs", action="store_true", help="查看日志")
    args = parser.parse_args()

    if args.status:
        q = get_quarantine()
        print(f"\n🛡️ PipeMind 免疫系统")
        print(f"   隔离模块: {len(q)} 个")
        for name, info in q.items():
            print(f"   · {name}: 失败 {info.get('failures',0)} 次")
        logs = get_logs(limit=5)
        print(f"\n   最近事件: {len(logs)} 条")

    if args.quarantine:
        q = get_quarantine()
        print(json.dumps(q, ensure_ascii=False, indent=2))

    if args.logs:
        logs = get_logs(limit=20)
        for l in logs:
            print(f"  [{l.get('time','?')[:19]}] {l.get('kind','?')}: {l.get('message','')[:60]}")
