import { Handle, Position } from 'reactflow';
import { useState } from 'react';

export function SearchNode({ data, selected }) {
  const [query, setQuery] = useState(data.query || '');

  data.query = query;

  return (
    <div className={`min-w-[220px] rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm shadow-xl ${
      selected ? 'border-cyan-400 ring-2 ring-cyan-400/20' : 'border-cyan-500/30'
    } ${data.executed ? 'ring-2 ring-emerald-400/40' : ''}`}>
      <Handle type="target" position={Position.Left} className="!bg-cyan-400 !w-3 !h-3 !border-2 !border-gray-900" />
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-700/50 bg-cyan-500/10 rounded-t-xl">
        <span>🔍</span>
        <span className="text-sm font-medium text-cyan-300">搜索</span>
      </div>
      <div className="p-3 space-y-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="输入搜索关键词..."
          className="w-full px-2 py-1.5 text-xs bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:border-cyan-500/50"
        />
        <div className="flex gap-2 text-xs text-gray-500">
          <span>时效:</span>
          <select
            value={data.freshness || 'week'}
            onChange={(e) => { data.freshness = e.target.value; }}
            className="bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-300 focus:outline-none"
          >
            <option value="day">24小时</option>
            <option value="week">一周</option>
            <option value="month">一月</option>
          </select>
        </div>
      </div>
      {data.executed && data.result && (
        <div className="px-3 py-1.5 text-xs text-emerald-400 border-t border-gray-700/50 bg-emerald-500/5 rounded-b-xl">
          ✅ {data.result.duration}ms
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-cyan-400 !w-3 !h-3 !border-2 !border-gray-900" />
    </div>
  );
}

export function LLMNode({ data, selected }) {
  const [prompt, setPrompt] = useState(data.prompt || '请总结以下内容的关键信息');

  data.prompt = prompt;

  return (
    <div className={`min-w-[220px] rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm shadow-xl ${
      selected ? 'border-purple-400 ring-2 ring-purple-400/20' : 'border-purple-500/30'
    } ${data.executed ? 'ring-2 ring-emerald-400/40' : ''}`}>
      <Handle type="target" position={Position.Left} className="!bg-purple-400 !w-3 !h-3 !border-2 !border-gray-900" />
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-700/50 bg-purple-500/10 rounded-t-xl">
        <span>🧠</span>
        <span className="text-sm font-medium text-purple-300">LLM 处理</span>
      </div>
      <div className="p-3 space-y-2">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="输入处理指令..."
          rows={3}
          className="w-full px-2 py-1.5 text-xs bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500/50 resize-none"
        />
        <div className="flex gap-2 text-xs text-gray-500">
          <span>模型:</span>
          <input
            defaultValue={data.model || 'deepseek-chat'}
            onChange={(e) => { data.model = e.target.value; }}
            placeholder="模型名"
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-300 focus:outline-none"
          />
        </div>
      </div>
      {data.executed && data.result && (
        <div className="px-3 py-1.5 text-xs text-emerald-400 border-t border-gray-700/50 bg-emerald-500/5 rounded-b-xl">
          ✅ {data.result.duration}ms
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-purple-400 !w-3 !h-3 !border-2 !border-gray-900" />
    </div>
  );
}

export function OutputNode({ data, selected }) {
  return (
    <div className={`min-w-[220px] rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm shadow-xl ${
      selected ? 'border-emerald-400 ring-2 ring-emerald-400/20' : 'border-emerald-500/30'
    } ${data.executed ? 'ring-2 ring-emerald-400/40' : ''}`}>
      <Handle type="target" position={Position.Left} className="!bg-emerald-400 !w-3 !h-3 !border-2 !border-gray-900" />
      <div className="flex items-center gap-2 px-3 py-2 border-b border-gray-700/50 bg-emerald-500/10 rounded-t-xl">
        <span>📤</span>
        <span className="text-sm font-medium text-emerald-300">输出</span>
      </div>
      <div className="p-3">
        <div className="flex gap-2 text-xs text-gray-500">
          <span>格式:</span>
          <select
            value={data.format || 'text'}
            onChange={(e) => { data.format = e.target.value; }}
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-300 focus:outline-none"
          >
            <option value="text">纯文本</option>
            <option value="markdown">Markdown</option>
            <option value="json">JSON</option>
          </select>
        </div>
        <p className="text-xs text-gray-600 mt-2">接收上游节点结果</p>
      </div>
      {data.executed && data.result && (
        <div className="px-3 py-1.5 text-xs text-emerald-400 border-t border-gray-700/50 bg-emerald-500/5 rounded-b-xl">
          ✅ {data.result.duration}ms
        </div>
      )}
    </div>
  );
}
