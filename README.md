# 🧠 PipeMind — Windows AI Lifeform

> Born on Windows. Not a tool. Alive.

PipeMind is a native Windows AI Agent with persistent session memory, multi-provider auto-failover, context compression, skill system, sub-agent delegation, backup self-healing, and a dream reflection system.

**No WSL. No Docker. No heavy frameworks.** Double-click and run.

---

## Quick Start

```cmd
# 1. Set up your API key
python pipemind.py --setup

# 2. Start interactive mode
python pipemind.py
```

That's it.

## Capabilities

| Feature | Description |
|---------|-------------|
| 🧠 Persistent Sessions | SQLite storage, cross-session memory. `/history` search, `/sessions` list |
| 🔄 Multi-Provider | DeepSeek / OpenAI / any OpenAI-compatible API. Auto-failover on error |
| 📦 Context Compression | Auto-compress long conversations, prevents token overflow |
| 📚 Skill System | 13 skills with auto-injected system prompts. Each skill has a Pitfalls section |
| 👥 Sub-Agent Delegation | Complex tasks auto-decomposed into parallel sub-tasks |
| 🩹 Backup & Self-Heal | File integrity baseline + snapshot backup + auto-restore |
| 🌙 Dream System | Light→REM→Deep three-phase reflection + time-limited nudge reminders |
| 🔧 68 Tools | File, terminal, web, registry, services, processes, clipboard, notifications… |
| 🖼️ Vision & Voice | Screenshot analysis, text-to-speech |
| 📖 Diary & Evolution | Auto-logging, self-extension, pattern absorption |

## Commands

```
/exit       exit         /clear     clear context
/save       save session /tools     list tools
/skills     list skills  /status    vital signs
/evolve     manual evolve /learn    record a lesson
/soul       view soul    /history   search history
/sessions   recent sessions  /providers  switch API provider
/context    context usage /help      help
```

## Skills (13)

Each skill includes usage instructions and a `## Pitfalls` section (lessons learned from experience).

```
pipemind-backup       Backup & restore
pipemind-coding       Coding conventions (Windows Python)
pipemind-creative     Creative thinking & problem solving
pipemind-dream-guide  Dream system guide
pipemind-evolution    Evolution engine
pipemind-helper       General helper
pipemind-memory-guide Memory system guide
pipemind-network      Network diagnostics
pipemind-process      Process management
pipemind-security-guide  File integrity & security
pipemind-self-test    Self diagnostics
pipemind-system       Windows system management
pipemind-windows-deep Windows deep integration
```

## Standalone Tools

```cmd
python pipemind_dream.py               # Run full dream cycle
python pipemind_dream.py --nudge       # View active reminders
python pipemind_backup.py --backup      # Create snapshot
python pipemind_backup.py --heal        # Auto-heal tampered files
python pipemind_backup.py --check       # Check file integrity
python pipemind_session.py --sessions   # List recent sessions
python pipemind_session.py --search <q> # Search conversation history
python pipemind_provider.py --test      # Test all configured providers
python pipemind_delegate.py --task <desc>  # Submit a sub-task
python pipemind_compress.py --test      # Test compression
```

## File Structure

```
pipemind/
├── pipemind.py                  # Core engine
├── pipemind_brain.py            # Cerebral cortex
├── pipemind_session.py          # Session persistence
├── pipemind_provider.py         # Multi-provider engine
├── pipemind_compress.py         # Context compression
├── pipemind_delegate.py         # Sub-agent system
├── pipemind_dream.py            # Dream system
├── pipemind_backup.py           # Backup & self-heal
├── pipemind_tools.py            # 68 tools
├── pipemind_*.py                # 22 modules total
├── SOUL.md                      # Soul core
├── config.json                  # Local config (not tracked)
└── skills/                      # 13 skills
    ├── pipemind-self-test/
    ├── pipemind-backup/
    ├── pipemind-coding/
    └── ...
```

## Design Philosophy

**PipeMind is not another framework. It's a native AI you build yourself.**

- Windows native — no WSL, no Docker
- Lightweight — 22 modules, ~4500 lines total
- Every line is readable, modifiable, controllable
- Capabilities grow organically, not stacked

## Tech Stack

- **Language:** Python 3 (no external framework dependencies)
- **Storage:** SQLite (sessions) + JSON files (memory, dreams, backups)
- **LLM API:** OpenAI-compatible (DeepSeek, OpenAI, or any)
- **Platform:** Windows only (uses native Win32 APIs)

## License

MIT
