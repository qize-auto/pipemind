"""PipeMind — 安全韧性层：加密存储 + 审计日志 + 崩溃恢复 + 热重载"""
import os, json, datetime, base64, hashlib, hmac, sys, glob, shutil, traceback

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIT_LOG = os.path.join(PIPEMIND_DIR, "memory", "_audit.json")
CRASH_LOG = os.path.join(PIPEMIND_DIR, "memory", "_crashes.json")
BACKUP_DIR = os.path.join(PIPEMIND_DIR, "memory", "_backups")
SECRET_FILE = os.path.join(PIPEMIND_DIR, "memory", ".secrets")


# ── API Key 加密存储 ──

def _get_machine_key() -> bytes:
    """获取机器唯一密钥（基于硬件信息）"""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
        return hashlib.sha256(machine_guid.encode()).digest()
    except Exception:
        return hashlib.sha256(b"PIPEMIND_DEFAULT_KEY").digest()


def encrypt(text: str) -> str:
    """加密文本"""
    from cryptography.fernet import Fernet
    key = base64.urlsafe_b64encode(_get_machine_key()[:32])
    return Fernet(key).encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    """解密文本"""
    from cryptography.fernet import Fernet
    key = base64.urlsafe_b64encode(_get_machine_key()[:32])
    return Fernet(key).decrypt(token.encode()).decode()


def save_secret(name: str, value: str) -> str:
    """加密保存敏感信息"""
    try:
        from cryptography.fernet import Fernet
        secrets = {}
        if os.path.exists(SECRET_FILE):
            try:
                with open(SECRET_FILE, "r") as f:
                    secrets = json.load(f)
            except Exception: pass
        secrets[name] = encrypt(value)
        with open(SECRET_FILE, "w") as f:
            json.dump(secrets, f)
        return f"✅ 已加密保存 {name}"
    except ImportError:
        return "⚠ 需要安装 cryptography: pip install cryptography"
    except Exception as e:
        return f"❌ {e}"


def load_secret(name: str) -> str:
    """读取加密的敏感信息"""
    if not os.path.exists(SECRET_FILE):
        return ""
    try:
        from cryptography.fernet import Fernet
        with open(SECRET_FILE, "r") as f:
            secrets = json.load(f)
        if name in secrets:
            return decrypt(secrets[name])
        return ""
    except Exception:
        return ""


def secure_config() -> str:
    """将 config.json 中的 API Key 加密存储"""
    try:
        import pipemind_config as cfg
        c = cfg.load()
        key = c.get("model", {}).get("api_key", "")
        if key and not key.startswith("ENC:"):
            save_secret("api_key", key)
            c["model"]["api_key"] = "ENC:stored"
            cfg.save(c)
            return "✅ API Key 已加密存储"
        return "✅ API Key 已保护"
    except Exception as e:
        return f"❌ {e}"


# ── 审计日志 ──

def audit(action: str, detail: str = "", status: str = "ok"):
    """记录操作审计日志"""
    logs = []
    if os.path.exists(AUDIT_LOG):
        try:
            with open(AUDIT_LOG, "r") as f:
                logs = json.load(f)
        except Exception: pass
    
    logs.append({
        "time": datetime.datetime.now().isoformat(),
        "action": action,
        "detail": detail[:200],
        "status": status
    })
    
    logs = logs[-500:]  # 保留最近 500 条
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    with open(AUDIT_LOG, "w") as f:
        json.dump(logs, f, indent=2)


def audit_report(hours: int = 24) -> str:
    """审计报告"""
    if not os.path.exists(AUDIT_LOG):
        return "📋 暂无审计记录"
    
    try:
        with open(AUDIT_LOG, "r") as f:
            logs = json.load(f)
    except Exception:
        return "📋 数据损坏"
    
    cutoff = (datetime.datetime.now() - datetime.timedelta(hours=hours)).isoformat()
    recent = [l for l in logs if l["time"] > cutoff]
    
    if not recent:
        return f"📋 最近 {hours} 小时无操作记录"
    
    # 统计
    by_action = {}
    for l in recent:
        a = l["action"]
        by_action[a] = by_action.get(a, 0) + 1
    
    lines = [f"📋 最近 {hours} 小时审计 ({len(recent)} 条操作):"]
    for action, count in sorted(by_action.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"  {action}: {count} 次")
    lines.append("")
    for l in recent[-5:]:
        lines.append(f"  [{l['time'][:19]}] {l['action']} — {l['detail'][:50]}")
    
    return "\n".join(lines)


# ── 崩溃恢复 ──

def log_crash(error: str, context: str = ""):
    """记录崩溃信息"""
    crashes = []
    if os.path.exists(CRASH_LOG):
        try:
            with open(CRASH_LOG, "r") as f:
                crashes = json.load(f)
        except Exception: pass
    
    crashes.append({
        "time": datetime.datetime.now().isoformat(),
        "error": str(error)[:300],
        "context": context[:200],
        "traceback": traceback.format_exc()[:500]
    })
    
    crashes = crashes[-20:]  # 保留最近 20 条
    os.makedirs(os.path.dirname(CRASH_LOG), exist_ok=True)
    with open(CRASH_LOG, "w") as f:
        json.dump(crashes, f, indent=2)
    
    # 自动备份关键文件
    auto_backup()


def get_last_crash() -> str:
    """查看最近崩溃"""
    if not os.path.exists(CRASH_LOG):
        return "✅ 无崩溃记录"
    try:
        with open(CRASH_LOG, "r") as f:
            crashes = json.load(f)
        if not crashes:
            return "✅ 无崩溃记录"
        last = crashes[-1]
        return f"🩺 最近崩溃: {last['time'][:19]}\n   {last['error'][:100]}"
    except Exception:
        return "📋 数据损坏"


# ── 自动备份 ──

def auto_backup() -> str:
    """备份关键文件"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    files_to_backup = [
        "SOUL.md", "config.json", "pipemind.py",
        "pipemind_tools.py", "pipemind_evolution.py",
        "pipemind_diary.py", "pipemind_precision.py",
        "pipemind_metabolism.py"
    ]
    
    backed_up = []
    for f in files_to_backup:
        src = os.path.join(PIPEMIND_DIR, f)
        if os.path.exists(src):
            dst = os.path.join(BACKUP_DIR, f"{ts}_{f}")
            shutil.copy2(src, dst)
            backed_up.append(f)
    
    # 清理旧备份（保留最近 10 个）
    all_backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "*")))
    while len(all_backups) > 10 * len(files_to_backup):
        os.remove(all_backups[0])
        all_backups = all_backups[1:]
    
    return f"✅ 已备份 {len(backed_up)} 个文件"


def list_backups() -> str:
    """列出备份"""
    backups = sorted(glob.glob(os.path.join(BACKUP_DIR, "*")))
    if not backups:
        return "(无备份)"
    lines = ["📦 备份列表:"]
    for b in backups[-10:]:
        name = os.path.basename(b)
        size = os.path.getsize(b)
        lines.append(f"  {name} ({size}B)")
    return "\n".join(lines)


# ── 热重载 ──

def hot_reload() -> str:
    """热重载所有模块"""
    results = []
    modules = [
        "pipemind_config", "pipemind_tools", "pipemind_skills",
        "pipemind_evolution", "pipemind_diary", "pipemind_vision",
        "pipemind_voice", "pipemind_monitor", "pipemind_memory_plus",
        "pipemind_self_test", "pipemind_metabolism", "pipemind_precision",
        "pipemind_windows_deep"
    ]
    
    for mod_name in modules:
        if mod_name in sys.modules:
            try:
                import importlib
                importlib.reload(sys.modules[mod_name])
                results.append(f"✅ {mod_name}")
            except Exception as e:
                results.append(f"❌ {mod_name}: {e}")
    
    return "\n".join(results) if results else "没有模块需要重载"


def safe_execute(func, *args, **kwargs):
    """安全执行函数，崩溃时自动记录"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        log_crash(str(e), f"{func.__name__}")
        return None
