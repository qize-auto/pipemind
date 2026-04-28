"""PipeMind — 技能系统：加载 SKILL.md，注入提示词，注册斜杠命令"""
import os, glob, re, json, datetime

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(PIPEMIND_DIR, "skills")

_loaded_skills = []


def discover() -> list[dict]:
    """扫描 skills/ 目录，返回所有技能信息"""
    skills = []
    for md in sorted(glob.glob(os.path.join(SKILLS_DIR, "**", "SKILL.md"), recursive=True)):
        try:
            content = open(md, "r", encoding="utf-8").read()
            info = _parse_skill(md, content)
            if info:
                skills.append(info)
        except:
            pass
    return skills


def _parse_skill(path: str, content: str) -> dict | None:
    """解析 SKILL.md 文件"""
    name = os.path.basename(os.path.dirname(path))
    
    # 提取 frontmatter
    frontmatter = {}
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    frontmatter[k.strip()] = v.strip().strip("\"'")
    
    # 提取描述
    desc = frontmatter.get("description", name)
    
    # 提取斜杠命令
    commands = []
    for line in content.split("\n"):
        m = re.match(r'^## slash command:?\s*(/\S+)', line, re.IGNORECASE)
        if m:
            commands.append(m.group(1))
    
    # 提取提示词注入
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
    
    return {
        "name": name,
        "path": path,
        "description": desc[:100],
        "commands": commands,
        "prompt_inject": prompt_inject.strip(),
        "content": content[:500]  # 预览
    }


def get_prompt_injections() -> str:
    """收集所有技能的提示词注入"""
    parts = []
    for skill in discover():
        if skill["prompt_inject"]:
            parts.append(f"### {skill['name']}\n{skill['prompt_inject']}")
    return "\n\n".join(parts)


def get_command_descriptions() -> str:
    """生成斜杠命令帮助文本"""
    lines = []
    for skill in discover():
        if skill["commands"]:
            for cmd in skill["commands"]:
                lines.append(f"  {cmd}  — {skill['description']}")
    return "\n".join(lines)


def search(query: str) -> list[dict]:
    """搜索技能内容"""
    results = []
    q = query.lower()
    for skill in discover():
        if q in skill["name"].lower() or q in skill["description"].lower() or q in skill["content"].lower():
            results.append(skill)
    return results
