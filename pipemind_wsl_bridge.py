"""PipeMind WSL桥梁 — 弈辛守护者

功能:
  1. 健康监控 — 每5分钟检查弈辛进程 + API 连通性
  2. 自动修复 — API 连续挂 2 次 → 自动切换备用模型 + 重启
  3. 配置管理 — 读写弈辛 ~/.hermes/config.yaml
  4. 进程控制 — 启动/停止/重启弈辛
  5. 状态面板 — Web 控制台实时查看

数据 (memory/):
  _yixin_events.json  — 诊断与修复事件日志
"""

import os, sys, json, datetime, time, threading, subprocess, re

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
MEM_DIR = os.path.join(PIPEMIND_DIR, "memory")
EVENTS_FILE = os.path.join(MEM_DIR, "_yixin_events.json")

WSL_DISTRO = "Ubuntu"
WSL_YIXIN_CONFIG = "~/.hermes/config.yaml"

# ── 备用模型预设 ──────────────────────────
# 从环境变量读 API Key，没配就提示
BACKUP_PRESETS = [
    {
        "name": "DeepSeek v4 (当前)",
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    {
        "name": "DeepSeek v3 (备用)",
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-v3.2",
        "env_key": "DEEPSEEK_API_KEY",
    },
    {
        "name": "DeepSeek Reasoner",
        "provider": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-reasoner",
        "env_key": "DEEPSEEK_API_KEY",
    },
]


# ═══════════════════════════════════════════════
# 1. 弈辛配置管理
# ═══════════════════════════════════════════════

class YixinConfig:
    """读写弈辛 ~/.hermes/config.yaml"""

    @staticmethod
    def _wsl(cmd):
        """在 WSL 中执行命令"""
        try:
            r = subprocess.run(
                ["wsl", "-d", WSL_DISTRO, "-e", "bash", "-l", "-c", cmd],
                capture_output=True, text=True, timeout=15
            )
            return r.stdout.strip(), r.returncode
        except subprocess.TimeoutExpired:
            return "", -1
        except FileNotFoundError:
            return "", -2

    @staticmethod
    def read() -> dict:
        """读取当前模型配置"""
        out, code = YixinConfig._wsl("cat ~/.hermes/config.yaml")
        if code != 0 or not out:
            return {}

        cfg = {}
        for line in out.split("\n"):
            m = re.match(r'^\s{2}(\w+):\s*(.+)', line)
            if m:
                cfg[m.group(1)] = m.group(2).strip().strip("'\"")
        return cfg

    @staticmethod
    def write(api_key: str, base_url: str, model_name: str, provider: str) -> bool:
        """写入新配置（同步更新 auxiliary.compression）"""
        cmds = [
            f"sed -i 's|^  api_key:.*|  api_key: {api_key}|' {WSL_YIXIN_CONFIG}",
            f"sed -i 's|^  base_url:.*|  base_url: {base_url}|' {WSL_YIXIN_CONFIG}",
            f"sed -i 's|^  model_name:.*|  model_name: {model_name}|' {WSL_YIXIN_CONFIG}",
            f"sed -i 's|^  default:.*|  default: {model_name}|' {WSL_YIXIN_CONFIG}",
            f"sed -i 's|^  provider:.*|  provider: {provider}|' {WSL_YIXIN_CONFIG}",
            # auxiliary.compression
            f"sed -i '/^  compression:/,/^  [a-z]/ s|    api_key:.*|    api_key: {api_key}|' {WSL_YIXIN_CONFIG}",
            f"sed -i '/^  compression:/,/^  [a-z]/ s|    base_url:.*|    base_url: {base_url}|' {WSL_YIXIN_CONFIG}",
            f"sed -i '/^  compression:/,/^  [a-z]/ s|    model: .*|    model: {model_name}|' {WSL_YIXIN_CONFIG}",
        ]
        ok = True
        for cmd in cmds:
            _, code = YixinConfig._wsl(cmd)
            if code != 0:
                ok = False
        return ok

    @staticmethod
    def switch_preset(index: int, api_key_override: str = "") -> dict:
        """切换到预设方案"""
        if index < 0 or index >= len(BACKUP_PRESETS):
            return {"ok": False, "error": "无效预设索引"}

        p = BACKUP_PRESETS[index]
        api_key = api_key_override or os.environ.get(p["env_key"], "")

        if not api_key:
            return {"ok": False, "error": f"需要 {p['env_key']} 环境变量"}

        ok = YixinConfig.write(api_key, p["base_url"], p["model"], p["provider"])
        if ok:
            return {"ok": True, "model": p["model"], "provider": p["provider"], "name": p["name"]}
        return {"ok": False, "error": "写入配置失败"}


# ═══════════════════════════════════════════════
# 2. 弈辛进程控制
# ═══════════════════════════════════════════════

class YixinControl:
    """启动/停止/重启弈辛"""

    @staticmethod
    def _wsl(cmd):
        try:
            r = subprocess.run(
                ["wsl", "-d", WSL_DISTRO, "-e", "bash", "-l", "-c", cmd],
                capture_output=True, text=True, timeout=15
            )
            return r.stdout.strip(), r.returncode
        except:
            return "", -1

    @staticmethod
    def is_running() -> bool:
        out, code = YixinControl._wsl("pgrep -f 'hermes' | head -1")
        return code == 0 and out.strip() != ""

    @staticmethod
    def get_pid() -> str:
        out, _ = YixinControl._wsl("pgrep -f 'hermes' | head -1")
        return out.strip()

    @staticmethod
    def restart() -> bool:
        """重启弈辛"""
        YixinControl._wsl("pkill -f 'hermes' 2>/dev/null; sleep 2")
        time.sleep(1)
        YixinControl._wsl("nohup hermes > /dev/null 2>&1 &")
        # 等 5 秒确认启动
        for i in range(10):
            time.sleep(0.5)
            if YixinControl.is_running():
                return True
        return False

    @staticmethod
    def stop() -> bool:
        YixinControl._wsl("pkill -f 'hermes' 2>/dev/null")
        time.sleep(1)
        return not YixinControl.is_running()


# ═══════════════════════════════════════════════
# 3. 健康监控（后台线程）
# ═══════════════════════════════════════════════

class YixinMonitor:
    """弈辛健康监控 — 每5分钟检查"""

    def __init__(self):
        self._running = False
        self._thread = None
        self._auto_fix = True
        self._status = {
            "running": False,
            "pid": "",
            "model": "",
            "provider": "",
            "connected": False,
            "last_check": None,
            "last_ok": None,
            "fail_count": 0,
            "auto_fixes": 0,
        }

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    @property
    def status(self):
        return dict(self._status)

    def _loop(self):
        while self._running:
            try:
                self._check()
            except:
                pass
            time.sleep(300)  # 5 分钟

    def _check(self):
        now = datetime.datetime.now().isoformat()
        self._status["last_check"] = now

        # 1. 进程检查
        running = YixinControl.is_running()
        self._status["running"] = running
        self._status["pid"] = YixinControl.get_pid() if running else ""

        # 2. 读配置
        cfg = YixinConfig.read()
        self._status["model"] = cfg.get("model_name", "?")
        self._status["provider"] = cfg.get("provider", "?")

        # 3. API 连通测试
        api_ok = self._test_api(cfg)
        self._status["connected"] = api_ok

        if api_ok:
            self._status["last_ok"] = now
            self._status["fail_count"] = 0
            self._log_event("ok", f"弈辛正常 | {cfg.get('model_name','?')}")
        else:
            self._status["fail_count"] += 1
            self._log_event("fail", f"API 不可达 | {self._status.get('model','?')}")

            # 自动修复：连续失败 2 次
            if self._auto_fix and self._status["fail_count"] >= 2:
                self._auto_fix_action()

    def _test_api(self, cfg) -> bool:
        """轻量 API 测试"""
        if not cfg:
            return False
        api_key = cfg.get("api_key", "")
        base_url = cfg.get("base_url", "https://api.deepseek.com/v1").rstrip("/")
        model = cfg.get("model_name", "deepseek-chat")
        if not api_key:
            return False
        try:
            import urllib.request
            body = json.dumps({
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 5,
            }).encode()
            req = urllib.request.Request(
                f"{base_url}/chat/completions",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
            )
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode())
            return "choices" in data
        except:
            return False

    def _auto_fix_action(self):
        """自动修复：依次尝试备用模型"""
        self._log_event("auto_fix_start", "开始自动修复...")

        for idx in range(len(BACKUP_PRESETS)):
            p = BACKUP_PRESETS[idx]
            api_key = os.environ.get(p["env_key"], "")
            if not api_key:
                continue

            result = YixinConfig.switch_preset(idx, api_key)
            if not result.get("ok"):
                continue

            time.sleep(2)
            ok = YixinControl.restart()
            if ok:
                self._status["auto_fixes"] += 1
                self._status["fail_count"] = 0
                self._log_event("auto_fixed",
                    f"已切换至 {p['name']} ({p['model']})，弈辛已重启")
                return

        self._log_event("auto_fix_fail", "所有备用方案均失败")

    def trigger_check(self):
        """手动触发一次检查"""
        self._check()

    def trigger_auto_fix(self):
        """手动触发自动修复"""
        self._auto_fix_action()

    def _log_event(self, kind, message):
        """记录事件到文件"""
        os.makedirs(MEM_DIR, exist_ok=True)
        event = {
            "time": datetime.datetime.now().isoformat(),
            "kind": kind,
            "message": message,
            "model": self._status.get("model", "?"),
            "running": self._status.get("running", False),
        }
        events = []
        if os.path.exists(EVENTS_FILE):
            try:
                with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                    events = json.load(f)
            except:
                pass
        events.append(event)
        if len(events) > 200:
            events = events[-200:]
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)


# ── 全局监控实例 ──
_monitor = YixinMonitor()


def get_monitor():
    return _monitor


def get_events(limit=30):
    """获取最近事件"""
    if not os.path.exists(EVENTS_FILE):
        return []
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            events = json.load(f)
        return events[-limit:]
    except:
        return []


def get_presets():
    """获取预设列表（脱敏，不返回 API Key）"""
    return [
        {"index": i, "name": p["name"], "provider": p["provider"],
         "model": p["model"], "has_key": bool(os.environ.get(p["env_key"]))}
        for i, p in enumerate(BACKUP_PRESETS)
    ]
