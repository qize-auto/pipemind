# PipeMind 进化嵌入方案

## 原则
1. 不破坏 PipeMind 现有代码 — 只新增模块，不改核心
2. 复用弈辛已验证的机制 — skills/pitfalls/梦境/nudge
3. Windows 原生兼容 — 不走 WSL

## 嵌入方案

```
pipemind/
├── pipemind_dream.py        ← 新增：梦境系统（从弈辛移植）
├── pipemind_nudge.json      ← 新增：nudge 存储
├── pipemind_backup.py       ← 新增：备份恢复
├── skills/
│   ├── pipemind-helper/     ← 已有
│   ├── pipemind-self-test/  ← 新增：自检技能
│   ├── pipemind-backup/     ← 新增：备份技能
│   └── pipemind-coding/     ← 新增：编码规范技能 + Pitfalls
└── memory/
    ├── .dreams/             ← 新增：梦境存储
    └── .baseline.json       ← 新增：文件完整性基线
```

## 三样具体做什么

### 1. 技能体系 — 移植 3 个核心技能 + Pitfalls
直接写 SKILL.md 到 skills/ 目录，PipeMind 的 brain.py 会自动加载。

### 2. 记忆增强 — 轻量语义搜索 + 梦境反思
写 pipemind_dream.py，PipeMind 在 evolution_cycle 中调用。
不做向量库（太重），用 TF-IDF + 关键词匹配。

### 3. 自愈备份 — Git 基线 + 文件完整性
写 pipemind_backup.py，支持三种模式：
- --check: 检查文件完整
- --heal: 自动修复被篡改的文件
- --backup: 备份到本地存档
