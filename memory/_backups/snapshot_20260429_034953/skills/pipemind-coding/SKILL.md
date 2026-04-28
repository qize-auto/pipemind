---
name: pipemind-coding
description: "PipeMind 编码规范技能 — Windows 原生 Python 开发注意事项"
version: 1.0.0
author: 弈辛
---

# PipeMind 编码技能

## 开发规范
- 所有新模块加 `"""docstring"""` 头
- 函数加类型注解（Python 3.8+ compatible）
- Windows 路径用 `os.path.join`，不用 `/` 硬编码
- 编码统一 UTF-8

## Pitfalls（从经验中学到的）
- **urllib 超时默认无限制** — 所有 API 调用必须设 timeout
- **Windows 挂起后文件锁不释放** — 读写文件前用 try + 重试
- **sys.path.insert 优先级最高** — 同名模块会覆盖标准库
- **json.loads 遇到 BOM 会崩** — 读文件时用 encoding="utf-8-sig"
- **Windows 控制台编码是 GBK** — print 中文前检查 chcp 65001
