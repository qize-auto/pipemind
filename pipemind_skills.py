"""PipeMind 技能热加载 — 不重启就能加载新技能"""

import os, glob, re, json, threading, time, hashlib

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(PIPEMIND_DIR, "skills")

_loaded_skills = []
_watcher_thread = None
_watcher_running = False
_last_fingerprints = {}

# ── 技能解析 ──────────────────────────────────

def _fingerprint(name, content):
    return hashlib.md5(f"{name}:{content}".encode()).hexdigest()[:12]

def _parse_skill(path):
    """解析一个 SKILL.md 文件"""
    name = os.path.basename(os.path.dirname(path))
    try:
        content = open(path, encoding="utf-8").read()
    except:
        return None
    
    fp = _fingerprint(name, content)
    
    # frontmatter
    frontmatter = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    frontmatter[k.strip()] = v.strip().strip("\"'")
    
    desc = frontmatter.get("description", name)
    tags = frontmatter.get("tags", "")
    
    # 提取提示注入
    prompt_inject = ""
    in_inject = False
    for line in content.split("\n"):
        if line.strip().lower().startswith("## system prompt"):
            in_inject = True
            continue
        if in_inject:
            if line.startswith("## "):
                break
            prompt_inject += line + "\n"
    
    # 提取斜杠命令
    commands = []
    for line in content.split("\n"):
        m = re.match(r'^## slash command:?\s*(/\S+)', line, re.IGNORECASE)
        if m:
            commands.append(m.group(1))
    
    return {
        "name": name,
        "desc": desc,
        "tags": tags,
        "path": path,
        "commands": commands,
        "fingerprint": fp,
        "prompt_inject": prompt_inject.strip(),
    }

# ── 发现 & 热加载 ────────────────────────────

def discover() -> list[dict]:
    """扫描 skills/ 目录，返回所有技能信息"""
    skills = []
    for md in sorted(glob.glob(os.path.join(SKILLS_DIR, "**", "SKILL.md"), recursive=True)):
        info = _parse_skill(md)
        if info:
            skills.append(info)
    return skills

def get_prompt_injections() -> str:
    """获取所有技能的提示词注入"""
    global _loaded_skills
    _loaded_skills = discover()
    injections = []
    for s in _loaded_skills:
        if s["prompt_inject"]:
            injections.append(f"### {s['name']}\n{s['prompt_inject']}")
    return "\n\n".join(injections[:5]) if injections else ""

def reload() -> int:
    """热加载：重新扫描技能目录，返回加载数"""
    global _loaded_skills
    _loaded_skills = discover()
    return len(_loaded_skills)

def list_skills() -> list[dict]:
    """返回当前加载的技能列表"""
    global _loaded_skills
    if not _loaded_skills:
        _loaded_skills = discover()
    return _loaded_skills

# ── 文件监控（自动热加载） ──────────────────

def _check_changes():
    """检查技能文件是否有变化"""
    global _last_fingerprints
    
    current = {}
    for md in glob.glob(os.path.join(SKILLS_DIR, "**", "SKILL.md"), recursive=True):
        name = os.path.basename(os.path.dirname(md))
        try:
            content = open(md, encoding="utf-8").read()
            current[name] = _fingerprint(name, content)
        except:
            continue
    
    if _last_fingerprints and current != _last_fingerprints:
        added = set(current.keys()) - set(_last_fingerprints.keys())
        removed = set(_last_fingerprints.keys()) - set(current.keys())
        changed = {k for k in current if k in _last_fingerprints and current[k] != _last_fingerprints[k]}
        
        if added or removed or changed:
            count = reload()
            if added:
                for s in added:
                    print(f"  📥 新技能: {s}")
            if removed:
                for s in removed:
                    print(f"  🗑️ 技能移除: {s}")
            if changed:
                for s in changed:
                    print(f"  🔄 技能更新: {s}")
            return count
    
    _last_fingerprints = current
    return None

def start_watcher(interval=5):
    """启动文件监控线程（每 interval 秒检查一次）"""
    global _watcher_thread, _watcher_running
    
    if _watcher_running:
        return
    
    _watcher_running = True
    
    def _watch():
        global _last_fingerprints
        # 初始化指纹
        _last_fingerprints = {}
        for md in glob.glob(os.path.join(SKILLS_DIR, "**", "SKILL.md"), recursive=True):
            name = os.path.basename(os.path.dirname(md))
            try:
                content = open(md, encoding="utf-8").read()
                _last_fingerprints[name] = _fingerprint(name, content)
            except:
                continue
        
        while _watcher_running:
            _check_changes()
            time.sleep(interval)
    
    _watcher_thread = threading.Thread(target=_watch, daemon=True)
    _watcher_thread.start()

def stop_watcher():
    """停止文件监控"""
    global _watcher_running
    _watcher_running = False
