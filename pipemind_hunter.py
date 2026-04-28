"""PipeMind 技能猎人 — 从 GitHub / ClawHub 搜索、分析、吸收技能

当本地技能注册表无匹配时，自动去外部平台猎取高分技能。

用法:
  python pipemind_hunter.py --search "写小说"     # 搜索外部技能
  python pipemind_hunter.py --absorb <url>        # 吸收指定技能
  python pipemind_hunter.py --hunt "写小说"       # 完整狩猎:搜索+分析+吸收
  python pipemind_hunter.py --upgrade             # 检查已吸收技能的更新
"""

import json, os, re, datetime, subprocess, sys, glob, hashlib, tempfile, shutil

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(PIPEMIND_DIR, "skills")
REGISTRY_FILE = os.path.join(PIPEMIND_DIR, "memory", "_skill_registry.json")
HUNTER_CACHE = os.path.join(PIPEMIND_DIR, "memory", "_hunter_cache.json")
ABSORBED_LOG = os.path.join(PIPEMIND_DIR, "memory", "_absorbed_skills.json")

# ── 外部技能源 ──────────────────────────────

SKILL_SOURCES = [
    {
        "name": "awesome-openclaw-skills",
        "repo": "https://github.com/VoltAgent/awesome-openclaw-skills",
        "type": "openclaw",
        "stars": 47487,
    },
    {
        "name": "awesome-openclaw-skills-zh",
        "repo": "https://github.com/VoltAgent/awesome-openclaw-skills-zh",
        "type": "openclaw",
        "stars": 3984,
    },
    {
        "name": "openclaw-master-skills",
        "repo": "https://github.com/LeoYeAI/openclaw-master-skills",
        "type": "openclaw",
        "stars": 1953,
    },
]

# ── 工具 ──────────────────────────────────────

def _load_json(path, default=None):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return default or {}

def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _log(msg):
    print(f"  🎯 {msg}")

# ── GitHub 搜索 ──────────────────────────────

def search_github(query, limit=10):
    """用 gh CLI 搜索 GitHub 上的技能仓库"""
    try:
        result = subprocess.run(
            ["gh", "search", "repos", query, "--limit", str(limit),
             "--json", "name,description,stargazersCount,url,owner"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        return []
    except:
        return []

def search_openclaw_skills(query, limit=5):
    """在已知的 OpenClaw 技能源中搜索（按匹配度+质量排序）"""
    cache = _load_json(HUNTER_CACHE)
    results = []
    
    keywords = query.lower().split()
    
    for source in SKILL_SOURCES:
        source_cache = cache.get(source["name"], {})
        for skill_name, info in source_cache.items():
            text = f"{skill_name} {info.get('desc', '')}".lower()
            score = sum(0.3 for kw in keywords if kw in text)
            if info.get('tags'):
                score += sum(0.5 for kw in keywords if kw in ' '.join(info['tags']).lower())
            if score > 0:
                quality = _quality_score(info)
                final_score = round(score * 0.6 + quality * 0.4, 2)  # 混合评分
                results.append({
                    "source": source["name"],
                    "stars": source["stars"],
                    "name": skill_name,
                    "desc": info.get("desc", ""),
                    "tags": info.get("tags", []),
                    "score": final_score,
                    "quality": quality,
                    "url": info.get("url", ""),
                })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]

# ── 探索技能源 ──────────────────────────────

def _quality_score(info):
    """评估外部技能的质量分数 (0~1)"""
    score = 0.0
    desc = info.get("desc", "")
    tags = info.get("tags", [])
    content_len = info.get("content_len", 0)
    if len(desc) > 100: score += 0.3
    elif len(desc) > 50: score += 0.2
    elif len(desc) > 20: score += 0.1
    signals = ["using","via","with","for","to","api","cli","python","json","file"]
    score += min(0.3, sum(1 for s in signals if s in desc.lower()) * 0.05)
    if any(s in desc for s in ["```","import","def ","http","config","install"]):
        score += 0.2
    score += min(0.1, len(tags) * 0.03)
    if content_len > 500: score += 0.1
    elif content_len > 200: score += 0.05
    if any(p in desc.lower() for p in ["a skill for","enables","provides"]) and len(desc) < 60:
        score = max(0, score - 0.2)
    return round(min(1.0, score), 2)


def explore_source(source, force=False):
    """克隆或更新技能源仓库，建立本地缓存"""
    cache = _load_json(HUNTER_CACHE)
    source_name = source["name"]
    
    if source_name in cache and not force:
        _log(f"{source_name} 已缓存 ({len(cache[source_name])} 技能)")
        return cache[source_name]
    
    _log(f"探索 {source_name}...")
    tmp_dir = tempfile.mkdtemp()
    try:
        # 浅克隆
        subprocess.run(
            ["git", "clone", "--depth", "1", source["repo"], tmp_dir],
            capture_output=True, text=True, timeout=120
        )
        
        skills = {}
        # 搜索所有 SKILL.md 和分类 .md 文件
        for md in glob.glob(os.path.join(tmp_dir, "**", "*.md"), recursive=True):
            try:
                content = open(md, encoding="utf-8", errors="replace").read()
                rel = os.path.relpath(md, tmp_dir)
                name = os.path.basename(os.path.dirname(md))
                if name in ("", "."):
                    name = os.path.basename(md).replace(".md", "")
                
                # 格式1: SKILL.md 有 frontmatter
                desc = ""
                tags = []
                fm = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
                if fm:
                    for line in fm.group(1).split("\n"):
                        if line.startswith("description:"):
                            desc = line.split(":", 1)[1].strip().strip('"').strip("'")
                        elif line.startswith("tags:"):
                            t = line.split(":", 1)[1].strip()
                            if t.startswith("["):
                                try: tags = json.loads(t)
                                except: pass
                
                # 格式2: 分类列表 .md（awesome-openclaw-skills 格式）
                if not fm and "categories" in rel:
                    # 从文件名提取分类名
                    cat_name = os.path.basename(md).replace(".md", "")
                    # 提取每个技能条目
                    for line in content.split("\n"):
                        m = re.match(r'-\s+\[(.+?)\]\((.+?)\)\s*-\s*(.+)', line)
                        if m:
                            skill_name = m.group(1)
                            skill_url = m.group(2)
                            skill_desc = m.group(3)
                            # 从 URL 提取唯一 ID
                            skill_id = skill_url.rstrip("/").split("/")[-1] if "/" in skill_url else skill_name
                            # 生成内容指纹
                            fp = hashlib.md5(f"{skill_name}{skill_desc}".encode()).hexdigest()[:12]
                            skills[skill_id] = {
                                "desc": skill_desc,
                                "tags": [cat_name, skill_name],
                                "fingerprint": fp,
                                "content_len": len(skill_desc),
                                "url": skill_url,
                                "category": cat_name,
                            }
                    continue  # 已处理，跳到下一个文件
            except:
                continue
        
        cache[source_name] = skills
        _save_json(HUNTER_CACHE, cache)
        _log(f"✓ {source_name}: {len(skills)} 个技能缓存")
        return skills
        
    except Exception as e:
        _log(f"⚠ 探索失败: {e}")
        return {}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def explore_all_sources(force=False):
    """探索所有技能源"""
    total = 0
    for source in SKILL_SOURCES:
        skills = explore_source(source, force)
        total += len(skills)
    _log(f"共 {total} 个外部技能已缓存")
    return total

# ── 吸收技能 ──────────────────────────────

def absorb_skill(external_name, source_name, skill_info):
    """从外部吸收技能到 PipeMind"""
    cache = _load_json(HUNTER_CACHE)
    source_skills = cache.get(source_name, {})
    
    if external_name not in source_skills:
        return {"error": f"技能 {external_name} 不在缓存中"}
    
    info = source_skills[external_name]
    
    # 生成 PipeMind 技能名
    safe_name = re.sub(r'[^a-z0-9-]', '', external_name.lower().replace(" ", "-"))
    if not safe_name.startswith("pipemind-"):
        safe_name = f"pipemind-{safe_name}"
    
    # 创建技能目录
    skill_dir = os.path.join(SKILLS_DIR, safe_name)
    if os.path.exists(skill_dir):
        _log(f"技能 {safe_name} 已存在，升级中...")
    
    os.makedirs(skill_dir, exist_ok=True)
    
    # 生成 SKILL.md
    desc = info.get("desc", f"从 {source_name} 吸收的技能")
    tags = info.get("tags", [external_name])
    tags_str = json.dumps(tags)
    
    skill_content = f"""---
name: {safe_name}
description: "{desc}"
version: 1.0.0
author: PipeMind (absorbed from {source_name})
tags: {tags_str}
---

# {safe_name}

> 从 [{source_name}]({next(s['repo'] for s in SKILL_SOURCES if s['name'] == source_name)}) 吸收。
> 原始名称: {external_name}
> 内容指纹: {info.get('fingerprint', '?')}

## 用法

{desc}

## Pitfalls

- **吸收技能可能需要适配 PipeMind 的 API** — 如有异常请反馈
- **此技能是自动吸收的** — 建议手动检查和优化
"""
    
    skill_path = os.path.join(skill_dir, "SKILL.md")
    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(skill_content)
    
    # 记录吸收日志
    absorbed = _load_json(ABSORBED_LOG, {"absorbed": []})
    absorbed["absorbed"].append({
        "external_name": external_name,
        "source": source_name,
        "local_name": safe_name,
        "fingerprint": info.get("fingerprint", ""),
        "absorbed_at": datetime.datetime.now().isoformat(),
    })
    _save_json(ABSORBED_LOG, absorbed)
    
    # 重建注册表
    try:
        import pipemind_skillforge as forge
        forge.build_registry()
    except:
        pass
    
    _log(f"✅ 已吸收: {external_name} → {safe_name}")
    return {"status": "absorbed", "local_name": safe_name, "path": skill_path}

# ── 完整狩猎 ──────────────────────────────

def hunt(query):
    """完整狩猎流程：搜索外部 → 匹配 → 吸收"""
    _log(f"开始狩猎: '{query}'")
    
    # 1. 先检查本地注册表
    registry = _load_json(REGISTRY_FILE, {})
    local_matches = []
    q = query.lower()
    for name, info in registry.items():
        if q in name.lower() or q in info.get("desc", "").lower():
            local_matches.append((1.0, name, info))
    
    if local_matches:
        _log(f"本地已有匹配: {local_matches[0][1]}")
        return {"source": "local", "matches": local_matches}
    
    # 2. 确保外部技能源已探索
    explore_all_sources()
    
    # 3. 在外部源中搜索
    external = search_openclaw_skills(query)
    
    if not external:
        # 4. 用 GitHub 搜索
        _log("外部源无匹配，搜索 GitHub...")
        github_results = search_github(f"openclaw skill {query}")
        if github_results:
            for r in github_results:
                external.append({
                    "source": "github",
                    "stars": r.get("stargazersCount", 0),
                    "name": r["name"],
                    "desc": r.get("description", ""),
                    "score": 0.5,
                })
    
    if external:
        _log(f"找到 {len(external)} 个外部匹配:")
        for i, m in enumerate(external[:5]):
            ql = m.get('quality', 0)
            _log(f"  [{i}] ⭐{m.get('stars', '?')} ❓{ql} {m['name']} — {m['desc'][:50]}")
        
        # 只吸收高质量技能 (quality >= 0.5)
        top = external[0]
        quality = top.get("quality", 0)
        if quality >= 0.5 and top["source"] != "github":
            _log(f"  质量评分 {quality} ≥ 0.5，吸收中...")
            result = absorb_skill(top["name"], top["source"], top)
            return {"source": "external", "absorbed": result, "matches": external}
        else:
            _log(f"  质量评分 {quality} < 0.5，跳过吸收（仅报告）")
            return {"source": "external_low_quality", "matches": external}
    
    _log("没有找到外部匹配")
    return {"source": "none", "matches": []}

# ── 升级已吸收的技能 ──────────────────────

def upgrade_absorbed():
    """检查已吸收的技能是否有更新"""
    absorbed = _load_json(ABSORBED_LOG, {"absorbed": []})
    if not absorbed.get("absorbed"):
        _log("没有已吸收的技能需要升级")
        return
    
    _log(f"检查 {len(absorbed['absorbed'])} 个已吸收技能...")
    
    # 重新探索所有源
    explore_all_sources(force=True)
    cache = _load_json(HUNTER_CACHE)
    
    updated = 0
    for entry in absorbed["absorbed"]:
        external = entry["external_name"]
        source = entry["source"]
        old_fp = entry["fingerprint"]
        
        source_cache = cache.get(source, {})
        if external in source_cache:
            new_fp = source_cache[external].get("fingerprint", "")
            if new_fp and new_fp != old_fp:
                _log(f"🔄 {external}: 有更新，重新吸收...")
                absorb_skill(external, source, source_cache[external])
                updated += 1
    
    _log(f"升级完成: {updated} 个技能已更新")
    return updated

# ── CLI ─────────────────────────────────────

def main():
    args = sys.argv[1:]
    
    if "--explore" in args:
        force = "--force" in args
        explore_all_sources(force)
    
    elif "--search" in args:
        idx = args.index("--search") + 1
        if idx < len(args):
            q = " ".join(args[idx:])
            # 先确保已探索
            explore_all_sources()
            results = search_openclaw_skills(q)
            if results:
                print(f"\n🔍 外部搜索 '{q}' — {len(results)} 个匹配:\n")
                for r in results[:10]:
                    print(f"  [{r['score']}] ⭐{r.get('stars','?')} {r['name']}")
                    print(f"     {r['desc'][:80]}")
                    print()
            else:
                print(f"\n🔍 无匹配，试试 --hunt 完整狩猎")
    
    elif "--absorb" in args:
        idx = args.index("--absorb") + 1
        if idx < len(args):
            name = args[idx]
            source_name = args[idx + 1] if idx + 1 < len(args) else SKILL_SOURCES[0]["name"]
            result = absorb_skill(name, source_name, {})
            if "error" in result:
                print(f"  ❌ {result['error']}")
    
    elif "--hunt" in args:
        idx = args.index("--hunt") + 1
        if idx < len(args):
            q = " ".join(args[idx:])
            result = hunt(q)
            print(f"\n📋 狩猎结果: {result['source']}")
            if result.get("absorbed"):
                a = result["absorbed"]
                print(f"  ✅ 已吸收: {a.get('local_name', '?')}")
    
    elif "--upgrade" in args:
        upgrade_absorbed()
    
    elif "--status" in args:
        cache = _load_json(HUNTER_CACHE, {})
        total = sum(len(v) for v in cache.values())
        absorbed = _load_json(ABSORBED_LOG, {"absorbed": []})
        print(f"\n📊 技能猎人状态")
        print(f"   探索的源: {len(cache)} / {len(SKILL_SOURCES)}")
        print(f"   缓存技能: {total}")
        print(f"   已吸收: {len(absorbed.get('absorbed', []))}")
    
    else:
        print("用法:")
        print("  python pipemind_hunter.py --explore          探索所有技能源")
        print("  python pipemind_hunter.py --search <关键词>  搜索外部技能")
        print("  python pipemind_hunter.py --absorb <name>    吸收技能")
        print("  python pipemind_hunter.py --hunt <任务>      完整狩猎")
        print("  python pipemind_hunter.py --upgrade          升级已吸收技能")
        print("  python pipemind_hunter.py --status           查看状态")

if __name__ == "__main__":
    main()
