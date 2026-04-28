---
name: pipemind-system
description: "PipeMind 系统管理技能 — Windows 系统信息、服务、启动项"
version: 1.0.0
author: 弈辛
---

# PipeMind 系统管理技能

## 用法
通过内置工具调用，无需额外命令。

## 可用工具
- `windows_info` — 系统信息（版本、CPU、内存、磁盘）
- `service_list` — 列出 Windows 服务
- `service_action start/stop/restart <name>` — 管理服务
- `startup_list` — 查看开机启动项

## Pitfalls
- **修改服务前先查依赖** — stop 服务前确认没有其他服务依赖它
- **开机启动项修改需要管理员权限** — 工具会返回权限错误
- **系统信息中的内存值是物理内存** — 不包含虚拟内存
