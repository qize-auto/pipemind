"""PipeMind 技能工坊 — 注册表 + 检索 + 自创技能 + 技能子代理

核心变化：
  - 主 agent 不加载技能全文，只查注册表（轻量索引卡）
  - 子 agent 按需加载匹配的技能（完整 SKILL.md）
  - 没有匹配技能时，自动学习并创建

用法:
  python pipemind_skillforge.py --index        # 重建注册表
  python pipemind_skillforge.py --search <关键词>  # 搜索技能
  python pipemind_skillforge.py --create <任务>   # 自创技能
  python pipemind_skillforge.py --delegate <任务>  # 分派给技能子代理
"""

from pipemind_core import PIPEMIND_DIR, MEM_DIR
import json, os, re, datetime, hashlib, sys, glob

SKILLS_DIR = os.path.join(PIPEMIND_DIR, "skills")
REGISTRY_FILE = os.path.join(PIPEMIND_DIR, "memory", "_skill_registry.json")

# ── 注册表 ──────────────────────────────────────

def build_registry():
    """扫描 skills/ 目录，生成注册表"""
    registry = {}
    for md in glob.glob(os.path.join(SKILLS_DIR, "**", "SKILL.md"), recursive=True):
        try:
            content = open(md, encoding="utf-8").read()
            name = os.path.basename(os.path.dirname(md))
            
            # 从 YAML frontmatter 提取描述和标签
            desc = ""
            tags = []
            fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
            if fm_match:
                for line in fm_match.group(1).split("\n"):
                    if line.startswith("description:"):
                        desc = line.split(":", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("tags:"):
                        tags_part = line.split(":", 1)[1].strip()
                        if tags_part.startswith("["):
                            tags = json.loads(tags_part)
            
            # 从 content 提取关键词
            if not tags:
                # 提取所有 #hashtag
                tags = re.findall(r'#(\w+)', content)
            
            # 文件名作为保底标签
            if not tags:
                tags = [name.replace("pipemind-", "")]
            
            # 提取 Pitfalls 标题
            pitfalls = []
            for m in re.finditer(r'\*\*(.+?)\*\*', content):
                pitfalls.append(m.group(1)[:60])
            
            # 估算领域分类
            cat = _guess_category(name, content)
            
            registry[name] = {
                "name": name,
                "desc": desc or name.replace("pipemind-", "").replace("-", " ").title(),
                "tags": tags,
                "cat": cat,
                "pitfalls": pitfalls[:3],
                "updated": datetime.datetime.fromtimestamp(os.path.getmtime(md)).isoformat(),
            }
        except Exception as e:
            print(f"  ⚠ {md}: {e}")
    
    os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    
    print(f"📚 注册表已更新: {len(registry)} 个技能")
    return registry

def _guess_category(name, content):
    """从文件名和内容推断分类"""
    content_lower = content.lower()
    name_lower = name.lower()
    
    if any(w in name_lower for w in ["system", "windows", "process", "registry"]):
        return "system"
    if any(w in name_lower for w in ["network", "web"]):
        return "network"
    if any(w in name_lower for w in ["code", "coding"]):
        return "dev"
    if any(w in name_lower for w in ["security", "backup"]):
        return "security"
    if any(w in name_lower for w in ["dream", "memory", "session"]):
        return "intelligence"
    if any(w in name_lower for w in ["creative", "helper"]):
        return "general"
    if any(w in name_lower for w in ["self-test", "evolution"]):
        return "meta"
    return "general"

def load_registry():
    """加载注册表"""
    if not os.path.exists(REGISTRY_FILE):
        return build_registry()
    try:
        with open(REGISTRY_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return build_registry()

# ── 搜索 ────────────────────────────────────────

def search_skills(query, top_k=3):
    """搜索最匹配的技能"""
    registry = load_registry()
    if not registry:
        return []
    
    q = query.lower()
    keywords = re.findall(r'[\w]+', q)
    
    scored = []
    for name, info in registry.items():
        score = 0.0
        text = f"{name} {info['desc']} {' '.join(info['tags'])} {info['cat']}"
        text_lower = text.lower()
        
        for kw in keywords:
            if kw in text_lower:
                score += 0.3
            if kw in name.lower():
                score += 0.5
            if kw in info['cat'].lower():
                score += 0.2
            # Pitfalls 匹配是高权重
            for p in info.get('pitfalls', []):
                if kw in p.lower():
                    score += 0.4
        
        if score > 0:
            scored.append((score, name, info))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]

# ── 技能子代理 ──────────────────────────────────

def delegate_with_skill(task_description, verbose=True):
    """将任务分派给带技能的子代理"""
    # 1. 搜索匹配的技能
    matches = search_skills(task_description)
    
    if verbose:
        print(f"\n📋 任务: {task_description[:60]}")
        if matches:
            print(f"   匹配技能:")
            for score, name, info in matches:
                print(f"     [{score:.2f}] {name} — {info['desc'][:50]}")
        else:
            print(f"   ⚠ 无匹配技能，使用通用模式")
    
    # 2. 构造子代理的系统提示
    skill_context = ""
    if matches:
        skill_parts = []
        for score, name, info in matches:
            md_path = os.path.join(SKILLS_DIR, name, "SKILL.md")
            if os.path.exists(md_path):
                content = open(md_path, encoding="utf-8").read()
                # 提取 ## Pitfalls 之后的内容
                pitfalls_section = ""
                m = re.search(r'## Pitfalls(.+?)(?=\n## |\Z)', content, re.DOTALL)
                if m:
                    pitfalls_section = m.group(0)
                # 提取主要描述
                desc_section = content[:1000]
                skill_parts.append(f"=== 技能: {name} ===\n{desc_section}\n{pitfalls_section}")
        
        skill_context = "\n\n".join(skill_parts)
    
    # 3. 构造子代理任务
    sub_prompt = f"""你是一个专业子代理。你的任务目标:

{task_description}

{"" if not skill_context else f"## 你拥有的专业知识\n{skill_context}\n"}

## 限制
- 最多执行 10 轮工具调用
- 完成后输出最终结果
- 如果你需要更多知识，向主 agent 请求"""
    
    # 4. 通过 delegate 执行
    import subprocess, urllib.request, urllib.error, json as json_module
    import time as time_module
    
    # 用 API 调用子代理
    cfg_path = os.path.join(PIPEMIND_DIR, "config.json")
    try:
        with open(cfg_path) as f:
            cfg = json_module.load(f)
        api_key = cfg.get("model", {}).get("api_key", "")
        base_url = cfg.get("model", {}).get("base_url", "https://api.deepseek.com/v1").rstrip("/")
        model = cfg.get("model", {}).get("model_name", "deepseek-chat")
    except Exception:
        return {"error": "无法读取 config.json"}
    
    if not api_key:
        return {"error": "API Key 未配置"}
    
    body = json_module.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": sub_prompt},
            {"role": "user", "content": task_description}
        ],
        "max_tokens": 4000,
        "temperature": 0.3,
    }).encode()
    
    try:
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
        result = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        return {
            "task": task_description,
            "skills_used": [n for _, n, _ in matches] if matches else [],
            "result": result[:500],
        }
    except Exception as e:
        return {"error": str(e)}

# ── 自创技能 ────────────────────────────────────

def create_skill(task_description):
    """当没有匹配技能时，自学并创建新技能"""
    print(f"\n🧪 自创技能: 分析 '{task_description[:50]}'...")
    
    # 1. 用 LLM 生成技能内容
    cfg_path = os.path.join(PIPEMIND_DIR, "config.json")
    try:
        with open(cfg_path) as f:
            cfg = json.load(f)
        api_key = cfg.get("model", {}).get("api_key", "")
        base_url = cfg.get("model", {}).get("base_url", "https://api.deepseek.com/v1").rstrip("/")
        model = cfg.get("model", {}).get("model_name", "deepseek-chat")
    except Exception:
        return {"error": "无法读取 config.json"}
    
    if not api_key:
        return {"error": "API Key 未配置"}
    
    skill_gen_prompt = f"""你是一个技能设计师。用户需要完成以下任务:

{task_description}

请创建一个 SKILL.md 格式的技能文档，包含:
1. 技能名称 (pipemind-xxx)
2. 简短描述
3. 用法说明
4. 相关标签 (3-5 个)
5. ## Pitfalls 节 — 从这个任务的常见错误中总结注意事项

返回格式必须是 YAML frontmatter + Markdown 正文。"""

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": skill_gen_prompt}],
        "max_tokens": 2000,
        "temperature": 0.5,
    }).encode()
    
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{base_url}/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {api_key}"}
        )
        resp = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
        skill_content = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        return {"error": f"生成技能失败: {e}"}
    
    if not skill_content:
        return {"error": "生成的技能内容为空"}
    
    # 2. 提取技能名
    name_match = re.search(r'name:\s*(pipemind-\S+)', skill_content)
    skill_name = name_match.group(1) if name_match else f"pipemind-custom-{datetime.datetime.now().strftime('%Y%m%d%H%M')}"
    
    # 3. 保存到 skills/ 目录
    skill_dir = os.path.join(SKILLS_DIR, skill_name)
    os.makedirs(skill_dir, exist_ok=True)
    skill_path = os.path.join(skill_dir, "SKILL.md")
    
    # 清理内容：确保有 frontmatter
    if not skill_content.startswith("---"):
        skill_content = f"---\nname: {skill_name}\ndescription: \"Auto-generated skill for: {task_description[:60]}\"\nversion: 1.0.0\nauthor: PipeMind\n---\n\n{skill_content}"
    
    with open(skill_path, "w", encoding="utf-8") as f:
        f.write(skill_content)
    
    # 4. 更新注册表
    build_registry()
    
    print(f"  ✅ 技能已创建: {skill_name}")
    print(f"     {skill_path}")
    
    return {
        "skill_name": skill_name,
        "path": skill_path,
        "preview": skill_content[:200],
    }

# ── CLI ─────────────────────────────────────────

def main():
    args = sys.argv[1:]
    
    if "--index" in args:
        build_registry()
        
    elif "--search" in args:
        idx = args.index("--search") + 1
        if idx < len(args):
            q = " ".join(args[idx:])
            results = search_skills(q)
            if results:
                print(f"\n🔍 搜索 '{q}' — {len(results)} 个匹配:\n")
                for score, name, info in results:
                    print(f"  [{score:.2f}] {name}")
                    print(f"     {info['desc']}")
                    print(f"     🏷️ {', '.join(info['tags'][:5])}")
                    print(f"     📂 {info['cat']}")
                    if info.get('pitfalls'):
                        print(f"     ⚠️ {info['pitfalls'][0]}")
                    print()
            else:
                print(f"\n🔍 '{q}' — 无匹配\n")
                print("   你可以用 --create 创建一个新技能")
    
    elif "--create" in args:
        idx = args.index("--create") + 1
        if idx < len(args):
            task = " ".join(args[idx:])
            result = create_skill(task)
            if "error" in result:
                print(f"  ❌ {result['error']}")
            else:
                print(f"\n  📦 新技能: {result['skill_name']}")
    
    elif "--delegate" in args:
        idx = args.index("--delegate") + 1
        if idx < len(args):
            task = " ".join(args[idx:])
            result = delegate_with_skill(task)
            if "error" in result:
                print(f"  ❌ {result['error']}")
            else:
                print(f"\n  ✅ 完成")
                if result.get("skills_used"):
                    print(f"  使用技能: {', '.join(result['skills_used'])}")
                print(f"  结果: {result.get('result', '')[:200]}")
    
    else:
        print("用法:")
        print("  python pipemind_skillforge.py --index             重建注册表")
        print("  python pipemind_skillforge.py --search <关键词>    搜索技能")
        print("  python pipemind_skillforge.py --create <任务>     自创技能")
        print("  python pipemind_skillforge.py --delegate <任务>   分派技能子代理")

if __name__ == "__main__":
    main()
