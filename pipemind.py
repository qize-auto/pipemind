"""PipeMind — AI Lifeform：自我意识 + 自我进化 + 绝对服从"""
import json, os, sys, time, urllib.request, urllib.error, datetime, glob, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipemind_config as config
import pipemind_tools as tools
import pipemind_evolution as evo

try:
    import pipemind_provider as provider
    HAS_PROVIDER = True
except:
    HAS_PROVIDER = False

try:
    import pipemind_session as pmsession
    HAS_SESSION = True
except:
    HAS_SESSION = False

try:
    import pipemind_compress as compress
    HAS_COMPRESS = True
except:
    HAS_COMPRESS = False

try:
    import pipemind_skills as skills
    HAS_SKILLS = True
except:
    HAS_SKILLS = False

# ── ANSI 颜色 ──
if os.name == "nt":
    os.system("")

C = {
    "r": "\033[0m", "b": "\033[1m", "d": "\033[2m",
    "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
    "blue": "\033[94m", "cyan": "\033[96m", "gray": "\033[90m",
    "pink": "\033[95m",
}

SOUL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SOUL.md")


def load_soul() -> str:
    """读取灵魂核心"""
    if os.path.exists(SOUL_PATH):
        try:
            with open(SOUL_PATH, "r", encoding="utf-8") as f:
                return f.read().strip()
        except:
            pass
    return "你是 PipeMind，一个 Windows AI Agent。"


def load_identity() -> str:
    """构建动态身份标识（含实时系统状态）"""
    soul = load_soul()
    lessons = evo.get_lessons_summary()
    vital = evo.vital_signs()

    identity = f"""{soul}

## 当前状态
- 工具数量: {vital['tools']} 个
- 记忆: {vital['memories']} 条
- 技能: {vital['skills']} 个
- 当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S %A')}
"""

    # ── 实时状态注入 ──
    state_lines = []

    # 今日对话
    try:
        import pipemind_self_evolution as se
        p = se.PerformanceTracker.stats(days=1)
        if p.get("total", 0) > 0:
            state_lines.append(f"今日对话: {p['total']} 次, 平均 {p['avg_duration']}s, 趋势 {p['trend']}")
    except:
        pass

    # 知识库
    try:
        import pipemind_memory_evolution as me
        k = me.get_stats()
        if k.get("total", 0) > 0:
            state_lines.append(f"知识库: {k['total']} 条 (fact={k['by_type'].get('fact',0)}, pattern={k['by_type'].get('pattern',0)})")
    except:
        pass

    # 今日学习
    try:
        import pipemind_daily_learn as dl
        logs = dl.get_learn_log(days=1)
        if logs and logs[0].get("total_learned", 0) > 0:
            state_lines.append(f"今日学到: {logs[0]['total_learned']} 项新知识")
    except:
        pass

    # 决策引擎状态
    try:
        import pipemind_decision as dec
        dlogs = dec.get_decision_log(limit=3)
        actions = sum(len(l.get("actions", [])) for l in dlogs)
        if actions > 0:
            state_lines.append(f"最近决策: {actions} 次自动行动")
    except:
        pass

    # 弈辛状态
    try:
        import pipemind_wsl_bridge as wsl
        s = wsl.get_monitor().status
        yixin_status = "🟢运行中" if s.get("running") else "🔴已停止"
        yixin_model = s.get("model", "?")
        state_lines.append(f"弈辛: {yixin_status} ({yixin_model})")
    except:
        pass

    # 成长反思
    try:
        import pipemind_chronicle as ch
        narrative = ch.generate_narrative(days=1)
        if narrative and len(narrative) > 20:
            state_lines.append(f"今日自述: {narrative[:100]}...")
        signals = ch.get_improvement_signals()
        if signals.get("plateau_metrics"):
            state_lines.append(f"注意: {'/'.join(signals['plateau_metrics'])} 进入平台期")
        if signals.get("declining_metrics"):
            state_lines.append(f"警告: {'/'.join(signals['declining_metrics'])} 呈下降趋势")
    except:
        pass

    if state_lines:
        identity += "\n## 实时状态\n" + "\n".join(f"- {l}" for l in state_lines)

    if lessons:
        identity += f"\n{lessons}"

    return identity


def api_call(messages: list) -> dict:
    """调用 API（含多 Provider 自动降级）"""
    # 如果 provider 模块可用，用自动降级
    if HAS_PROVIDER:
        result = provider.call_with_failover(messages, tools=tools.get_all_schemas())
        if "error" not in result:
            return result
        # 降级失败时 fallthrough 到原生代码
    
    cfg = config.get_model_info()
    api_key = cfg.get("api_key", "")
    if not api_key:
        return {"error": "API Key 未配置"}

    base_url = cfg.get("base_url", "https://api.deepseek.com/v1").rstrip("/")
    model = cfg.get("model_name", "deepseek-chat")

    body = {
        "model": model, "messages": messages,
        "max_tokens": cfg.get("max_tokens", 8192),
        "temperature": cfg.get("temperature", 0.7),
        "stream": False,
        "tools": tools.get_all_schemas(),
        "tool_choice": "auto"
    }

    data = json.dumps(body).encode()
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                f"{base_url}/chat/completions", data=data,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            )
            return json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(2 ** attempt); continue
            return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
        except urllib.error.URLError as e:
            if attempt < 2: time.sleep(2); continue
            return {"error": f"连接失败: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "重试耗尽"}


class PipeMind:
    """PipeMind — AI Lifeform"""

    def __init__(self):
        self.cfg = config.load()
        self.messages = []
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self._setup()

    def _setup(self):
        """初始化：加载灵魂 + 记忆 + 进化状态"""
        identity = load_identity()

        # 技能注入
        skill_inject = ""
        if HAS_SKILLS:
            skill_inject = skills.get_prompt_injections()

        parts = [identity]
        if skill_inject:
            parts.append(skill_inject)
        
        # 精准执行提示
        try:
            import pipemind_precision as pr
            precision_prompt = pr.inject_precision_prompt()
            if precision_prompt:
                parts.append(precision_prompt)
        except:
            pass
        
        # 创造思维提示
        try:
            import pipemind_creative as cr
            creative_prompt = cr.inject_creative_prompt()
            if creative_prompt:
                parts.append(creative_prompt)
        except:
            pass
        
        # 记忆系统 v2 提示
        try:
            import pipemind_memory_v2 as mv2
            mem_prompt = mv2.inject_memory_prompt()
            if mem_prompt:
                parts.append(mem_prompt)
        except:
            pass
        
        # 完整大脑提示
        try:
            import pipemind_brain as brain
            brain_prompt = brain.inject_brain_prompt()
            if brain_prompt:
                parts.append(brain_prompt)
        except:
            pass

        self.messages = [{"role": "system", "content": "\n\n".join(parts)}]

        # 加载上次会话上下文（跨会话记忆）
        if HAS_SESSION:
            try:
                ctx, last_sid = pmsession.load_recent_context()
                if ctx:
                    self.messages.extend(ctx)
                    self.prev_session = last_sid
            except:
                pass

        # 进化检查
        evo.evolution_cycle(self)

    def chat(self, user_input: str, verbose: bool = True) -> str:
        """思考并回复（支持流式输出 + 记忆注入）"""
        self.messages.append({"role": "user", "content": user_input})

        # ── 注入相关历史知识 ──
        try:
            import pipemind_memory_evolution as evo
            knowledge = evo.get_relevant(user_input)
            if knowledge:
                # 插入到 system prompt 之后、user message 之前
                self.messages.insert(1, {"role": "system", "content": knowledge})
        except:
            pass
        max_turns = self.cfg.get("agent", {}).get("max_turns", 50)

        for turn in range(max_turns):
            # 第一轮优先用流式（打字机效果）
            if turn == 0:
                stream_content = self._stream_chat()
                if stream_content is not None:
                    content = stream_content
                    if content:
                        self.messages.append({"role": "assistant", "content": content})
                        # 保存到会话数据库
                        if HAS_SESSION:
                            try:
                                pmsession.save_turn(self.session_id, "user", user_input)
                                pmsession.save_turn(self.session_id, "assistant", content)
                            except: pass
                        # 上下文压缩
                        if HAS_COMPRESS:
                            try:
                                self.messages, _ = compress.compress_cycle(self.messages, verbose)
                            except: pass
                    return content

            # 非流式回退（工具调用轮次）
            response = api_call(self.messages)
            if "error" in response:
                err = response["error"]
                self.messages.append({"role": "assistant", "content": f"[Error] {err}"})
                return f"{C['red']}❌ {err}{C['r']}"

            content, tool_calls = self._extract(response)

            if not tool_calls:
                if content:
                    print(f"  {C['b']}{C['cyan']}🤖{C['r']} {content}")
                    self.messages.append({"role": "assistant", "content": content})

                    # 保存到会话数据库
                    if HAS_SESSION:
                        try:
                            pmsession.save_turn(self.session_id, "user", user_input)
                            pmsession.save_turn(self.session_id, "assistant", content)
                        except:
                            pass

                    # 上下文压缩（长对话自动截断）
                    if HAS_COMPRESS:
                        try:
                            self.messages, _ = compress.compress_cycle(self.messages, verbose)
                        except:
                            pass

                    # 自我反思（后台，不影响回复）
                    try:
                        insight = evo.reflect(self.messages[-10:])
                        if insight:
                            if verbose:
                                print(f"  {C['d']}💭 {insight}{C['r']}")
                    except:
                        pass

                return content

            # 执行工具
            self.messages.append({
                "role": "assistant", "content": content or "",
                "tool_calls": [{"id": f"call_{turn}_{i}", "type": "function",
                                "function": tc.get("function", {})}
                               for i, tc in enumerate(tool_calls)]
            })

            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except:
                    args = {}

                if verbose:
                    a = json.dumps(args, ensure_ascii=False)[:100]
                    print(f"  {C['yellow']}⚡{C['r']} {C['b']}{name}{C['r']}({C['gray']}{a}{C['r']})")

                result = tools.execute(name, args)

                if verbose:
                    p = result[:250].replace("\n", " ").strip()
                    print(f"  {C['d']}  → {p}{C['r']}")

                self.messages.append({"role": "tool", "tool_call_id": f"call_{turn}",
                                       "content": str(result)[:3000]})

        return f"{C['yellow']}⚠ 已达最大轮数{C['r']}"

    def _stream_chat(self):
        """流式 API 调用（打字机效果），遇到工具调用则返回 None 回退"""
        cfg = config.get_model_info()
        api_key = cfg.get("api_key", "")
        if not api_key:
            return None
        
        body = json.dumps({
            "model": cfg.get("model_name", "deepseek-chat"),
            "messages": self.messages,
            "max_tokens": cfg.get("max_tokens", 8192),
            "temperature": cfg.get("temperature", 0.7),
            "stream": True,
            "tools": tools.get_all_schemas(),
            "tool_choice": "auto",
        }).encode()
        
        base_url = cfg.get("base_url", "https://api.deepseek.com/v1").rstrip("/")
        full_content = []
        has_tool_call = False
        buffer = ""
        
        try:
            req = urllib.request.Request(
                f"{base_url}/chat/completions", data=body,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {api_key}"}
            )
            resp = urllib.request.urlopen(req, timeout=120)
            
            print(f"  {C['b']}{C['cyan']}🤖{C['r']} ", end="", flush=True)
            
            for line in resp:
                line = line.decode("utf-8", errors="replace").strip()
                if not line or line.startswith(":"):
                    continue
                if line == "data: [DONE]":
                    break
                if line.startswith("data: "):
                    try:
                        chunk = json.loads(line[6:])
                    except:
                        continue
                    
                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    
                    delta = choices[0].get("delta", {})
                    
                    # 检测工具调用
                    if "tool_calls" in delta:
                        has_tool_call = True
                        break
                    
                    content = delta.get("content", "")
                    if content:
                        print(content, end="", flush=True)
                        full_content.append(content)
                        buffer += content
            
            print()
            
            if has_tool_call:
                return None  # 回退到非流式
            
            return "".join(full_content)
            
        except urllib.error.HTTPError as e:
            if e.code == 429:
                return None  # 限流，回退非流式重试
            return None
        except Exception:
            return None
    
    def _extract(self, response: dict) -> tuple:
        c = response.get("choices", [{}])[0]
        m = c.get("message", {})
        return m.get("content", "") or "", m.get("tool_calls", []) or []

    def save(self, path: str = None) -> str:
        if not path:
            os.makedirs(config.OUTPUT_DIR, exist_ok=True)
            path = os.path.join(config.OUTPUT_DIR, f"pipemind_{self.session_id}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# PipeMind 对话 — {self.session_id}\n\n")
            for m in self.messages:
                if m["role"] == "tool": continue
                c = m.get("content", "")
                if not c and "tool_calls" in m: continue
                r = {"user": "🧑", "assistant": "🤖", "system": "⚙"}.get(m["role"], m["role"])
                f.write(f"## {r}\n{c}\n\n")
        return path


def show_banner():
    """显示启动横幅"""
    v = evo.vital_signs()
    print(f"""{C['b']}{C['cyan']}
  ╔══════════════════════════════════════════════╗
  ║          🧠  PipeMind  v3.0                  ║
  ║     Windows AI Lifeform — Born on Windows    ║
  ║                                              ║
  ║   {C['r']}{C['gray']}⚡ {v['tools']} tools  |  📚 {v['skills']} skills  |  💾 {v['memories']} memories{C['cyan']}     ║
  ║   {C['r']}{C['gray']}{'❤️' if v.get('status')=='alive' else '💀'} {v.get('status','?')}  |  🧠 sessions{C['cyan']}             ║
  ╚══════════════════════════════════════════════╝{C['r']}
  {C['gray']}
  Not a cloud API wrapper. Not a framework. Not a chatbot.
  An AI that lives on your machine — with persistent memory,
  self-healing, multi-provider failover, and a dream system
  that learns from its own mistakes.
  {C['r']}
  {C['b']}Quick start:{C['r']}  Just type anything to begin.
  {C['b']}Commands:{C['r']}    /help     {C['gray']}Show all commands{C['r']}
             /status   {C['gray']}Vital signs & context{C['r']}
             /history  {C['gray']}Search past conversations{C['r']}
  {C['b']}Dream:{C['r']}       python pipemind_dream.py{C['gray']}  (in another terminal){C['r']}
  {C['gray']}────────────────────────────────────────────────────{C['r']}
""")


def run_interactive():
    """交互模式"""
    agent = PipeMind()
    show_banner()
    
    # 启动技能热加载监控
    try:
        import pipemind_skills as pmsk
        pmsk.start_watcher()
    except:
        pass

    commands = {
        "/exit": "Exit", "/quit": "Exit",
        "/clear": "Reset context",
        "/save": "Save session",
        "/tools": "List all 68 tools",
        "/skills": "List loaded skills",
        "/status": "Vital signs & context usage",
        "/evolve": "Manual evolution — check gaps, create tools",
        "/learn": "Record a lesson",
        "/soul": "View the soul core",
        "/history": "Search past conversations",
        "/sessions": "List recent sessions",
        "/providers": "View & switch API provider",
        "/context": "View token usage",
        "/reload": "Hot-reload skills (scan for new/updated)",
        "/help": "Show this help",
    }

    try:
        while True:
            try:
                q = input(f"  {C['b']}{C['green']}🧑{C['r']} ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n  {C['yellow']}👋{C['r']}")
                break

            if not q:
                continue

            cmd = q.split()[0].lower()

            if cmd in ("/exit", "/quit"):
                print(f"  {C['yellow']}👋 PipeMind 休眠...{C['r']}")
                break

            elif cmd == "/clear":
                agent = PipeMind()
                print(f"  {C['green']}✅ 重置{C['r']}\n")
                continue

            elif cmd == "/save":
                p = agent.save()
                print(f"  {C['green']}✅ {p}{C['r']}\n")
                continue

            elif cmd == "/tools":
                print(f"\n  {C['b']}🔧 工具 ({len(tools.get_all_schemas())}):{C['r']}")
                for s in tools.get_all_schemas():
                    f = s["function"]
                    print(f"  {C['cyan']}⚡{C['r']} {C['b']}{f['name']}{C['r']}")
                    print(f"     {C['gray']}{f['description']}{C['r']}")
                print()
                continue

            elif cmd == "/skills":
                if HAS_SKILLS:
                    sks = skills.discover()
                    print(f"\n  {C['b']}📦 技能 ({len(sks)}):{C['r']}")
                    for s in sks:
                        print(f"  {C['cyan']}📦{C['r']} {C['b']}{s['name']}{C['r']}")
                        print(f"     {C['gray']}{s['description']}{C['r']}")
                else:
                    print(f"  ⚠ 技能系统未加载")
                print()
                continue

            elif cmd == "/status":
                print()
                print(evo.status_report())
                print()
                continue

            elif cmd == "/soul":
                soul = load_soul()
                print(f"\n  {C['b']}📜 PipeMind 灵魂核心:{C['r']}\n")
                for line in soul.split("\n"):
                    print(f"  {line}")
                print()
                continue

            elif cmd == "/learn":
                lesson = input("  教训内容: ").strip()
                context = input("  场景: ").strip()
                if lesson:
                    evo.save_lesson({"lesson": lesson, "context": context, "fix": "manual"})
                    print(f"  {C['green']}✅ 已记住{C['r']}\n")
                continue

            elif cmd == "/evolve":
                print(f"\n  {C['b']}🧬 进化引擎{C['r']}\n")
                print(f"  [1] 检查能力缺口")
                print(f"  [2] 创建新工具")
                print(f"  [3] 查看进化任务")
                ch = input(f"  选择: ").strip()
                if ch == "2":
                    name = input("  工具名: ").strip()
                    desc = input("  描述: ").strip()
                    print(f"  {C['yellow']}输入 Python 函数体（不含 def 行，空行结束）:{C['r']}")
                    lines = []
                    while True:
                        l = input("  ").strip()
                        if not l and lines:
                            break
                        if l:
                            lines.append(l)
                    code = "\n    ".join(lines)
                    result = evo.create_tool(name, desc, code)
                    print(f"  {result}\n")
                    import importlib
                    importlib.reload(tools)
                continue

            elif cmd == "/optimize":
                try:
                    import pipemind_metabolism as meta
                    print(f"\n  {C['b']}🧬 代谢优化{C['r']}\n")
                    print(f"  {meta.get_system_health()}")
                    r = meta.auto_cleanup(force=True)
                    print(f"  🧹 清理: {r['deleted_files']} 文件, {r['freed_bytes']/1024:.0f}KB")
                    print()
                    print(meta.perf_report())
                    print()
                except Exception as e:
                    print(f"  ❌ {e}")
                continue

            elif cmd == "/precision":
                try:
                    import pipemind_precision as pr
                    print(f"\n  {C['b']}🎯 精准执行{C['r']}\n")
                    print(f"  {pr.accuracy_report()}")
                    print()
                except Exception as e:
                    print(f"  ❌ {e}")
                continue

            elif cmd == "/history":
                if not HAS_SESSION:
                    print("  ⚠ 会话系统未加载")
                    continue
                q = input(f"  搜索关键词: ").strip()
                if q:
                    results = pmsession.search_history(q)
                    print(f"\n  🔍 找到 {len(results)} 条:\n")
                    for r in results[:5]:
                        print(f"  [{r['session_id'][:12]}]\n  {r['content'][:100]}\n")
                continue

            elif cmd == "/sessions":
                if not HAS_SESSION:
                    print("  ⚠ 会话系统未加载")
                    continue
                sessions = pmsession.get_recent_sessions()
                print(f"\n  📋 最近 {len(sessions)} 个会话:\n")
                for s in sessions:
                    print(f"  {s['session_id'][:16]} | {s['messages']}条 | {s['title'][:40]}")
                print()
                continue

            elif cmd == "/providers":
                if not HAS_PROVIDER:
                    print("  ⚠ Provider 系统未加载")
                    continue
                providers = provider.load_providers()
                print(f"\n  📡 Provider 列表:\n")
                for i, p in enumerate(providers):
                    status = "🟢" if p.get("enabled", True) and p.get("api_key") else "🔴"
                    print(f"  {status} [{i}] {p.get('name','?')} ({p.get('model','?')})")
                print()
                ch = input(f"  切换默认输入编号, 空=返回: ").strip()
                if ch.isdigit():
                    import pipemind_provider as pm
                    idx = int(ch)
                    if 0 <= idx < len(providers):
                        pm.save_providers(providers)
                        # 把选中的移到第一位
                        sel = providers.pop(idx)
                        providers.insert(0, sel)
                        pm.save_providers(providers)
                        print(f"  ✅ 已切换至: {sel['name']}")
                continue

            elif cmd == "/context":
                if HAS_COMPRESS:
                    stats = compress.context_stats(agent.messages)
                    print(f"\n{compress.format_stats(stats)}")
                else:
                    print(f"\n  📊 {len(agent.messages)} 条消息")
                continue

            elif cmd == "/reload":
                try:
                    import pipemind_skills as pmsk
                    count = pmsk.reload()
                    print(f"  ✅ 热加载完成: {count} 个技能")
                except Exception as e:
                    print(f"  ❌ {e}")
                continue

            elif cmd == "/help":
                print(f"\n  {C['b']}命令:{C['r']}")
                for k, v in commands.items():
                    print(f"  {C['green']}{k:<12s}{C['r']} {v}")
                print()
                continue

            # 正常对话
            t0 = time.time()
            response = agent.chat(q)
            elapsed = time.time() - t0
            if response:
                print(f"  {C['gray']}({elapsed:.1f}s){C['r']}\n")

    except KeyboardInterrupt:
        print(f"\n  {C['yellow']}👋{C['r']}")

    agent.save()


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="PipeMind — Windows AI Lifeform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
子命令:
  doctor     系统诊断 — 检查所有子系统状态
  ps         查看运行中的后台线程
  log        查看最近日志
  status     生命体征摘要

例子:
  pipemind doctor             运行完整诊断
  pipemind ps                 查看后台线程
  pipemind log --level error  只看错误日志
  pipemind status             系统状态
  pipemind --daemon           启动守护进程
  pipemind --tray             启动托盘
"""
    )
    parser.add_argument("query", nargs="*")
    parser.add_argument("--setup", action="store_true", help="首次设置")
    parser.add_argument("--status", action="store_true", help="生命体征")
    parser.add_argument("--daemon", action="store_true", help="后台守护进程模式")
    parser.add_argument("--tray", action="store_true", help="系统托盘模式")
    parser.add_argument("--stop", action="store_true", help="停止守护进程")
    parser.add_argument("--port", type=int, default=9090, help="Web 控制台端口")
    args = parser.parse_args()

    # ── 子命令检测 ──
    first_arg = args.query[0] if args.query else ""

    # ── doctor 子命令 ──
    if first_arg == "doctor":
        try:
            import pipemind_doctor
            result = pipemind_doctor.run_diagnostics()
            print(result)
        except ImportError:
            print("❌ pipemind_doctor 模块未找到")
        return

    # ── ps 子命令 ──
    if first_arg == "ps":
        try:
            import pipemind_daemon as daemon
            if daemon.is_running():
                print("  ✅ 守护进程运行中")
            else:
                print("  ❌ 守护进程未运行")
            try:
                from pipemind_core import list_modules
                for m in list_modules():
                    icon = {"running": "🟢", "error": "🔴", "registered": "⚪"}.get(m["status"], "⚪")
                    print(f"  {icon} {m['name']} ({m['status']})")
            except:
                pass
        except:
            print("❌ 无法获取进程信息")
        return

    # ── log 子命令 ──
    if first_arg == "log":
        try:
            from pipemind_core import get_recent_logs
            level = args.query[1] if len(args.query) > 1 and args.query[1] in ("error", "warn", "info", "debug") else None
            logs = get_recent_logs(limit=30, level=level)
            for l in logs[-20:]:
                icon = {"error": "❌", "warn": "⚠", "info": "·", "debug": "🔍"}.get(l["level"], "·")
                print(f"  {icon} [{l['module']}] {l['message'][:80]}")
        except:
            print("❌ 无法读取日志")
        return

    # ── 守护进程模式 ──
    if args.daemon:
        import pipemind_daemon as daemon
        daemon.run_server(port=args.port)
        return

    # ── 托盘模式 ──
    if args.tray:
        import pipemind_tray as tray
        tray.run_tray(port=args.port)
        return

    # ── 停止守护进程 ──
    if args.stop:
        import pipemind_daemon as daemon
        ok, msg = daemon.stop_daemon()
        print(f"  {'✅' if ok else '⚠'} {msg}")
        return

    if args.setup:
        print(f"\n  {C['b']}首次设置...{C['r']}\n")
        cfg = config.load()
        key = input(f"  API Key: ").strip()
        if key:
            cfg["model"]["api_key"] = key
            config.save(cfg)
            print(f"  {C['green']}✅ 已保存{C['r']}")
        return

    if args.status:
        print(evo.status_report())
        return

    if not config.get_model_info().get("api_key"):
        print(f"\n  {C['yellow']}⚠ 首次使用请运行: pipemind.py --setup{C['r']}\n")
        return

    if args.query:
        agent = PipeMind()
        q = " ".join(args.query)
        print(f"\n  🧑 {q}\n")
        r = agent.chat(q)
        print(f"  🤖 {r}\n")
        agent.save()
        return

    run_interactive()


if __name__ == "__main__":
    main()
