import { useState, useEffect, useCallback } from 'react';

export default function HistoryPanel({ t }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [runDetail, setRunDetail] = useState(null);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/runs');
      const data = await res.json();
      if (data.success) {
        setRuns(data.runs);
      }
    } catch (err) {
      console.error('Failed to fetch runs:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  const handleExpand = async (id) => {
    if (expandedId === id) {
      setExpandedId(null);
      setRunDetail(null);
      return;
    }
    setExpandedId(id);
    try {
      const res = await fetch(`/api/runs/${id}`);
      const data = await res.json();
      if (data.success) {
        setRunDetail(data.run);
      }
    } catch (err) {
      console.error('Failed to fetch run detail:', err);
      setRunDetail(null);
    }
  };

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    try {
      const res = await fetch(`/api/runs/${id}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        setRuns((prev) => prev.filter((r) => r.id !== id));
        if (expandedId === id) {
          setExpandedId(null);
          setRunDetail(null);
        }
      }
    } catch (err) {
      console.error('Failed to delete run:', err);
    }
  };

  const statusLabel = (status) => {
    const key = `history.status.${status}`;
    const label = t(key);
    // If translation not found, fallback
    return label !== key ? label : status;
  };

  const formatTime = (ts) => {
    if (!ts) return '';
    const d = new Date(ts);
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getMonth() + 1}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  return (
    <aside className="w-[420px] border-l border-gray-800 bg-gray-900/50 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <h2 className="text-sm font-medium text-gray-400">{t('history.title')}</h2>
        <button
          onClick={fetchRuns}
          className="text-xs text-gray-500 hover:text-indigo-400 transition-colors"
          disabled={loading}
        >
          ↻
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {loading && runs.length === 0 && (
          <p className="text-xs text-gray-500 text-center py-8">{t('app.running')}</p>
        )}
        {!loading && runs.length === 0 && (
          <p className="text-xs text-gray-500 text-center py-8">{t('history.empty')}</p>
        )}
        {runs.map((run) => (
          <div key={run.id}>
            <div
              onClick={() => handleExpand(run.id)}
              className="p-3 bg-gray-800/50 rounded-lg border border-gray-700/50 hover:border-indigo-500/50 cursor-pointer transition-colors group"
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs whitespace-nowrap">{statusLabel(run.status)}</span>
                  <span className="text-sm font-medium text-gray-200 truncate">{run.pipelineName}</span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <span className="text-xs text-gray-500">{run.nodeCount} {t('dialog.save.nodes')}</span>
                  <button
                    onClick={(e) => handleDelete(run.id, e)}
                    className="opacity-0 group-hover:opacity-100 text-xs text-red-400 hover:text-red-300 transition-all px-1 py-0.5 rounded hover:bg-red-900/30"
                    title={t('history.delete')}
                  >
                    ✕
                  </button>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-600">{formatTime(run.startedAt)}</span>
                <span className="text-xs text-gray-600">{expandedId === run.id ? '▲' : '▼'}</span>
              </div>
            </div>
            {expandedId === run.id && runDetail && (
              <div className="mx-2 p-3 bg-gray-800/30 rounded-b-lg border border-gray-700/30 border-t-0 text-xs space-y-2">
                <div className="text-gray-400">
                  <span className="text-gray-500">{t('history.id')}:</span> {runDetail.id}
                </div>
                <div className="text-gray-400">
                  <span className="text-gray-500">{t('history.time')}:</span>{' '}
                  {new Date(runDetail.startedAt || '').toLocaleString()}
                </div>
                {runDetail.completedAt && (
                  <div className="text-gray-400">
                    <span className="text-gray-500">{t('history.status')}:</span>{' '}
                    {statusLabel(runDetail.status)}
                  </div>
                )}
                {runDetail.results && Object.keys(runDetail.results).length > 0 && (
                  <div>
                    <div className="text-gray-500 mb-1">{t('panel.results')}:</div>
                    <pre className="text-gray-400 bg-gray-900/50 rounded p-2 max-h-48 overflow-y-auto whitespace-pre-wrap break-all">
                      {JSON.stringify(runDetail.results, null, 2).slice(0, 5000)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </aside>
  );
}
