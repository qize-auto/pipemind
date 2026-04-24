import { useState } from 'react';

const TYPE_CONFIGS = {
  search: [
    { key: 'keyword', label: 'keyword', type: 'text', placeholderKey: 'node.search.placeholder' },
    { key: 'count', label: 'count', type: 'number', default: 5, min: 1, max: 20 },
    { key: 'freshness', label: 'freshness', type: 'select', optionsKey: 'node.search.freshness.options' },
  ],
  llm: [
    { key: 'prompt', label: 'prompt', type: 'textarea', placeholderKey: 'node.llm.placeholder', rows: 4 },
    { key: 'model', label: 'model', type: 'select', default: 'deepseek-chat', options: [
      { value: 'deepseek-chat', labelKey: 'model.ds.chat' },
      { value: 'deepseek-reasoner', labelKey: 'model.ds.reasoner' },
      { value: 'qwen3.5-plus', labelKey: 'model.qwen.plus' },
      { value: 'MiniMax-M2.5', labelKey: 'model.minimax.m25' },
      { value: 'openclaw', labelKey: 'model.openclaw' },
    ]},
    { key: 'temperature', label: 'temperature', type: 'range', default: 0.3, min: 0, max: 1, step: 0.1 },
  ],
  kb: [
    { key: 'query', label: 'query', type: 'text', placeholderKey: 'node.kb.placeholder' },
    { key: 'limit', label: 'limit', type: 'number', default: 5, min: 1, max: 20 },
  ],
  review: [
    { key: 'strictness', label: 'strictness', type: 'select', options: [
      { value: 'mild', labelKey: 'node.review.mild' },
      { value: 'normal', labelKey: 'node.review.normal' },
      { value: 'strict', labelKey: 'node.review.strict' },
    ]},
    { key: 'tone', label: 'tone', type: 'select', options: [
      { value: 'kind', labelKey: 'node.review.kind' },
      { value: 'balanced', labelKey: 'node.review.balanced' },
      { value: 'critical', labelKey: 'node.review.critical' },
    ]},
  ],
  memory: [
    { key: 'query', label: 'query', type: 'text', placeholderKey: 'node.memory.query' },
    { key: 'wing', label: 'wing', type: 'text', placeholder: 'pipemind' },
    { key: 'room', label: 'room', type: 'text', placeholder: 'general' },
    { key: 'limit', label: 'limit', type: 'number', default: 5 },
  ],
  mindmap: [],  // no config
  output: [
    { key: 'format', label: 'format', type: 'select', options: [
      { value: 'text', labelKey: 'node.output.text' },
      { value: 'markdown', labelKey: 'node.output.markdown' },
      { value: 'json', labelKey: 'node.output.json' },
    ]},
  ],
};

export default function ConfigSidebar({ selectedNode, updateNodeData, t }) {
  if (!selectedNode) return null;

  const configs = TYPE_CONFIGS[selectedNode.type] || [];
  const nodeData = selectedNode.data || {};

  const handleChange = (key, value) => {
    updateNodeData(selectedNode.id, { [key]: value });
  };

  return (
    <div className="w-80 border-l border-gray-800 bg-gray-900/50 flex flex-col">
      <div className="px-4 py-3 border-b border-gray-800">
        <h2 className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <NodeIcon type={selectedNode.type} />
          {nodeData.label}
        </h2>
        <span className="text-xs text-gray-600 mt-0.5 block">{selectedNode.type}</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {configs.length === 0 && (
          <p className="text-xs text-gray-500 italic">{t('node.noConfig')}</p>
        )}
        {configs.map(cfg => (
          <div key={cfg.key}>
            <label className="block text-xs text-gray-500 mb-1">{cfg.label}</label>
            {cfg.type === 'text' && (
              <input
                type="text"
                value={nodeData[cfg.key] || cfg.default || ''}
                onChange={e => handleChange(cfg.key, e.target.value)}
                placeholder={cfg.placeholderKey ? t(cfg.placeholderKey) : cfg.placeholder || ''}
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:border-indigo-500/50"
              />
            )}
            {cfg.type === 'number' && (
              <input
                type="number"
                value={nodeData[cfg.key] ?? cfg.default ?? ''}
                onChange={e => handleChange(cfg.key, parseInt(e.target.value) || cfg.default)}
                min={cfg.min} max={cfg.max}
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-indigo-500/50"
              />
            )}
            {cfg.type === 'textarea' && (
              <textarea
                rows={cfg.rows || 3}
                value={nodeData[cfg.key] || ''}
                onChange={e => handleChange(cfg.key, e.target.value)}
                placeholder={t(cfg.placeholderKey || '')}
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:border-indigo-500/50 resize-none"
              />
            )}
            {cfg.type === 'select' && (
              <select
                value={nodeData[cfg.key] || cfg.options[0]?.value || ''}
                onChange={e => handleChange(cfg.key, e.target.value)}
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-200 focus:outline-none focus:border-indigo-500/50"
              >
                {(cfg.options || []).map(opt => (
                  <option key={opt.value} value={opt.value}>
                    {opt.labelKey ? t(opt.labelKey) : opt.value}
                  </option>
                ))}
                {(cfg.optionsKey && t(cfg.optionsKey) !== cfg.optionsKey) && (
                  Object.entries(t(cfg.optionsKey)).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))
                )}
              </select>
            )}
            {cfg.type === 'range' && (
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  value={nodeData[cfg.key] ?? cfg.default ?? 0.3}
                  onChange={e => handleChange(cfg.key, parseFloat(e.target.value))}
                  min={cfg.min || 0} max={cfg.max || 1} step={cfg.step || 0.1}
                  className="flex-1"
                />
                <span className="text-xs text-gray-500 w-8 text-right">
                  {nodeData[cfg.key] ?? cfg.default ?? 0.3}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function NodeIcon({ type }) {
  const icons = {
    search: '🔍', llm: '🤖', review: '🔬',
    kb: '📚', mindmap: '🧠', memory: '🏛️', output: '📤',
  };
  return <span>{icons[type] || '📦'}</span>;
}
