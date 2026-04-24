import { Handle, Position } from 'reactflow';
import { useState } from 'react';
import { useI18n } from '../i18n.jsx';

export function MemoryNode({ data, selected, id }) {
  const { t } = useI18n();
  const [mode, setMode] = useState(data.mode || 'search');
  const [wing, setWing] = useState(data.wing || 'pipemind');
  const [room, setRoom] = useState(data.room || 'general');
  const [query, setQuery] = useState(data.query || '');
  const [nResults, setNResults] = useState(data.n_results || 5);

  const update = (key, val) => {
    data[key] = val;
  };

  return (
    <div className={`min-w-[340px] rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm shadow-xl ${
      selected ? 'border-violet-400 ring-2 ring-violet-400/20' : 'border-violet-500/30'
    }`}>
      <Handle type="target" position={Position.Left} className="!bg-violet-400 !w-3 !h-3 !border-2 !border-gray-900" />

      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50 bg-violet-500/10 rounded-t-xl">
        <div className="flex items-center gap-2">
          <span>🏛️</span>
          <span className="text-sm font-medium text-violet-300">{t('node.memory')}</span>
        </div>
        {data.onAddNode && (
          <button
            onClick={() => {/* source handle handles connections */}}
            className="w-5 h-5 flex items-center justify-center rounded-full bg-violet-600 hover:bg-violet-500 text-white text-xs leading-none transition-colors shadow-md"
            title={t('node.add')}
          >
            +
          </button>
        )}
      </div>

      <div className="p-3 space-y-2">
        {/* Mode selector */}
        <div className="flex gap-1 bg-gray-800/60 rounded-lg p-1">
          <button
            className={`flex-1 text-xs px-2 py-1 rounded-md transition-colors ${
              mode === 'search' ? 'bg-violet-600 text-white' : 'text-gray-400 hover:text-gray-200'
            }`}
            onClick={() => { setMode('search'); update('mode', 'search'); }}
          >
            🔍 {t('node.memory.search')}
          </button>
          <button
            className={`flex-1 text-xs px-2 py-1 rounded-md transition-colors ${
              mode === 'save' ? 'bg-violet-600 text-white' : 'text-gray-400 hover:text-gray-200'
            }`}
            onClick={() => { setMode('save'); update('mode', 'save'); }}
          >
            💾 {t('node.memory.save')}
          </button>
        </div>

        {/* Wing */}
        <div>
          <label className="text-xs text-gray-400 block mb-1">{t('node.memory.wing')}</label>
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-violet-500"
            value={wing} onChange={e => { setWing(e.target.value); update('wing', e.target.value); }}
            placeholder="pipemind"
          />
        </div>

        {/* Room */}
        <div>
          <label className="text-xs text-gray-400 block mb-1">{t('node.memory.room')}</label>
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-violet-500"
            value={room} onChange={e => { setRoom(e.target.value); update('room', e.target.value); }}
            placeholder="general"
          />
        </div>

        {/* Query (search mode) */}
        {mode === 'search' && (
          <>
            <div>
              <label className="text-xs text-gray-400 block mb-1">{t('node.memory.query')}</label>
              <input
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-violet-500"
                value={query} onChange={e => { setQuery(e.target.value); update('query', e.target.value); }}
                placeholder="搜索记忆..."
              />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">{t('node.memory.results')}</label>
              <input type="number" min={1} max={20}
                className="w-20 bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-violet-500"
                value={nResults} onChange={e => { const v = parseInt(e.target.value) || 5; setNResults(v); update('n_results', v); }}
              />
            </div>
          </>
        )}
      </div>

      {data.executed && data.duration !== undefined && (
        <div className="px-3 py-1.5 text-xs text-emerald-400 border-t border-gray-700/50 bg-emerald-500/5 rounded-b-xl">
          {t('node.done')}{data.duration}{t('node.duration')}
        </div>
      )}

      <Handle type="source" position={Position.Right} className="!bg-violet-400 !w-3 !h-3 !border-2 !border-gray-900" />
    </div>
  );
}
