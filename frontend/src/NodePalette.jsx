import { useCallback } from 'react';

const nodes = [
  { type: 'search', icon: '🔍', label: '搜索', color: 'bg-cyan-600/20 border-cyan-500/40 text-cyan-300', desc: '联网搜索信息' },
  { type: 'llm', icon: '🧠', label: 'LLM 处理', color: 'bg-purple-600/20 border-purple-500/40 text-purple-300', desc: 'AI 分析总结' },
  { type: 'output', icon: '📤', label: '输出', color: 'bg-emerald-600/20 border-emerald-500/40 text-emerald-300', desc: '格式化展示结果' },
];

export default function NodePalette() {
  const onDragStart = useCallback((event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  }, []);

  return (
    <aside className="w-56 border-r border-gray-800 bg-gray-900/50 flex flex-col">
      <h2 className="text-sm font-medium text-gray-400 px-4 py-3 border-b border-gray-800">
        节点库
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
                <p className="text-sm font-medium">{node.label}</p>
                <p className="text-xs opacity-70 mt-0.5">{node.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="p-3 border-t border-gray-800">
        <p className="text-xs text-gray-600 leading-relaxed">
          拖拽节点到画布<br />
          连接线串联工作流
        </p>
      </div>
    </aside>
  );
}
