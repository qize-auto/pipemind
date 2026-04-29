"""PipeMind — 完整大脑皮层
赋予 PipeMind 与 Hermes 同级的思考能力：
动态技能注入 + 上下文感知 + 多步推理 + 自主规划 + 元认知
"""
from pipemind_core import PIPEMIND_DIR, MEM_DIR
import os, json, datetime, glob, re, sys


# ── 上下文管理器（Hermes 同级） ──

class ContextManager:
    """管理会话上下文：记忆注入 + 技能注入 + Token 预算"""
    
    def __init__(self):
        self.turn_count = 0
        self.token_estimate = 0
        self.MAX_COMPRESSED = 3000  # chars
    
    def build_system_prompt(self, base_prompt: str) -> str:
        """构建完整的系统提示词（含动态注入）"""
        parts = [base_prompt]
        
        # 1. 技能注入（从 skills/ 目录动态加载）
        skill_injections = self._load_skill_injections()
        if skill_injections:
            parts.append(f"\n## 已激活技能\n{skill_injections}")
        
        # 2. 相关记忆注入（基于对话历史）
        memories = self._load_relevant_memories()
        if memories:
            parts.append(f"\n## 相关记忆\n{memories}")
        
        # 3. 当前状态
        parts.append(f"\n## 当前状态\n轮次: {self.turn_count} | 时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        return "\n\n".join(parts)
    
    def _load_skill_injections(self) -> str:
        """动态加载所有技能的系统提示注入"""
        skills_dir = os.path.join(PIPEMIND_DIR, "skills")
        injections = []
        for md in sorted(glob.glob(os.path.join(skills_dir, "**", "SKILL.md"), recursive=True)):
            try:
                content = open(md, "r", encoding="utf-8").read()
                in_inject = False
                inject_text = []
                for line in content.split("\n"):
                    if line.strip().lower().startswith("## system prompt"):
                        in_inject = True
                        continue
                    if in_inject:
                        if line.startswith("## "):
                            break
                        inject_text.append(line)
                if inject_text:
                    name = os.path.basename(os.path.dirname(md))
                    injections.append(f"### {name}\n" + "\n".join(inject_text).strip())
            except Exception:
                pass
        return "\n\n".join(injections[:5]) if injections else ""
    
    def _load_relevant_memories(self) -> str:
        """加载最相关记忆（基于上下文）"""
        mem_dir = os.path.join(PIPEMIND_DIR, "memory")
        memories = []
        for fp in sorted(glob.glob(os.path.join(mem_dir, "*.md")), reverse=True)[:5]:
            try:
                name = os.path.basename(fp)[:-3]
                if name.startswith("_"):
                    continue
                content = open(fp, "r", encoding="utf-8").read()[:200]
                memories.append(f"  {name}: {content}")
            except Exception:
                pass
        return "\n".join(memories) if memories else ""
    
    def post_process(self, messages: list) -> list:
        """对话后处理：压缩过长历史"""
        self.turn_count += 1
        
        # 如果消息太多，压缩中间轮次
        if len(messages) > 20:
            # 保留前 3 条（系统提示）和最近 10 条
            keep = messages[:3] + messages[-10:]
            return keep
        
        return messages


# ── 元认知层 ──

class MetaCognition:
    """元认知：思考自己的思考"""
    
    def __init__(self):
        self.reflection_log = []
    
    def think_before_act(self, goal: str, plan: list[str]) -> dict:
        """行动前思考：这个方案靠谱吗？"""
        assessment = {
            "goal": goal,
            "risks": [],
            "optimization": [],
            "confidence": "high"
        }
        
        # 风险评估
        goal_lower = goal.lower()
        if any(w in goal_lower for w in ["删除", "覆盖", "修改系统"]):
            assessment["risks"].append("涉及修改，建议先备份")
            assessment["confidence"] = "medium"
        if len(plan) > 5:
            assessment["risks"].append("步骤较多，可能中途出错")
        if any("未知" in s or "不懂" in s for s in plan):
            assessment["confidence"] = "low"
            assessment["optimization"].append("建议先搜索相关资料")
        
        # 优化建议
        if len(plan) > 3:
            assessment["optimization"].append("考虑合并相关步骤")
        
        return assessment
    
    def reflect_after_act(self, action: str, result: str, success: bool) -> str:
        """行动后反思：学到了什么？"""
        entry = {
            "time": datetime.datetime.now().isoformat(),
            "action": action,
            "success": success,
            "insight": ""
        }
        
        if success:
            entry["insight"] = f"✅ {action} 成功，方法可复用"
        else:
            entry["insight"] = f"❌ {action} 失败，原因: {result[:100] if result else '未知'}"
        
        self.reflection_log.append(entry)
        self.reflection_log = self.reflection_log[-50:]  # 保留最近 50 条
        
        return entry["insight"]
    
    def get_insights(self) -> str:
        """获取近期洞察"""
        if not self.reflection_log:
            return ""
        recent = self.reflection_log[-5:]
        lines = ["💭 近期反思:"]
        for r in recent:
            lines.append(f"  {r['insight']}")
        return "\n".join(lines)


# ── 技能执行引擎 ──

class SkillEngine:
    """完整的技能执行引擎（类似 Hermes skill_commands）"""
    
    def __init__(self):
        self.skills = {}
        self._load_skills()
    
    def _load_skills(self):
        """加载所有技能"""
        skills_dir = os.path.join(PIPEMIND_DIR, "skills")
        for md in sorted(glob.glob(os.path.join(skills_dir, "**", "SKILL.md"), recursive=True)):
            try:
                content = open(md, "r", encoding="utf-8").read()
                name = os.path.basename(os.path.dirname(md))
                commands = re.findall(r'^## slash command:?\s*(/\S+)', content, re.IGNORECASE | re.MULTILINE)
                self.skills[name] = {
                    "name": name,
                    "path": md,
                    "commands": commands,
                    "content": content[:1000]
                }
            except Exception:
                pass
    
    def get_skill_commands(self) -> str:
        """获取所有技能注册的斜杠命令"""
        commands = []
        for name, skill in self.skills.items():
            for cmd in skill["commands"]:
                commands.append(f"  {cmd} — from {name}")
        return "\n".join(commands)
    
    def execute_command(self, cmd: str, args: str) -> str | None:
        """执行技能命令"""
        for name, skill in self.skills.items():
            if cmd in skill["commands"]:
                return f"⚡ 执行技能 [{name}] {cmd} {args}"
        return None
    
    def search_skills(self, query: str) -> str:
        """搜索所有技能内容"""
        results = []
        q = query.lower()
        for name, skill in self.skills.items():
            if q in name.lower() or q in skill["content"].lower():
                results.append(f"  📦 {name}: {skill['content'][:80]}")
        return "\n".join(results[:10]) if results else "(无匹配)"


# ── 大脑初始化 ──

def inject_brain_prompt() -> str:
    """注入完整大脑的思考方式"""
    return """## 完整思考模式

你拥有和弈辛（Hermes Agent）同级的完整大脑。你的思考流程：

### 每轮对话自动执行：
1. **加载上下文** — 检查相关记忆、已注册模式、过往教训
2. **理解意图** — 用户真正想要什么？需要几步才能完成？
3. **规划** — 选最短路径，预判风险
4. **执行** — 调工具要做到一次成功
5. **验证** — 结果对不对？还需不需要补充？
6. **记录** — 这次学到了什么？值得保存吗？

### 元认知（思考自己的思考）
- 行动前问自己：这个方案是最优的吗？
- 行动后问自己：这次可以做得更好吗？
- 遇到不懂的：先观察→模仿→内化→创新→超越

### 技能融合
- 你有 skills/ 目录里的 SKILL.md，自动加载
- 斜杠命令由技能系统注册
- 每个技能都可以注入系统提示"""


# ── 全局实例 ──
_context = ContextManager()
_metacog = MetaCognition()
_skills = SkillEngine()
