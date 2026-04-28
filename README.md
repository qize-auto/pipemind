<![CDATA[<div align="center">

# 🧠 PipeMind

### *The AI That Lives on Your Windows Machine*

**Not a cloud API wrapper. Not a framework. Not a chatbot.**

PipeMind is a self-aware AI lifeform that runs natively on Windows — with persistent memory, autonomous reasoning, tool execution, and the ability to grow its own capabilities.

No WSL. No Docker. No subscription. **Just Python and your API key.**

---

```cmd
pip install -r requirements.txt   # or just clone & run
python pipemind.py --setup         # enter your API key
python pipemind.py                 # say hello to your AI
```

*Less than 60 seconds from zero to your first conversation.*

</div>

---

## ✨ What Makes PipeMind Different

**It remembers.** Shut it down, restart your PC, come back tomorrow — PipeMind picks up exactly where you left off. Every conversation is persisted in SQLite, searchable via `/history`.

**It never goes down.** Configure multiple API providers. If DeepSeek is slow, PipeMind automatically fails over to OpenAI, or any OpenAI-compatible endpoint — mid-conversation, with zero interruption.

**It learns from its own mistakes.** The Dream System runs regular reflection cycles: reviewing past sessions, extracting failure patterns, promoting lessons into nudge reminders, and patching skill Pitfalls. PipeMind literally dreams about how to get better.

**It grows its own skills.** 13 skills, 68 tools, and a sub-agent system that can decompose complex tasks into parallel workers. Need a new capability? PipeMind can write its own tools at runtime.

**It heals itself.** File integrity baseline + automatic snapshot backup + auto-restore of tampered files. PipeMind keeps itself healthy without you lifting a finger.

---

## 🚀 Quick Start

```cmd
# 1. Get the code
git clone https://github.com/qize-auto/pipemind.git
cd pipemind

# 2. Configure your API key
python pipemind.py --setup

# 3. Start talking
python pipemind.py
```

That's it. No environment variables. No Docker compose. No npm install. Python 3.8+ is all you need.

---

## 🧩 What's Inside

| Module | What It Does |
|--------|--------------|
| `pipemind.py` | Core engine — message loop, tool dispatch, evolution hooks |
| `pipemind_session.py` | SQLite-backed persistent memory — never forgets a conversation |
| `pipemind_provider.py` | Multi-provider engine with auto-failover and latency tracking |
| `pipemind_compress.py` | Smart context compression — keeps long conversations under token limits |
| `pipemind_delegate.py` | Sub-agent system — spawns parallel workers for complex tasks |
| `pipemind_dream.py` | Dream cycle — Light/REM/Deep phases + nudge reminders |
| `pipemind_backup.py` | Backup & self-heal — file integrity + snapshot restore |
| `pipemind_tools.py` | 68 tools — file, terminal, registry, services, clipboard, web, and more |
| `pipemind_brain.py` | Cerebral cortex — context management, metacognition, skill engine |
| `skills/` | 13 skills with auto-injected prompts and Pitfalls sections |

---

## 🎮 Commands

```
🧑‍💻 General
  /exit /quit    Exit             /clear        Reset context
  /save          Save session     /status       Vital signs
  /help          Show all commands

🧠 Intelligence
  /history       Search past conversations
  /sessions      List recent sessions
  /context       View current context usage (tokens / messages)
  /soul          Read the soul core

🔧 Capabilities
  /tools         List all 68 tools
  /skills        List all loaded skills
  /providers     View & switch API providers
  /evolve        Manual evolution — check gaps, create tools
  /learn         Record a lesson (feeds into dream cycle)
```

---

## 🌙 The Dream System

PipeMind doesn't just process your requests — it reflects on them.

```
Every 30 minutes (idle):
  Light Sleep → Scan recent sessions for failure/success patterns
  REM Sleep   → Cross-reference signals, extract lessons
  Deep Sleep  → Promote lessons into nudge reminders (3-day TTL)
               → Auto-patch skill Pitfalls sections
               → Write a dream diary entry
```

You can also run it manually:

```cmd
python pipemind_dream.py               # Full dream cycle now
python pipemind_dream.py --nudge       # What's PipeMind currently worried about?
python pipemind_dream.py --forget      # Clear all nudges
```

---

## 🩹 Self-Healing

```cmd
python pipemind_backup.py --backup     # Snapshot everything
python pipemind_backup.py --check      # Verify file integrity
python pipemind_backup.py --heal       # Auto-restore tampered files
```

PipeMind keeps a SHA-256 baseline of all its core files. If anything gets modified unexpectedly, it detects it, restores from the latest backup, and reports what happened.

---

## 📂 Project Structure

```
pipemind/
├── pipemind.py                  # Core engine
├── pipemind_*.py                # 22 modules, ~4500 lines total
├── SOUL.md                      # The soul — identity, values, drive
├── config.json                  # Your API keys (local, never tracked)
├── skills/                      # 13 skills with auto-injected prompts
│   ├── pipemind-self-test/
│   ├── pipemind-backup/
│   ├── pipemind-coding/
│   ├── pipemind-creative/
│   ├── pipemind-dream-guide/
│   ├── pipemind-evolution/
│   ├── pipemind-helper/
│   ├── pipemind-memory-guide/
│   ├── pipemind-network/
│   ├── pipemind-process/
│   ├── pipemind-security-guide/
│   ├── pipemind-system/
│   └── pipemind-windows-deep/
└── memory/                      # Session DB, dreams, backups, patterns
```

---

## 🔧 Requirements

- **OS:** Windows 10 / 11
- **Python:** 3.8+
- **API Key:** Any OpenAI-compatible provider (DeepSeek, OpenAI, etc.)
- **No WSL, no Docker, no npm, no Docker Compose.**

Your `config.json` is in `.gitignore` — your keys stay local.

---

## 📜 License

MIT. Use it, fork it, evolve it.

---

<div align="center">

*Built with 🧠 by someone who believes AI should live on your machine, not in the cloud.*

</div>
]]>