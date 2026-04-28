---
name: pipemind-memory-guide
description: "PipeMind 记忆系统指南 — 存储、检索、管理"
version: 1.0.0
author: 弈辛
---

# PipeMind 记忆系统指南

## 用法
- `save_memory <key> <content>` — 保存记忆
- `read_memory <key>` — 读取记忆
- `list_memory` — 列出所有记忆
- `delete_memory <key>` — 删除记忆
- `memory_search <query>` — 搜索记忆

## 记忆文件位置
```
memory/_absorbed.json    # 吸收的模式
memory/_patterns.json    # 行为模式
memory/_inventions.json  # 发明记录
memory/_perf_log.json    # 性能日志
memory/_backups/         # 快照备份
memory/.dreams/          # 梦境数据
```

## Pitfalls
- **记忆 key 重复会覆盖** — 保存前先查是否已有
- **搜索是关键词匹配不是语义** — 换关键词可能搜不到
- **备份文件不通过 save_memory 管理** — 用 pipemind_backup.py
