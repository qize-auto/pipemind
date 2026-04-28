---
name: pipemind-security-guide
description: "PipeMind 安全技能 — 文件完整性、基线、权限"
version: 1.0.0
author: 弈辛
---

# PipeMind 安全技能

## 用法
```cmd
python pipemind_backup.py --check    # 检查完整性
python pipemind_backup.py --heal     # 恢复被篡改文件
python pipemind_backup.py --backup   # 创建快照
```

## 内置安全工具
- `secure_config` — 检查 API Key 是否泄露
- `audit_log` — 查看操作审计日志
- `self_test` — 全面自检

## Pitfalls
- **基线不存在时 --heal 无效** — 必须先 --backup
- **自愈只修被篡改的文件** — 新文件和已删文件只报告
- **安全审计日志不自动清理** — 定期备份
