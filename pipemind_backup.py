"""PipeMind 备份自愈系统 — 文件完整性 + 本地快照备份

移植自弈辛 security_scan.py --auto-heal，适配 Windows 原生。

用法:
  python pipemind_backup.py --check   # 检查完整性
  python pipemind_backup.py --heal    # 自愈（恢复被篡改的文件）
  python pipemind_backup.py --backup  # 创建快照备份
  python pipemind_backup.py --status  # 查看备份状态
"""

from pipemind_core import PIPEMIND_DIR, MEM_DIR
import json, os, hashlib, datetime, glob, shutil, sys

BASELINE_FILE = os.path.join(PIPEMIND_DIR, "memory", ".baseline.json")
BACKUP_DIR = os.path.join(PIPEMIND_DIR, "memory", "_backups")

# 需要监控的文件模式
WATCH_PATTERNS = [
    "pipemind*.py",
    "pipemind*.json",
    "skills/**/SKILL.md",
    "SOUL.md",
    "config.json",
]

def _list_watched_files():
    """列出所有需要监控的文件"""
    files = []
    for pattern in WATCH_PATTERNS:
        for fp in sorted(glob.glob(os.path.join(PIPEMIND_DIR, pattern), recursive=True)):
            if os.path.isfile(fp) and "__pycache__" not in fp:
                rel = os.path.relpath(fp, PIPEMIND_DIR)
                files.append((rel, fp))
    return files

def _compute_baseline():
    """计算当前文件基线"""
    baseline = {}
    for rel, fp in _list_watched_files():
        try:
            with open(fp, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            baseline[rel] = {
                "hash": h,
                "size": os.path.getsize(fp),
                "mtime": os.path.getmtime(fp),
            }
        except Exception:
            pass
    return baseline

def _save_baseline(baseline):
    os.makedirs(os.path.dirname(BASELINE_FILE), exist_ok=True)
    with open(BASELINE_FILE, "w") as f:
        json.dump(baseline, f, indent=2)

def _load_baseline():
    if not os.path.exists(BASELINE_FILE):
        return {}
    try:
        with open(BASELINE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

# ── 检查 ────────────────────────────────────────

def check_integrity():
    """检查文件完整性，返回异常列表"""
    baseline = _load_baseline()
    if not baseline:
        return {"error": "无基线数据，请先运行 --backup"}
    
    results = {"modified": [], "new": [], "missing": [], "ok": [], "total": 0}
    current_files = {rel: fp for rel, fp in _list_watched_files()}
    
    for rel, info in baseline.items():
        if rel not in current_files:
            results["missing"].append(rel)
            continue
        
        fp = current_files[rel]
        try:
            with open(fp, "rb") as f:
                h = hashlib.sha256(f.read()).hexdigest()
            if h != info["hash"]:
                results["modified"].append(rel)
            else:
                results["ok"].append(rel)
        except Exception:
            results["missing"].append(rel)
    
    for rel in current_files:
        if rel not in baseline:
            results["new"].append(rel)
    
    results["total"] = len(results["ok"]) + len(results["modified"]) + len(results["new"])
    return results

# ── 自愈 ────────────────────────────────────────

def auto_heal():
    """自愈：从备份恢复被篡改的文件"""
    results = check_integrity()
    fixes = {"restored": [], "warnings": [], "errors": []}
    
    # 只修 modified 文件
    for rel in results.get("modified", []):
        backup_path = os.path.join(BACKUP_DIR, "latest", rel)
        original_path = os.path.join(PIPEMIND_DIR, rel)
        if os.path.exists(backup_path):
            try:
                os.makedirs(os.path.dirname(original_path), exist_ok=True)
                shutil.copy2(backup_path, original_path)
                fixes["restored"].append(rel)
            except Exception as e:
                fixes["errors"].append(f"{rel}: {e}")
        else:
            fixes["warnings"].append(f"{rel}: 无备份可恢复")
    
    # 新文件和缺失文件只报告
    for rel in results.get("new", []):
        fixes["warnings"].append(f"新文件: {rel}")
    for rel in results.get("missing", []):
        fixes["warnings"].append(f"缺失: {rel}")
    
    return fixes

# ── 备份 ────────────────────────────────────────

def create_backup():
    """创建快照备份"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_dir = os.path.join(BACKUP_DIR, f"snapshot_{timestamp}")
    latest_dir = os.path.join(BACKUP_DIR, "latest")
    
    for rel, fp in _list_watched_files():
        dst = os.path.join(snapshot_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(fp, dst)
        except Exception:
            pass
    
    # 更新 latest 软链（Windows 用复制）
    if os.path.exists(latest_dir):
        shutil.rmtree(latest_dir)
    shutil.copytree(snapshot_dir, latest_dir)
    
    # 保存基线
    baseline = _compute_baseline()
    _save_baseline(baseline)
    
    # 清理旧快照（保留最近 10 个）
    snapshots = sorted(glob.glob(os.path.join(BACKUP_DIR, "snapshot_*")))
    for old in snapshots[:-10]:
        shutil.rmtree(old, ignore_errors=True)
    
    count = len(baseline)
    print(f"✅ 备份完成: {count} 文件 -> {snapshot_dir}")
    return count

# ── 状态 ────────────────────────────────────────

def show_status():
    """显示备份状态"""
    baseline = _load_baseline()
    snapshots = sorted(glob.glob(os.path.join(BACKUP_DIR, "snapshot_*")))
    
    print(f"📊 PipeMind 备份状态")
    print(f"   基线文件: {len(baseline)} 个")
    print(f"   快照数: {len(snapshots)} 个")
    if snapshots:
        print(f"   最新: {os.path.basename(snapshots[-1])}")
    
    if baseline:
        results = check_integrity()
        if "error" in results:
            print(f"   ⚠ {results['error']}")
        else:
            status = "✅ 完好" if not results.get("modified") else f"⚠ {len(results['modified'])} 个被篡改"
            print(f"   完整性: {status}")
            if results.get("new"):
                print(f"   新文件: {len(results['new'])} 个")
            if results.get("missing"):
                print(f"   缺失: {len(results['missing'])} 个")

# ── 主入口 ──────────────────────────────────────

def main():
    args = set(sys.argv[1:])
    
    if "--backup" in args:
        create_backup()
    elif "--heal" in args:
        fixes = auto_heal()
        for f in fixes["restored"]:
            print(f"  ✓ 恢复: {f}")
        for w in fixes["warnings"]:
            print(f"  ⚠ {w}")
        for e in fixes["errors"]:
            print(f"  ✗ {e}")
        if not any([fixes["restored"], fixes["warnings"], fixes["errors"]]):
            print("✅ 所有文件完好")
    elif "--check" in args:
        results = check_integrity()
        if "error" in results:
            print(f"⚠ {results['error']}")
            return
        if results.get("modified"):
            print(f"⚠ 被篡改: {len(results['modified'])} 个")
            for f in results["modified"]:
                print(f"  · {f}")
        else:
            print(f"✅ 所有 {results['total']} 文件完好")
    elif "--status" in args or not args:
        show_status()
    else:
        print("用法: python pipemind_backup.py [--check|--heal|--backup|--status]")

if __name__ == "__main__":
    main()
