# 🧠 PipeMind — Windows AI Lifeform

> 一个诞生于 Windows 的 AI 生命体。不是工具，是活的。

PipeMind 是一个原生 Windows AI Agent。它拥有完整的会话记忆、多 API 自动降级、上下文压缩、技能体系、子代理分工、备份自愈和梦境反思系统。

**不需要 WSL，不需要 Docker，不需要复杂的框架。** 双击即跑。

---

## 快速开始

```cmd
# 1. 配置 API Key
python pipemind.py --setup

# 2. 启动交互模式
python pipemind.py
```

就这么简单。

## 内置能力

| 能力 | 说明 |
|------|------|
| 🧠 会话持久化 | SQLite 存储，跨会话不丢失。`/history` 搜索，`/sessions` 列表 |
| 🔄 多 Provider | DeepSeek / OpenAI / 任意兼容 API。主线路挂了自动切备用 |
| 📦 上下文压缩 | 长对话超阈值自动压缩，防止 token 超限 |
| 📚 技能体系 | 13 个技能，自动注入系统提示。每个技能含 Pitfalls 节 |
| 👥 子代理分工 | 复杂任务自动分解为并行子任务 |
| 🩹 备份自愈 | 文件完整性基线 + 快照备份 + 自动恢复 |
| 🌙 梦境系统 | Light→REM→Deep 三阶段反思 + nudge 短期提醒 |
| 🔧 68 个工具 | 文件、终端、网络、注册表、服务、进程、剪贴板、通知… |
| 🖼️ 视觉 & 语音 | 截图分析、文字朗读 |
| 📖 日记 & 进化 | 自动记录 + 自我扩展 + 模式吸收 |

## 内置命令

```
/exit       退出        /clear     清空对话
/save       保存        /tools     工具列表
/skills     技能列表    /status    生命体征
/evolve     手动进化    /learn     记录教训
/soul       查看灵魂    /history   搜索历史
/sessions   最近会话    /providers 切换 API Provider
/context    上下文用量   /help      帮助
```

## 技能体系（13 个）

每个技能包含用法说明 + `## Pitfalls`（从经验中总结的注意事项）。

```
pipemind-backup       备份恢复
pipemind-coding       编码规范
pipemind-creative     创造思维
pipemind-dream-guide  梦境系统指南
pipemind-evolution    进化引擎
pipemind-helper       通用辅助
pipemind-memory-guide 记忆系统指南
pipemind-network      网络诊断
pipemind-process      进程管理
pipemind-security-guide 安全完整性
pipemind-self-test    自检
pipemind-system       系统管理
pipemind-windows-deep Windows 深度集成
```

## 独立工具

```cmd
python pipemind_dream.py            # 做梦
python pipemind_dream.py --nudge    # 查看提醒
python pipemind_backup.py --backup   # 创建快照
python pipemind_backup.py --heal     # 自愈
python pipemind_backup.py --check    # 检查完整性
python pipemind_session.py --sessions  # 会话列表
python pipemind_session.py --search <q>  # 搜索历史
python pipemind_provider.py --test    # 测试所有 Provider
python pipemind_delegate.py --task <描述>  # 提交子任务
python pipemind_compress.py --test    # 测试压缩
```

## 文件结构

```
pipemind/
├── pipemind.py                  # 核心引擎
├── pipemind_brain.py            # 大脑皮层
├── pipemind_session.py          # 会话持久化
├── pipemind_provider.py         # 多 Provider 引擎
├── pipemind_compress.py         # 上下文压缩
├── pipemind_delegate.py         # 子代理系统
├── pipemind_dream.py            # 梦境系统
├── pipemind_backup.py           # 备份自愈
├── pipemind_tools.py            # 68 个工具
├── pipemind_*.py                # 22 个模块
├── SOUL.md                      # 灵魂核心
├── config.json                  # 配置（本地）
└── skills/                      # 13 个技能
    ├── pipemind-self-test/
    ├── pipemind-backup/
    ├── pipemind-coding/
    └── ...
```

## 设计哲学

**PipeMind 不是另一个框架。它是你亲手造的原生 AI。**

- Windows 原生，不依赖 WSL 或 Docker
- 轻量自主，22 个模块共 ~4500 行代码
- 每行代码都可读、可改、可控
- 能力不是堆出来的，是长出来的

## 对比

| | PipeMind | Hermes Agent |
|---|----------|-------------|
| 运行环境 | Windows 原生 | WSL Linux |
| 启动速度 | <1 秒 | ~7 秒 |
| 工具数 | 68 | ~30 |
| 技能数 | 13 | 36 |
| 子代理 | ✅ | ✅ |
| 会话持久 | ✅ | ✅ |
| 多 Provider | ✅ 自动降级 | ✅ |
| 上下文压缩 | ✅ | ✅ |
| 备份自愈 | ✅ | ✅ |
| 梦境系统 | ✅ | ✅ |
| Windows API | ✅ 注册表/服务/进程 | ❌ |
| 代码量 | ~4500 行 | 万级 |

## License

MIT
