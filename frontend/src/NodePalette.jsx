import { useCallback } from 'react';
import { useI18n } from './i18n';

const nodes = [
  { type: 'search', icon: '🔍', color: 'bg-cyan-600/20 border-cyan-500/40 text-cyan-300', key: 'search' },
  { type: 'llm', icon: '🧠', color: 'bg-purple-600/20 border-purple-500/40 text-purple-300', key: 'llm' },
  { type: 'output', icon: '📤', color: 'bg-emerald-600/20 border-emerald-500/40 text-emerald-300', key: 'output' },
  { type: 'review', icon: '🔬', color: 'bg-amber-600/20 border-amber-500/40 text-amber-300', key: 'review' },
  { type: 'kb', icon: '📚', color: 'bg-blue-600/20 border-blue-500/40 text-blue-300', key: 'kb' },
  { type: 'mindmap', icon: '🧠', color: 'bg-rose-600/20 border-rose-500/40 text-rose-300', key: 'mindmap' },
];

export default function NodePalette() {
  const { t } = useI18n();

  const onDragStart = useCallback((event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  }, []);

  return (
    <aside className="w-56 border-r border-gray-800 bg-gray-900/50 flex flex-col">
      <h2 className="text-sm font-medium text-gray-400 px-4 py-3 border-b border-gray-800">
        {t('palette.title')}
      </h2>
      <div className="flex-1 p-3 space-y-2 overflow-y-auto">
        {nodes.map((node) => (
          <div
            key={node.type}
            draggable
            onDragStart={(e) => onDragStart(e, node.type)}
            className={`p-3 rounded-lg border cursor-grab active:cursor-grabbing transition-all hover:scale-[1.02] hover:shadow-lg ${node.color}`}
          >
            <div className="flex items-center gap-2">
              <span className="text-lg">{node.icon}</span>
              <div>
                <p className="text-sm font-medium">{t(`palette.${node.key}`)}</p>
                <p className="text-xs opacity-70 mt-0.5">{t(`palette.${node.key}.desc`)}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="p-3 border-t border-gray-800">
        <p className="text-xs text-gray-600 leading-relaxed">
          {t('palette.hint1')}<br />
          {t('palette.hint2')}
        </p>
      </div>
    </aside>
  );
}
