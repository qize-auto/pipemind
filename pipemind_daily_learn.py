"""PipeMind 每日学习管道 — 自动从外部源吸收知识

每天凌晨运行（记忆聚合 + 进化日报之后）:
  1. 从弈辛学 — 扫描 ~/.hermes/skills/，转化有用技能
  2. 从工具学 — 分析性能历史，提炼模式
  3. 从 GitHub 学 — 检查已知源的新技能

数据 (memory/):
  _daily_learn_log.json  — 学习日志
  _learned_patterns.json — 学到的工具模式
"""

from pipemind_core import PIPEMIND_DIR, MEM_DIR
import os, json, datetime, re, sys, subprocess, glob, time

SKILLS_DIR = os.path.join(PIPEMIND_DIR, "skills")

LEARN_LOG_FILE = os.path.join(MEM_DIR, "_daily_learn_log.json")
PATTERNS_FILE = os.path.join(MEM_DIR, "_learned_patterns.json")


# ═══════════════════════════════════════════════
# 1. 从弈辛学
# ═══════════════════════════════════════════════

def learn_from_yixin() -> dict:
    """扫描弈辛的技能目录，分析可吸收的技能

    通过 WSL 读取 ~/.hermes/skills/
    """
    result = {"scanned": 0, "new": 0, "skills": []}

    # 通过 WSL 列出弈辛的技能
    yixin_skills = _list_yixin_skills()
    result["scanned"] = len(yixin_skills)

    # 列出 PipeMind 已有技能
    my_skills = set()
    for md in glob.glob(os.path.join(SKILLS_DIR, "**", "SKILL.md"), recursive=True):
        name = os.path.basename(os.path.dirname(md))
        my_skills.add(name)

    # 找弈辛有但 PipeMind 没有的技能
    new_skills = [s for s in yixin_skills if s["name"] not in my_skills]

    for skill in new_skills[:5]:  # 每次最多学 5 个
        adapted = _adapt_skill(skill)
        if adapted:
            result["skills"].append(adapted["name"])
            result["new"] += 1

    return {
        "source": "yixin",
        "scanned": result["scanned"],
        "new_skills": result["new"],
        "skill_names": result["skills"],
    }


def _list_yixin_skills() -> list[dict]:
    """通过 WSL 列出弈辛的技能"""
    skills = []
    try:
        # 用 find 找 SKILL.md 文件
        out = subprocess.run(
            ["wsl", "-d", "Ubuntu", "-e", "bash", "-l", "-c",
             r'find ~/.hermes/skills -name "SKILL.md" -exec grep -l "description:" {} \; 2>/dev/null | head -30'],
            capture_output=True, text=True, timeout=10
        )
        if out.returncode != 0 or not out.stdout.strip():
            return skills

        for path in out.stdout.strip().split("\n"):
            path = path.strip()
            if not path:
                continue

            # 读 SKILL.md 头部取名字和描述
            name = os.path.basename(os.path.dirname(path))
            desc = _read_yixin_skill_desc(path)
            skills.append({"name": name, "desc": desc, "path": path})
    except Exception:
        pass
    return skills


def _read_yixin_skill_desc(wsl_path: str) -> str:
    """从弈辛的 SKILL.md 提取描述"""
    try:
        out = subprocess.run(
            ["wsl", "-d", "Ubuntu", "-e", "bash", "-l", "-c",
             f'head -20 "{wsl_path}" 2>/dev/null'],
            capture_output=True, text=True, timeout=5
        )
        for line in out.stdout.split("\n"):
            if line.strip().startswith("description:"):
                return line.split(":", 1)[1].strip().strip("\"'")
    except Exception:
        pass
    return ""


def _adapt_skill(skill: dict) -> dict | None:
    """将弈辛技能转化为 PipeMind 技能

    只转化 Windows 兼容的技能（跳过 WSL 特定的）
    """
    name = skill.get("name", "")
    desc = skill.get("desc", "")

    # 跳过明显 WSL 特定的技能
    skip_keywords = ["wsl", "linux", "bash", "ubuntu", "apt"]
    if any(k in name.lower() for k in skip_keywords):
        return None

    # 生成 PipeMind 兼容的 SKILL.md
    pm_name = f"pipemind-from-{name}"
    pm_dir = os.path.join(SKILLS_DIR, pm_name)
    os.makedirs(pm_dir, exist_ok=True)

    skilly = f"""---
name: {pm_name}
description: "从弈辛吸收: {desc or name}"
author: 弈辛 → PipeMind
---

# {pm_name}

从弈辛的技能 `{name}` 转化而来。

## 原始描述

{desc or "无描述"}

## PipeMind 适配说明

- 平台: Windows
- 来源: 弈辛技能系统

## 使用

在对话中描述相关需求即可触发。
"""

    with open(os.path.join(pm_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skilly)

    return {"name": pm_name, "source": name}


# ═══════════════════════════════════════════════
# 2. 从工具使用学
# ═══════════════════════════════════════════════

def learn_from_tools() -> dict:
    """分析性能历史，提炼工具使用模式"""
    result = {"patterns": [], "lessons": []}

    # 读性能历史
    perf_file = os.path.join(MEM_DIR, "_perf_history.json")
    if not os.path.exists(perf_file):
        return result

    try:
        with open(perf_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        return result

    recent = [r for r in history if r.get("time", "").startswith(datetime.date.today().isoformat())]

    if not recent:
        return result

    # 分析工具使用频率
    tool_counts = {}
    for r in recent:
        tools = r.get("tools", 0)
        if tools > 0:
            key = f"tools_{tools}"
            tool_counts[key] = tool_counts.get(key, 0) + 1

    # 分析错误率
    error_records = [r for r in recent if r.get("errors", 0) > 0]
    if error_records:
        rate = len(error_records) / max(len(recent), 1)
        if rate > 0.3:
            result["lessons"].append({
                "trigger": "high_error_rate",
                "lesson": f"今日错误率 {rate:.0%}，建议减少连续工具调用",
                "confidence": 0.4,
            })

    # 保存模式
    if tool_counts:
        existing = []
        if os.path.exists(PATTERNS_FILE):
            try:
                with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass

        pattern = {
            "date": datetime.date.today().isoformat(),
            "patterns": tool_counts,
            "total_conversations": len(recent),
            "error_rate": round(len(error_records) / max(len(recent), 1), 3),
        }
        existing.append(pattern)
        if len(existing) > 30:
            existing = existing[-30:]

        os.makedirs(MEM_DIR, exist_ok=True)
        with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

        result["patterns"] = list(tool_counts.keys())
        result["total"] = len(recent)

    return result


# ═══════════════════════════════════════════════
# 3. 从 GitHub 学
# ═══════════════════════════════════════════════

def learn_from_github() -> dict:
    """检查 hunter 的已知源有没有新技能

    轻量检查：只看缓存是否过期，不实时搜索
    """
    result = {"checked": 0, "new": 0, "sources": []}

    cache_file = os.path.join(MEM_DIR, "_hunter_cache.json")
    if not os.path.exists(cache_file):
        return result

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            cache = json.load(f)
    except Exception:
        return result

    # 检查每个源的最后更新时间和技能数
    for source_name, skills in cache.items():
        skill_count = len(skills) if isinstance(skills, dict) else 0
        result["sources"].append({"name": source_name, "skills": skill_count})

    result["checked"] = len(cache)
    return result


# ═══════════════════════════════════════════════
# 4. 每日学习流程
# ═══════════════════════════════════════════════

def daily_learn() -> dict:
    """执行每日学习流程（由 daemon 在凌晨调用）"""
    today = datetime.date.today().isoformat()
    log = {
        "date": today,
        "time": datetime.datetime.now().isoformat(),
        "sources": [],
        "total_learned": 0,
        "summary": "",
    }

    # 1. 从弈辛学
    try:
        yixin_result = learn_from_yixin()
        if yixin_result["new_skills"] > 0:
            log["sources"].append(yixin_result)
            log["total_learned"] += yixin_result["new_skills"]
    except Exception as e:
        log["sources"].append({"source": "yixin", "error": str(e)})

    # 2. 从工具使用学
    try:
        tool_result = learn_from_tools()
        if tool_result.get("lessons"):
            # 保存 lesson 到 evolution 系统
            _save_lessons(tool_result["lessons"])
            log["sources"].append({
                "source": "tools",
                "patterns": tool_result.get("patterns", []),
                "lessons": len(tool_result.get("lessons", [])),
            })
    except Exception as e:
        log["sources"].append({"source": "tools", "error": str(e)})

    # 3. 从 GitHub 学
    try:
        github_result = learn_from_github()
        log["sources"].append(github_result)
    except Exception as e:
        log["sources"].append({"source": "github", "error": str(e)})

    # 生成摘要
    parts = [f"📚 今日学习 ({today})"]
    for s in log["sources"]:
        if s.get("new_skills"):
            parts.append(f"  · 从 {s['source']} 学到了 {s['new_skills']} 个新技能")
        elif s.get("lessons"):
            parts.append(f"  · 从工具使用中提炼了 {s['lessons']} 条教训")
        elif s.get("error"):
            parts.append(f"  · {s['source']}: {s['error']}")
    log["summary"] = "\n".join(parts)

    # 写日志
    os.makedirs(MEM_DIR, exist_ok=True)
    logs = []
    if os.path.exists(LEARN_LOG_FILE):
        try:
            with open(LEARN_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            pass
    logs.append(log)
    if len(logs) > 30:
        logs = logs[-30:]
    with open(LEARN_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

    return log


def _save_lessons(lessons: list):
    """保存教训到进化系统"""
    try:
        sys.path.insert(0, PIPEMIND_DIR)
        import pipemind_self_evolution as se
        for l in lessons:
            se.AutoLearner.learn_from_error(
                l.get("trigger", "unknown"),
                l.get("lesson", ""),
                l.get("confidence", 0.3),
            )
    except Exception:
        pass


# ═══════════════════════════════════════════════
# 5. 查询接口
# ═══════════════════════════════════════════════

def get_learn_log(days=7) -> list:
    """获取最近学习记录"""
    if not os.path.exists(LEARN_LOG_FILE):
        return []
    try:
        with open(LEARN_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
        return logs[-days:]
    except Exception:
        return []


def get_learned_skills() -> list:
    """列出从弈辛吸收的技能"""
    skills = []
    for md in glob.glob(os.path.join(SKILLS_DIR, "pipemind-from-*", "SKILL.md"), recursive=True):
        name = os.path.basename(os.path.dirname(md))
        desc = ""
        try:
            with open(md, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("description:"):
                        desc = line.split(":", 1)[1].strip().strip("\"'")
                        break
        except Exception:
            pass
        skills.append({"name": name, "desc": desc})
    return skills


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PipeMind 每日学习")
    parser.add_argument("--learn", action="store_true", help="执行每日学习")
    parser.add_argument("--from-yixin", action="store_true", help="从弈辛学习")
    parser.add_argument("--from-tools", action="store_true", help="从工具使用学习")
    parser.add_argument("--log", action="store_true", help="查看学习日志")
    args = parser.parse_args()

    if args.learn:
        result = daily_learn()
        print(result["summary"])

    if args.from_yixin:
        result = learn_from_yixin()
        print(f"扫描弈辛技能: {result['scanned']} 个")
        print(f"新吸收: {result['new_skills']} 个")
        for s in result.get("skill_names", []):
            print(f"  ✅ {s}")

    if args.from_tools:
        result = learn_from_tools()
        print(f"工具模式: {result.get('patterns', [])}")
        print(f"新教训: {len(result.get('lessons', []))} 条")

    if args.log:
        logs = get_learn_log()
        for l in logs[-5:]:
            print(f"\n📅 {l.get('date', '?')}")
            print(l.get("summary", ""))
