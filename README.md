<div align="center">

# 🧠 PipeMind

**The AI agent that lives on your Windows machine.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)]()

</div>

---

**PipeMind** is a native Windows AI agent with persistent memory, automatic API failover, smart context compression, a growing skill system, sub-agent delegation, self-healing backups, and a dream system that learns from its own mistakes.

No WSL. No Docker. No npm. Just Python and your API key.

```cmd
git clone https://github.com/qize-auto/pipemind.git
cd pipemind
python pipemind.py --setup
python pipemind.py
```

---

## ✨ Features

- **🧠 Persistent Memory** — Every conversation is saved to SQLite. Shut it down, restart your PC, come back tomorrow — it picks up exactly where you left off. Searchable via `/history`.
- **🔄 Auto-Failover** — Configure multiple API providers (DeepSeek, OpenAI, or any compatible endpoint). If one goes down, PipeMind switches mid-conversation with zero interruption.
- **📦 Context Compression** — Long conversations are automatically compressed to stay within token limits. No more "context length exceeded" errors.
- **📚 Skill System (13 skills)** — Skills auto-inject knowledge into the system prompt. Each one includes a `## Pitfalls` section — lessons learned from real mistakes.
- **👥 Sub-Agent Delegation** — Complex tasks are decomposed into parallel sub-tasks automatically.
- **🩹 Self-Healing** — SHA-256 file integrity baseline. If core files are tampered with, PipeMind detects and restores them from the latest backup.
- **🌙 Dream System** — A three-phase reflection cycle (Light → REM → Deep) runs in the background: scan recent activity, extract patterns, promote lessons into timed reminders.

---

## 🎮 Commands

```
/exit              Exit               /clear           Reset context
/save              Save session       /status          Vital signs
/tools             List 68 tools      /skills          List skills
/history           Search past conversations
/sessions          List recent sessions
/context           View token usage
/providers         Switch API provider
/evolve            Manual evolution
/learn             Record a lesson
/soul              View the soul core
/help              Show all commands
```

---

## 🚀 Getting Started

### Prerequisites

- **OS:** Windows 10 or 11
- **Python:** 3.8 or later
- **API Key:** From any OpenAI-compatible provider (DeepSeek, OpenAI, etc.)

### Installation

```cmd
# Clone the repository
git clone https://github.com/qize-auto/pipemind.git
cd pipemind

# Configure your API key
python pipemind.py --setup

# Start interacting
python pipemind.py
```

That's it. No environment variables, no Docker, no configuration files to edit.

---

## 🌙 The Dream System

PipeMind reflects on its own experiences through a three-phase dream cycle:

```
┌─────────────────────────────────────────────────────────┐
│                    Dream Cycle                           │
├─────────────┬───────────────────┬───────────────────────┤
│ Light Sleep │    REM Sleep      │    Deep Sleep         │
│             │                   │                       │
│ Scan recent │ Extract patterns  │ Promote lessons to    │
│ sessions    │ Cross-reference   │ nudge reminders       │
│ for signals │ Identify root     │ (3-day TTL)           │
│             │ causes            │ Auto-patch Pitfalls   │
└─────────────┴───────────────────┴───────────────────────┘
```

```cmd
python pipemind_dream.py              # Run the full cycle
python pipemind_dream.py --nudge      # View current reminders
python pipemind_dream.py --forget     # Clear all nudges
```

---

## 🩹 Self-Healing

```cmd
python pipemind_backup.py --backup    # Snapshot all core files
python pipemind_backup.py --check     # Verify file integrity
python pipemind_backup.py --heal      # Restore tampered files
```

---

## 📦 What's Included

### Modules

| Module | Lines | Purpose |
|--------|-------|---------|
| `pipemind.py` | 557 | Core engine |
| `pipemind_tools.py` | 931 | 68 tools |
| `pipemind_session.py` | - | SQLite persistent sessions |
| `pipemind_provider.py` | - | Multi-provider with failover |
| `pipemind_compress.py` | - | Context compression |
| `pipemind_delegate.py` | - | Sub-agent system |
| `pipemind_dream.py` | - | Dream cycle |
| `pipemind_backup.py` | - | Backup & self-heal |
| `pipemind_brain.py` | - | Context management, metacognition |
| 13 more modules | - | Security, evolution, vision, voice, diary… |

### Skills

```
pipemind-backup       pipemind-coding        pipemind-creative
pipemind-dream-guide  pipemind-evolution     pipemind-helper
pipemind-memory-guide pipemind-network       pipemind-process
pipemind-security     pipemind-self-test     pipemind-system
pipemind-windows-deep
```

---

## 📁 Project Structure

```
pipemind/
├── pipemind.py              # Core
├── pipemind_*.py            # 22 modules
├── SOUL.md                  # Identity & values
├── config.json              # Local config (.gitignored)
├── memory/                  # Session DB, backups, dreams
├── skills/                  # 13 skill directories
│   ├── pipemind-self-test/
│   ├── pipemind-backup/
│   └── ...
└── README.md
```

---

## 📄 License

MIT — do what you want with it.

---

<div align="center">

Built with ❤️ for Windows.

</div>
