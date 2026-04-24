# 🔧 PipeMind — AI Workflow Engine / AI 工作流引擎

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Pipe**line + **Mind** = AI workflow engine. Drag, connect, and run search → LLM → output pipelines — like building with Lego blocks.
>
> **流水线 + 思维 = AI 工作流引擎**。拖拽式构建搜索 → LLM → 输出流水线，像搭乐高一样组合 AI 能力。

---

## ✨ Features / 功能

| English | 中文 |
|---------|------|
| 🖱️ Drag-and-drop workflow builder (React Flow) | 🖱️ 可视化拖拽构建工作流（React Flow） |
| 🔍 Real web search via local Auth Gateway | 🔍 真实联网搜索（本地 Auth Gateway 代理） |
| 🧠 LLM processing (DeepSeek / OpenAI-compatible) | 🧠 LLM 文本处理（DeepSeek / 兼容 OpenAI） |
| 📤 Formatted output (Markdown / text / JSON) | 📤 格式化输出（Markdown / 文本 / JSON） |
| ⚡ DAG engine with topological execution | ⚡ DAG 引擎，拓扑排序并行执行 |
| 🔌 Extensible node system | 🔌 可扩展节点系统，可自定义节点 |

## 🏗 Architecture / 架构

```
User Input → 🔍 Search Node → 🧠 LLM Node → 📤 Output Node
                     │                │              │
                     ▼                ▼              ▼
              Auth Gateway (19000)  DeepSeek API    Markdown
              └── prosearch proxy   └── chat api    └── formatted
```

### Node Types / 节点类型

| Node | Type | Description / 说明 |
|------|------|-------------------|
| 🔍 | `search` | Web search with freshness filter / 联网搜索，支持时效过滤 |
| 🧠 | `llm` | LLM processing with custom prompt / 自定义提示词的 AI 处理 |
| 📤 | `output` | Format and display results / 格式化展示结果 |

---

## 🚀 Quick Start / 快速开始

### Prerequisites / 前置要求

- **Node.js** 22+
- **npm**
- **OpenClaw** (for Auth Gateway search proxy — only if using the search node)

### 1. Backend / 后端

```bash
cd backend
cp .env.example .env    # Edit with your API keys
npm install
npm start               # → http://localhost:3001
```

**Environment Variables / 环境变量**

| Variable / 变量 | Required | Default / 默认值 | Description / 说明 |
|----------------|----------|-------------------|-------------------|
| `PIPEMIND_LLM_KEY` | ✅ | — | OpenAI-compatible API key |
| `PIPEMIND_LLM_BASE` | ❌ | `https://api.deepseek.com` | API base URL |
| `PIPEMIND_AUTH_TOKEN` | ❌ | built-in token | Auth Gateway token for search |

### 2. Frontend (optional / 可选) / 前端

```bash
cd frontend
npm install
npm run dev             # → http://localhost:5173
```

### 3. Test the API / 测试 API

```bash
# Health check / 健康检查
curl http://localhost:3001/api/health

# Run a search-only workflow / 运行纯搜索工作流
curl -X POST http://localhost:3001/api/run \
  -H "Content-Type: application/json" \
  -d '{"nodes":[{"id":"n1","type":"search","data":{"query":"PipeMind workflow","count":2}}],"edges":[]}'

# Run a full pipeline / 运行全链路
curl -X POST http://localhost:3001/api/run \
  -H "Content-Type: application/json" \
  -d '{
    "nodes": [
      {"id":"n1","type":"search","data":{"query":"your topic","count":3}},
      {"id":"n2","type":"llm","data":{"prompt":"Summarize in Chinese"}},
      {"id":"n3","type":"output","data":{"format":"markdown"}}
    ],
    "edges": [
      {"id":"e1","source":"n1","target":"n2"},
      {"id":"e2","source":"n2","target":"n3"}
    ]
  }'
```

---

## 📋 Workflow JSON Format / 工作流 JSON 格式

```json
{
  "nodes": [
    {
      "id": "n1",
      "type": "search",
      "data": {
        "query": "search topic",
        "count": 3,
        "freshness": "week"   // day | week | month
      }
    },
    {
      "id": "n2",
      "type": "llm",
      "data": {
        "prompt": "You are a tutor. Summarize the results.",
        "model": "deepseek-chat"
      }
    },
    {
      "id": "n3",
      "type": "output",
      "data": {
        "format": "markdown"  // text | markdown | json
      }
    }
  ],
  "edges": [
    { "id": "e1", "source": "n1", "target": "n2" },
    { "id": "e2", "source": "n2", "target": "n3" }
  ]
}
```

---

## 🧩 Node Reference / 节点参考

### 🔍 Search Node

| Param / 参数 | Type / 类型 | Default / 默认值 | Description / 说明 |
|-------------|-------------|-------------------|-------------------|
| `query` | string | `"默认搜索"` | Search keyword / 搜索关键词 |
| `count` | number | `3` | Max results (1–10) / 最大结果数 |
| `freshness` | string | `"week"` | Time filter: `day` / `week` / `month` / 时效过滤 |

### 🧠 LLM Node

| Param / 参数 | Type / 类型 | Default / 默认值 | Description / 说明 |
|-------------|-------------|-------------------|-------------------|
| `prompt` | string | `"请总结以下内容"` | System prompt / 系统提示词 |
| `model` | string | `"deepseek-chat"` | Model name / 模型名称 |

### 📤 Output Node

| Param / 参数 | Type / 类型 | Default / 默认值 | Description / 说明 |
|-------------|-------------|-------------------|-------------------|
| `format` | string | `"text"` | `text` / `markdown` / `json` 输出格式 |

---

## 🧪 Testing / 测试

```bash
# Search node / 搜索节点测试
curl http://localhost:3001/api/run \
  -X POST -H "Content-Type: application/json" \
  -d '{"nodes":[{"id":"n1","type":"search","data":{"query":"AI workflow","count":2}}],"edges":[]}'

# LLM only (standalone mode, no search needed) / 纯 LLM 模式
curl http://localhost:3001/api/run \
  -X POST -H "Content-Type: application/json" \
  -d '{"nodes":[{"id":"n1","type":"llm","data":{"prompt":"教我 Python 装饰器"}},{"id":"n2","type":"output","data":{}}],"edges":[{"id":"e1","source":"n1","target":"n2"}]}'
```

---

## 🛠️ Development / 开发

### Project Structure / 项目结构

```
pipemind/
├── backend/
│   ├── src/
│   │   ├── index.js          # Express server + route setup
│   │   ├── engine.js         # DAG workflow execution engine
│   │   └── nodes/            # Node implementations
│   │       ├── search.js     # 🔍 Search node
│   │       ├── llm.js        # 🧠 LLM node
│   │       └── output.js     # 📤 Output node
│   ├── .env.example
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main app with React Flow canvas
│   │   ├── nodes/            # Custom React Flow components
│   │   └── api/              # API client
│   └── package.json
├── README.md
└── .gitignore
```

### DAG Engine / 引擎设计

The engine executes nodes in topological order based on edge dependencies. Each node is an async function receiving `(data, inputs)` where:
- `data` — static config from the workflow definition
- `inputs` — outputs from upstream connected nodes

引擎按拓扑顺序执行节点，每个节点是 `async (data, inputs)` 函数：
- `data` — 工作流定义的静态配置
- `inputs` — 上游节点的输出

### Adding a New Node / 添加新节点

1. Create a file in `backend/src/nodes/`, e.g. `translate.js`
2. Export an async function matching the signature `functionName(data, inputs)`
3. Register it in `backend/src/index.js`:

```javascript
const nodeHandlers = {
  search: nodes.search.search,
  llm: nodes.llm.llm,
  output: nodes.output.output,
  translate: nodes.translate.translate,  // your new node
};
```

---

## 📄 License / 许可证

MIT

---

## 🤝 Contributing / 贡献

PRs welcome! For major changes, open an issue first to discuss what you'd like to change.

欢迎提交 PR！重大变更请先提 issue 讨论。
