---
name: pipemind-self-test
description: "PipeMind 自检技能 — 健康检查 + 代谢分析 + 精度报告"
version: 1.0.0
author: 弈辛
---

# PipeMind 自检技能

## 用法
```cmd
python pipemind.py /self-test      # 全面自检
python pipemind.py /status         # 生命体征
python pipemind.py /optimize       # 代谢优化
```

## 自检项
- 文件完整性（调用 pipemind_backup.py --check）
- 记忆系统健康（记忆文件数、最新更新时间）
- 技能加载状态
- 工具响应性
- 代谢报告（清理缓存、压缩日志）

## Pitfalls（从经验中学到的）
- **自检发现异常后不修复等于白检** — 自检报错 → 立刻 pipemind_backup.py --heal
- **代谢清理可能误删有用缓存** — 先看报告再确认清理范围
- **精度报告需要真实数据才有意义** — 刚启动时的精度报告是空的
