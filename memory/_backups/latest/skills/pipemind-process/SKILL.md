---
name: pipemind-process
description: "PipeMind 进程管理技能 — 进程列表、监控、清理"
version: 1.0.0
author: 弈辛
---

# PipeMind 进程管理技能

## 用法
通过内置工具调用。

## 可用工具
- `get_process_list <filter>` — 按名称过滤进程
- `run_terminal taskkill /f /im <name>` — 强制终止

## Pitfalls
- **taskkill /f 数据可能丢失** — 确认后再执行
- **系统进程不能被终止** — 返回权限错误属正常
- **Windows 进程名不区分大小写**
