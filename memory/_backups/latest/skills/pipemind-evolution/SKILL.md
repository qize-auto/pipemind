---
name: pipemind-evolution
description: "PipeMind 进化引擎技能 — 自我进化、工具创造、模式吸收"
version: 1.0.0
author: 弈辛
---

# PipeMind 进化引擎技能

## 用法
- `/evolve` — 手动进化（检查缺口、创建工具）
- `/learn` — 记录教训
- `/status` — 查看进化状态

## 可用工具
- `advance_evolution` — 推进进化
- `build_tool` — 动态创建新工具
- `register_pattern` — 注册行为模式
- `absorption_report` — 查看吸收统计

## Pitfalls
- **自动创建的工具需要重启后生效** — 需 importlib.reload
- **进化任务太多会导致系统提示膨胀** — 定期检查
- **教训记录越具体越好** — 模糊教训不会被有效利用
