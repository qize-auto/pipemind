---
name: pipemind-dream-guide
description: "PipeMind 梦境系统指南 — 历史反思 + nudge 提醒"
version: 1.0.0
author: 弈辛
---

# PipeMind 梦境系统指南

## 用法
```cmd
python pipemind_dream.py           # 完整做梦
python pipemind_dream.py --nudge   # 查看提醒
python pipemind_dream.py --forget  # 清除 nudge
```

## 什么是 nudge
nudge 是梦境产出的短期提醒，3 天自动过期。

## Pitfalls
- **没有记忆数据时做梦是空的** — 先跑几轮对话再做梦
- **nudge 到期自动消失** — 重要的事到期前处理好
- **梦境不修改系统提示** — 只写文件不改行为
