import { Handle, Position } from 'reactflow';
import { useState } from 'react';
import { useI18n } from '../i18n';

// ── Quick-add helper ──
const NEXT_TYPES = {
  search: [{ type: 'llm', icon: '🧠' }, { type: 'review', icon: '🔬' }, { type: 'kb', icon: '📚' }, { type: 'memory', icon: '🏛️' }, { type: 'mindmap', icon: '🧠' }, { type: 'condition', icon: '🔀' }, { type: 'output', icon: '📤' }],
  llm: [{ type: 'review', icon: '🔬' }, { type: 'memory', icon: '🏛️' }, { type: 'mindmap', icon: '🧠' }, { type: 'condition', icon: '🔀' }, { type: 'output', icon: '📤' }],
  review: [{ type: 'memory', icon: '🏛️' }, { type: 'mindmap', icon: '🧠' }, { type: 'condition', icon: '🔀' }, { type: 'output', icon: '📤' }],
  kb: [{ type: 'llm', icon: '🧠' }, { type: 'review', icon: '🔬' }, { type: 'memory', icon: '🏛️' }, { type: 'mindmap', icon: '🧠' }, { type: 'condition', icon: '🔀' }, { type: 'output', icon: '📤' }],
  mindmap: [],
  memory: [{ type: 'llm', icon: '🧠' }, { type: 'review', icon: '🔬' }, { type: 'mindmap', icon: '🧠' }, { type: 'condition', icon: '🔀' }, { type: 'output', icon: '📤' }],
  condition: [{ type: 'llm', icon: '🧠' }, { type: 'review', icon: '🔬' }, { type: 'memory', icon: '🏛️' }, { type: 'mindmap', icon: '🧠' }, { type: 'output', icon: '📤' }],
};

function AddButton({ nodeType, nodeId, onAddNode }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const options = NEXT_TYPES[nodeType] || [];
  if (options.length === 0) return null;

  return (
    <div style={{ position: 'relative', zIndex: 50 }}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(o => !o); }}
        title={t('node.add')}
        className="w-5 h-5 flex items-center justify-center rounded-full bg-indigo-600 hover:bg-indigo-500 text-white text-xs leading-none transition-colors shadow-md"
      >
        +
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-6 z-50 bg-gray-800 border border-gray-700 rounded-lg py-1 shadow-xl min-w-[100px]">
            {options.map(opt => (
              <button
                key={opt.type}
                onClick={(e) => { e.stopPropagation(); onAddNode(nodeId, opt.type); setOpen(false); }}
                className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-gray-300 hover:bg-gray-700 hover:text-white transition-colors text-left"
              >
                <span>{opt.icon}</span>
                <span>{t(`node.add.${opt.type}`)}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ── Search Node ──
export function SearchNode({ data, selected, id }) {
  const { t } = useI18n();
  const [query, setQuery] = useState(data.query || '');
  data.query = query;

  return (
    <div className={`min-w-[220px] rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm shadow-xl ${
      selected ? 'border-cyan-400 ring-2 ring-cyan-400/20' : (data.error ? 'node-error' : 'border-cyan-500/30')
    } ${data.executing ? 'node-executing' : ''} ${data.executed ? 'ring-2 ring-emerald-400/40' : ''} ${data.error ? 'node-error' : ''}`}>
      <Handle type="target" position={Position.Left} className="!bg-cyan-400 !w-3 !h-3 !border-2 !border-gray-900" />
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50 bg-cyan-500/10 rounded-t-xl">
        <div className="flex items-center gap-2">
          <span>🔍</span>
          <span className="text-sm font-medium text-cyan-300">{t('node.search')}</span>
        </div>
        {data.onAddNode && <AddButton nodeType="search" nodeId={id} onAddNode={data.onAddNode} />}
      </div>
      <div className="p-3 space-y-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('node.search.placeholder')}
          className="w-full px-2 py-1.5 text-xs bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:border-cyan-500/50"
        />
        <div className="flex gap-2 text-xs text-gray-500">
          <span>{t('node.search.freshness')}:</span>
          <select
            value={data.freshness || 'week'}
            onChange={(e) => { data.freshness = e.target.value; }}
            className="bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-300 focus:outline-none"
          >
            <option value="day">{t('node.search.day')}</option>
            <option value="week">{t('node.search.week')}</option>
            <option value="month">{t('node.search.month')}</option>
          </select>
        </div>
      </div>
      {data.executed && data.result && (
        <div className="px-3 py-1.5 text-xs text-emerald-400 border-t border-gray-700/50 bg-emerald-500/5 rounded-b-xl">
          {t('node.done')}{data.result.duration}{t('node.duration')}
        </div>
      )}
      {data.error && (
        <div className="node-error-badge">❌ {String(data.error).slice(0, 80)}</div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-cyan-400 !w-3 !h-3 !border-2 !border-gray-900" />
    </div>
  );
}

// ── LLM Node ──
export function LLMNode({ data, selected, id }) {
  const { t } = useI18n();
  const [prompt, setPrompt] = useState(data.prompt || '请总结以下内容的关键信息');
  data.prompt = prompt;

  return (
    <div className={`min-w-[220px] rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm shadow-xl ${
      selected ? 'border-purple-400 ring-2 ring-purple-400/20' : (data.error ? 'node-error' : 'border-purple-500/30')
    } ${data.executing ? 'node-executing' : ''} ${data.executed ? 'ring-2 ring-emerald-400/40' : ''} ${data.error ? 'node-error' : ''}`}>
      <Handle type="target" position={Position.Left} className="!bg-purple-400 !w-3 !h-3 !border-2 !border-gray-900" />
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50 bg-purple-500/10 rounded-t-xl">
        <div className="flex items-center gap-2">
          <span>🧠</span>
          <span className="text-sm font-medium text-purple-300">{t('node.llm')}</span>
        </div>
        {data.onAddNode && <AddButton nodeType="llm" nodeId={id} onAddNode={data.onAddNode} />}
      </div>
      <div className="p-3 space-y-2">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={t('node.llm.placeholder')}
          rows={3}
          className="w-full px-2 py-1.5 text-xs bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:border-purple-500/50 resize-none"
        />
        <div className="flex gap-2 text-xs text-gray-500">
          <span>{t('node.llm.model')}:</span>
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
          {t('node.done')}{data.result.duration}{t('node.duration')}
        </div>
      )}
      {data.error && (
        <div className="node-error-badge">❌ {String(data.error).slice(0, 80)}</div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-purple-400 !w-3 !h-3 !border-2 !border-gray-900" />
    </div>
  );
}

// ── Review Node ──
export function ReviewNode({ data, selected, id }) {
  const { t } = useI18n();
  const [tone, setTone] = useState(data.tone || 'balanced');
  const [strictness, setStrictness] = useState(data.strictness || 'normal');
  data.tone = tone;
  data.strictness = strictness;

  return (
    <div className={`min-w-[220px] rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm shadow-xl ${
      selected ? 'border-amber-400 ring-2 ring-amber-400/20' : (data.error ? 'node-error' : 'border-amber-500/30')
    } ${data.executing ? 'node-executing' : ''} ${data.executed ? 'ring-2 ring-emerald-400/40' : ''} ${data.error ? 'node-error' : ''}`}>
      <Handle type="target" position={Position.Left} className="!bg-amber-400 !w-3 !h-3 !border-2 !border-gray-900" />
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50 bg-amber-500/10 rounded-t-xl">
        <div className="flex items-center gap-2">
          <span>🔬</span>
          <span className="text-sm font-medium text-amber-300">{t('node.review')}</span>
        </div>
        {data.onAddNode && <AddButton nodeType="review" nodeId={id} onAddNode={data.onAddNode} />}
      </div>
      <div className="p-3 space-y-2">
        <div className="flex gap-2 text-xs text-gray-500">
          <span>{t('node.review.strictness')}:</span>
          <select
            value={strictness}
            onChange={(e) => setStrictness(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-300 focus:outline-none"
          >
            <option value="mild">{t('node.review.mild')}</option>
            <option value="normal">{t('node.review.normal')}</option>
            <option value="strict">{t('node.review.strict')}</option>
          </select>
        </div>
        <div className="flex gap-2 text-xs text-gray-500">
          <span>{t('node.review.tone')}:</span>
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-300 focus:outline-none"
          >
            <option value="mild">{t('node.review.kind')}</option>
            <option value="balanced">{t('node.review.balanced')}</option>
            <option value="critical">{t('node.review.critical')}</option>
          </select>
        </div>
        <p className="text-xs text-gray-600">{t('node.review.desc')}</p>
      </div>
      {data.executed && data.result && (
        <div className="px-3 py-1.5 text-xs text-emerald-400 border-t border-gray-700/50 bg-emerald-500/5 rounded-b-xl">
          {t('node.done')}{data.result.duration}{t('node.duration')}
        </div>
      )}
      {data.error && (
        <div className="node-error-badge">❌ {String(data.error).slice(0, 80)}</div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-amber-400 !w-3 !h-3 !border-2 !border-gray-900" />
    </div>
  );
}

// ── Output Node ──
export function OutputNode({ data, selected, id }) {
  const { t } = useI18n();

  return (
    <div className={`min-w-[220px] rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm shadow-xl ${
      selected ? 'border-emerald-400 ring-2 ring-emerald-400/20' : (data.error ? 'node-error' : 'border-emerald-500/30')
    } ${data.executing ? 'node-executing' : ''} ${data.executed ? 'ring-2 ring-emerald-400/40' : ''} ${data.error ? 'node-error' : ''}`}>
      <Handle type="target" position={Position.Left} className="!bg-emerald-400 !w-3 !h-3 !border-2 !border-gray-900" />
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50 bg-emerald-500/10 rounded-t-xl">
        <div className="flex items-center gap-2">
          <span>📤</span>
          <span className="text-sm font-medium text-emerald-300">{t('node.output')}</span>
        </div>
        {data.onAddNode && <AddButton nodeType="output" nodeId={id} onAddNode={data.onAddNode} />}
      </div>
      <div className="p-3">
        <div className="flex gap-2 text-xs text-gray-500">
          <span>{t('node.output.format')}:</span>
          <select
            value={data.format || 'text'}
            onChange={(e) => { data.format = e.target.value; }}
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-300 focus:outline-none"
          >
            <option value="text">{t('node.output.text')}</option>
            <option value="markdown">{t('node.output.markdown')}</option>
            <option value="json">{t('node.output.json')}</option>
          </select>
        </div>
        <p className="text-xs text-gray-600 mt-2">{t('node.output.desc')}</p>
      </div>
      {data.executed && data.result && (
        <div className="px-3 py-1.5 text-xs text-emerald-400 border-t border-gray-700/50 bg-emerald-500/5 rounded-b-xl">
          {t('node.done')}{data.result.duration}{t('node.duration')}
        </div>
      )}
      {data.error && (
        <div className="node-error-badge">❌ {String(data.error).slice(0, 80)}</div>
      )}
    </div>
  );
}

// ── Knowledge Base Node ──
export function KBNode({ data, selected, id }) {
  const { t } = useI18n();
  const [query, setQuery] = useState(data.query || '');
  const [kbId, setKbId] = useState(data.knowledge_base_id || '');
  data.query = query;
  data.knowledge_base_id = kbId;

  return (
    <div className={`min-w-[220px] rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm shadow-xl ${
      selected ? 'border-blue-400 ring-2 ring-blue-400/20' : (data.error ? 'node-error' : 'border-blue-500/30')
    } ${data.executing ? 'node-executing' : ''} ${data.executed ? 'ring-2 ring-emerald-400/40' : ''} ${data.error ? 'node-error' : ''}`}>
      <Handle type="target" position={Position.Left} className="!bg-blue-400 !w-3 !h-3 !border-2 !border-gray-900" />
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50 bg-blue-500/10 rounded-t-xl">
        <div className="flex items-center gap-2">
          <span>📚</span>
          <span className="text-sm font-medium text-blue-300">{t('node.kb')}</span>
        </div>
        {data.onAddNode && <AddButton nodeType="kb" nodeId={id} onAddNode={data.onAddNode} />}
      </div>
      <div className="p-3 space-y-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('node.kb.placeholder')}
          className="w-full px-2 py-1.5 text-xs bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:border-blue-500/50"
        />
        <div className="flex gap-2 text-xs text-gray-500">
          <span>{t('node.kb.kbId')}:</span>
          <input
            value={kbId}
            onChange={(e) => setKbId(e.target.value)}
            placeholder="kb_xxx"
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-300 focus:outline-none"
          />
        </div>
      </div>
      {data.executed && data.result && (
        <div className="px-3 py-1.5 text-xs text-emerald-400 border-t border-gray-700/50 bg-emerald-500/5 rounded-b-xl">
          {t('node.done')}{data.result.duration}{t('node.duration')}
        </div>
      )}
      {data.error && (
        <div className="node-error-badge">❌ {String(data.error).slice(0, 80)}</div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-blue-400 !w-3 !h-3 !border-2 !border-gray-900" />
    </div>
  );
}
