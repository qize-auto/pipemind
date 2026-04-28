---
name: pipemind-windows-deep
description: "PipeMind Windows 深度集成技能 — 注册表、服务、计划任务"
version: 1.0.0
author: 弈辛
---

# PipeMind Windows 深度集成

## 可用工具
- `reg_read <path>` — 读注册表
- `reg_write <path> <value>` — 写注册表
- `service_list` — 服务列表
- `service_action <action> <name>` — 服务操作
- `startup_list` — 启动项
- `windows_info` — 系统信息

## Pitfalls
- **注册表写错系统可能崩** — 修改前先 reg_read 确认
- **服务名不是显示名** — 用 service_list 查实际名称
- **启动项修改需管理员权限** — 以管理员身份运行
