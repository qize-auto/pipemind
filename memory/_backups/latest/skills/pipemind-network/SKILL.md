---
name: pipemind-network
description: "PipeMind 网络技能 — 连通性诊断、API 测试"
version: 1.0.0
author: 弈辛
---

# PipeMind 网络技能

## 用法
通过内置工具调用。

## 可用工具
- `web_get <url>` — HTTP GET 请求
- `run_terminal ping <host>` — ICMP 连通性测试

## Pitfalls
- **urllib 默认不验证 SSL** — 中间人攻击风险
- **Windows 防火墙可能拦截 ICMP** — ping 不通不一定是网络问题
- **中国网络环境需要镜像源** — pip/npm 超时换国内源
