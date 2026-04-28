---
name: pipemind-backup
description: "PipeMind 备份恢复技能 — 快照备份 + 自愈 + 状态监控"
version: 1.0.0
author: 弈辛
---

# PipeMind 备份恢复技能

## 用法
```cmd
python pipemind_backup.py --backup   # 创建快照
python pipemind_backup.py --heal     # 自愈
python pipemind_backup.py --check    # 检查完整性
python pipemind_backup.py --status   # 查看状态
```

## 推荐周期
- 每天：`--check` 一次（检查完整性）
- 每周：`--backup` 一次（快照备份）
- 发现问题：`--heal`（自动恢复）

## Pitfalls（从经验中学到的）
- **基线不存在时 --heal 无效** — 先 --backup 建立基线
- **被篡改的文件没有备份也能恢复** — 如果备份不存在，--heal 只报告不修复
- **快照太多占用空间** — 系统保留最近 10 个，更早的自动删除
- **修改代码后记得 --backup** — 不然下次 --heal 会覆盖你的修改
