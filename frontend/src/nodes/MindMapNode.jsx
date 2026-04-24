import { Handle, Position } from 'reactflow';
import { useEffect, useRef, useState } from 'react';
import { Transformer } from 'markmap-lib';
import { Markmap } from 'markmap-view';
import { useI18n } from '../i18n';

// ── Mind Map Node ──
export function MindMapNode({ data, selected, id }) {
  const { t } = useI18n();
  const containerRef = useRef(null);
  const markmapRef = useRef(null);
  const [error, setError] = useState(null);

  const content = data.output || data.sourceContent || '';

  useEffect(() => {
    if (!containerRef.current || !content) return;

    // Destroy old instance
    if (markmapRef.current) {
      markmapRef.current.destroy();
      markmapRef.current = null;
    }

    try {
      const transformer = new Transformer();
      const { root } = transformer.transform(content);
      markmapRef.current = Markmap.create(containerRef.current, {
        colorFreezeLevel: 2,
        maxWidth: 320,
        nodeMinHeight: 16,
        zoom: false,
        pan: false,
      }, root);
      setError(null);

      // Fit to container on next frame
      requestAnimationFrame(() => {
        if (markmapRef.current) {
          markmapRef.current.fit();
        }
      });
    } catch (err) {
      console.error('markmap render error:', err);
      setError(err.message);
    }

    return () => {
      if (markmapRef.current) {
        markmapRef.current.destroy();
        markmapRef.current = null;
      }
    };
  }, [content]);

  // Refit on selection
  useEffect(() => {
    if (markmapRef.current && selected) {
      requestAnimationFrame(() => {
        if (markmapRef.current) {
          markmapRef.current.fit();
        }
      });
    }
  }, [selected]);

  const formatHint = content && !content.includes('#') && !content.includes('- ')
    ? '💡 提示：上游内容缺少标题结构(###/##/#)，建议用 LLM 输出带标题的格式'
    : null;

  return (
    <div className={`min-w-[380px] rounded-xl border-2 bg-gray-900/90 backdrop-blur-sm shadow-xl ${
      selected ? 'border-rose-400 ring-2 ring-rose-400/20' : 'border-rose-500/30'
    }`}>
      <Handle type="target" position={Position.Left} className="!bg-rose-400 !w-3 !h-3 !border-2 !border-gray-900" />
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50 bg-rose-500/10 rounded-t-xl">
        <div className="flex items-center gap-2">
          <span>🧠</span>
          <span className="text-sm font-medium text-rose-300">{t('node.mindmap')}</span>
        </div>
        {data.onAddNode && (
          <div style={{ position: 'relative', zIndex: 50 }}>
            <button
              onClick={() => { /* source handle handles connections */ }}
              className="w-5 h-5 flex items-center justify-center rounded-full bg-rose-600 hover:bg-rose-500 text-white text-xs leading-none transition-colors shadow-md"
              title={t('node.add')}
            >
              +
            </button>
          </div>
        )}
      </div>
      <div className="p-2" style={{ height: 280 }}>
        {error ? (
          <div className="flex items-center justify-center h-full text-xs text-red-400">
            ❌ 渲染错误: {error.slice(0, 100)}
          </div>
        ) : content ? (
          <div ref={containerRef} className="w-full h-full overflow-hidden rounded-lg bg-gray-800/30" />
        ) : (
          <div className="flex items-center justify-center h-full text-xs text-gray-500">
            {t('node.mindmap.placeholder')}
          </div>
        )}
      </div>
      {formatHint && (
        <div className="px-3 py-1.5 text-xs text-amber-400 border-t border-gray-700/50 bg-amber-500/5">
          {formatHint}
        </div>
      )}
      {data.executed && data.duration !== undefined && (
        <div className="px-3 py-1.5 text-xs text-emerald-400 border-t border-gray-700/50 bg-emerald-500/5 rounded-b-xl">
          {t('node.done')}{data.duration}{t('node.duration')}
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-rose-400 !w-3 !h-3 !border-2 !border-gray-900" />
    </div>
  );
}
