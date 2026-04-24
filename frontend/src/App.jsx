import { useState, useCallback, useRef, useEffect, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  addEdge,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

import NodePalette from './NodePalette.jsx';
import { SearchNode, LLMNode, OutputNode, ReviewNode } from './nodes/SearchNode.jsx';
import { I18nProvider, useI18n } from './i18n.js';

const nodeTypes = {
  search: SearchNode,
  llm: LLMNode,
  output: OutputNode,
  review: ReviewNode,
};

const NEXT_TYPES = {
  search: ['llm', 'review', 'output'],
  llm: ['review', 'output'],
  review: ['output'],
  output: [],
};

let nodeId = 0;

function AppInner() {
  const { t, lang, setLang } = useI18n();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  // Pipeline save/load state
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [showLoadDialog, setShowLoadDialog] = useState(false);
  const [pipelineName, setPipelineName] = useState('');
  const [savedPipelines, setSavedPipelines] = useState([]);
  const [examples, setExamples] = useState([]);
  const [loadError, setLoadError] = useState(null);

  const reactFlowWrapper = useRef(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const lastPlacedRef = useRef(null);

  const getDefaultLabel = useCallback((type) => {
    const labels = { search: t('node.search'), llm: t('node.llm'), output: t('node.output'), review: t('node.review') };
    return labels[type] || type;
  }, [t]);

  // Fetch saved pipelines & examples on mount
  useEffect(() => {
    fetch('/api/pipelines').then(r => r.json()).then(d => {
      if (d.success) setSavedPipelines(d.pipelines);
    }).catch(() => {});
    fetch('/api/pipelines/examples').then(r => r.json()).then(d => {
      if (d.success) setExamples(d.examples);
    }).catch(() => {});
  }, []);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // ── Drop from palette (with auto-connect) ──
  const onDrop = useCallback((event) => {
    event.preventDefault();
    const type = event.dataTransfer.getData('application/reactflow');
    if (!type || !reactFlowInstance) return;

    const position = reactFlowInstance.screenToFlowPosition({
      x: event.clientX,
      y: event.clientY,
    });

    const newNodeId = `node_${++nodeId}`;
    const newNode = {
      id: newNodeId,
      type,
      position,
      data: { label: getDefaultLabel(type) },
    };

    setNodes((nds) => nds.concat(newNode));

    // Auto-connect if previous node was placed via palette and types are compatible
    const last = lastPlacedRef.current;
    if (last && NEXT_TYPES[last.type]?.includes(type)) {
      setEdges((eds) => eds.concat({
        id: `e-${last.id}-${newNodeId}`,
        source: last.id,
        target: newNodeId,
        animated: true,
        style: { stroke: '#6366f1', strokeWidth: 2 },
      }));
    }

    lastPlacedRef.current = { id: newNodeId, type };
  }, [reactFlowInstance, setNodes, setEdges, getDefaultLabel]);

  // ── Quick-add from node button (auto-connected) ──
  const handleAddNode = useCallback((parentId, nextType) => {
    if (!reactFlowInstance) return;
    const parent = reactFlowInstance.getNode(parentId);
    if (!parent) return;

    const newId = `node_${++nodeId}`;
    const newNode = {
      id: newId,
      type: nextType,
      position: { x: parent.position.x + 300, y: parent.position.y },
      data: { label: getDefaultLabel(nextType) },
    };

    setNodes((nds) => nds.concat(newNode));
    setEdges((eds) => eds.concat({
      id: `e-${parentId}-${newId}`,
      source: parentId,
      target: newId,
      animated: true,
      style: { stroke: '#6366f1', strokeWidth: 2 },
    }));

    lastPlacedRef.current = { id: newId, type: nextType };
  }, [reactFlowInstance, setNodes, setEdges, getDefaultLabel]);

  // Inject onAddNode into each node's data
  const nodesWithAdd = useMemo(() =>
    nodes.map(n => ({ ...n, data: { ...n.data, onAddNode: handleAddNode } })),
    [nodes, handleAddNode]
  );

  // ── Run workflow ──
  const runWorkflow = async () => {
    setRunning(true);
    setResults(null);
    setError(null);
    try {
      const res = await fetch('/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodes, edges }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      setResults(data.results);
      const executedIds = new Set(Object.keys(data.results));
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          data: {
            ...n.data,
            executed: executedIds.has(n.id),
            result: data.results[n.id],
          },
        }))
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setRunning(false);
    }
  };

  // ── Pipeline Save ──
  const savePipeline = async () => {
    const name = pipelineName.trim() || `Pipeline_${new Date().toLocaleDateString()}`;
    try {
      const res = await fetch('/api/pipelines', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, nodes, edges }),
      });
      const data = await res.json();
      if (data.success) {
        setShowSaveDialog(false);
        setPipelineName('');
        const listRes = await fetch('/api/pipelines');
        const listData = await listRes.json();
        if (listData.success) setSavedPipelines(listData.pipelines);
      } else {
        throw new Error(data.error);
      }
    } catch (err) {
      alert(t('error.save') + ': ' + err.message);
    }
  };

  // ── Pipeline Load ──
  const loadPipeline = async (id) => {
    setLoadError(null);
    try {
      const res = await fetch(`/api/pipelines/${id}`);
      const data = await res.json();
      if (data.success && data.pipeline) {
        setNodes(data.pipeline.nodes || []);
        setEdges(data.pipeline.edges || []);
        setResults(null);
        setError(null);
        let maxId = 0;
        for (const n of (data.pipeline.nodes || [])) {
          const num = parseInt(n.id.replace('node_', ''));
          if (num > maxId) maxId = num;
        }
        nodeId = maxId;
        lastPlacedRef.current = null;
        setShowLoadDialog(false);
      } else {
        throw new Error(data.error || t('error.load'));
      }
    } catch (err) {
      setLoadError(err.message);
    }
  };

  const deletePipeline = async (pId, e) => {
    e.stopPropagation();
    try {
      await fetch(`/api/pipelines/${pId}`, { method: 'DELETE' });
      setSavedPipelines(p => p.filter(x => x.id !== pId));
    } catch (err) {
      alert(t('error.delete') + ': ' + err.message);
    }
  };

  const exportResults = async () => {
    if (!results) return;
    try {
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ results }),
      });
      const data = await res.json();
      if (data.success) {
        const blob = new Blob([data.content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = data.filename;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      alert('Export failed: ' + err.message);
    }
  };

  const clearCanvas = () => {
    setNodes([]);
    setEdges([]);
    setResults(null);
    setError(null);
    nodeId = 0;
    lastPlacedRef.current = null;
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🔧</span>
          <h1 className="text-lg font-semibold text-white tracking-tight">{t('app.title')}</h1>
          <span className="px-2 py-0.5 text-xs bg-indigo-600/20 text-indigo-300 rounded-full border border-indigo-500/30">
            {t('app.subtitle')}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={setLang}
            className="px-2 py-1 text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            {t('app.lang')}
          </button>
          <button
            onClick={() => { setPipelineName(''); setShowLoadDialog(true); }}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors flex items-center gap-1"
          >
            {t('app.load')}
          </button>
          <button
            onClick={() => { setPipelineName(''); setShowSaveDialog(true); }}
            disabled={nodes.length === 0}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 disabled:text-gray-600 rounded-lg transition-colors flex items-center gap-1"
          >
            {t('app.save')}
          </button>
          <span className="w-px h-6 bg-gray-800 mx-1"></span>
          <button
            onClick={clearCanvas}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            {t('app.clear')}
          </button>
          <button
            onClick={runWorkflow}
            disabled={running || nodes.length === 0}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
          >
            <span>{running ? t('app.running') : t('app.run')}</span>
          </button>
        </div>
      </header>

      {/* Main */}
      <div className="flex flex-1 overflow-hidden">
        <NodePalette />

        <div className="flex-1" ref={reactFlowWrapper}>
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodesWithAdd}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onInit={setReactFlowInstance}
              onDrop={onDrop}
              onDragOver={onDragOver}
              nodeTypes={nodeTypes}
              fitView
              deleteKeyCode="Delete"
              snapToGrid
              snapGrid={[16, 16]}
              defaultEdgeOptions={{ animated: true, style: { stroke: '#6366f1', strokeWidth: 2 } }}
            >
              <Background color="#1e293b" gap={24} />
              <Controls position="bottom-right" />
              <MiniMap
                nodeStrokeColor="#6366f1"
                nodeColor="#1e293b"
                nodeBorderRadius={4}
                maskColor="rgba(0,0,0,0.6)"
                style={{ background: '#0f172a' }}
              />
            </ReactFlow>
          </ReactFlowProvider>
        </div>

        {/* Right: Results Panel */}
        <aside className="w-80 border-l border-gray-800 bg-gray-900/50 flex flex-col">
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
            <h2 className="text-sm font-medium text-gray-400">
              {results ? t('panel.results') : error ? t('panel.error') : t('panel.tips')}
            </h2>
            {results && (
              <button
                onClick={exportResults}
                className="text-xs text-gray-500 hover:text-emerald-400 transition-colors flex items-center gap-1"
              >
                {t('panel.export')}
              </button>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-4 text-sm space-y-3">
            {!results && !error && (
              <div className="text-gray-500 space-y-2">
                <p>{t('panel.tip1')}</p>
                <p>{t('panel.tip2')}</p>
                <p>{t('panel.tip3')}</p>
                <div className="mt-4 p-3 bg-gray-800/50 rounded-lg border border-gray-700/50">
                  <p className="text-gray-400 text-xs font-medium mb-2">{t('panel.qstart')}:</p>
                  <ol className="text-gray-500 text-xs space-y-1 list-decimal list-inside">
                    <li>{t('panel.qs1')}</li>
                    <li>{t('panel.qs2')}</li>
                    <li>{t('panel.qs3')}</li>
                  </ol>
                </div>
              </div>
            )}
            {error && (
              <div className="p-3 bg-red-900/30 border border-red-800/50 rounded-lg text-red-300 text-xs whitespace-pre-wrap">
                {error}
              </div>
            )}
            {results && Object.entries(results).map(([id, r]) => (
              <div key={id} className="bg-gray-800/50 rounded-lg border border-gray-700/50 overflow-hidden">
                <div className="flex items-center justify-between px-3 py-2 bg-gray-800/80 border-b border-gray-700/50">
                  <span className="text-xs font-medium text-gray-300">{r.label}</span>
                  <span className="text-xs text-gray-500">{r.duration}{t('node.duration')}</span>
                </div>
                <pre className="p-3 text-xs text-gray-400 whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
                  {String(r.output || '').slice(0, 2000)}
                </pre>
              </div>
            ))}
          </div>
        </aside>
      </div>

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowSaveDialog(false)}>
          <div className="w-96 bg-gray-900 rounded-xl border border-gray-700 shadow-2xl" onClick={e => e.stopPropagation()}>
            <div className="px-5 py-4 border-b border-gray-800">
              <h3 className="text-base font-medium text-white">{t('dialog.save.title')}</h3>
            </div>
            <div className="p-5">
              <label className="block text-sm text-gray-400 mb-2">{t('dialog.save.name')}</label>
              <input
                autoFocus
                value={pipelineName}
                onChange={e => setPipelineName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && savePipeline()}
                placeholder={t('dialog.save.placeholder')}
                className="w-full px-3 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-200 placeholder-gray-600 focus:outline-none focus:border-indigo-500/50"
              />
              <p className="text-xs text-gray-600 mt-2">{nodes.length} {t('dialog.save.nodes')}</p>
            </div>
            <div className="flex justify-end gap-2 px-5 py-4 border-t border-gray-800">
              <button onClick={() => setShowSaveDialog(false)} className="px-4 py-1.5 text-sm text-gray-400 hover:text-white rounded-lg transition-colors">
                {t('dialog.save.cancel')}
              </button>
              <button onClick={savePipeline} className="px-4 py-1.5 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors">
                {t('dialog.save.confirm')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Load Dialog */}
      {showLoadDialog && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowLoadDialog(false)}>
          <div className="w-[420px] max-h-[70vh] bg-gray-900 rounded-xl border border-gray-700 shadow-2xl flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
              <h3 className="text-base font-medium text-white">{t('dialog.load.title')}</h3>
              <button onClick={() => setShowLoadDialog(false)} className="text-gray-500 hover:text-white text-lg leading-none">&times;</button>
            </div>
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {loadError && (
                <div className="p-2 text-xs text-red-400 bg-red-900/20 rounded-lg">{loadError}</div>
              )}
              {examples.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-indigo-400 uppercase tracking-wider mb-2">{t('dialog.load.examples')}</h4>
                  <div className="space-y-2">
                    {examples.map(ex => (
                      <div
                        key={ex.id}
                        onClick={() => loadPipeline(ex.id)}
                        className="p-3 bg-gray-800/50 rounded-lg border border-gray-700/50 hover:border-indigo-500/50 cursor-pointer transition-colors"
                      >
                        <p className="text-sm font-medium text-gray-200">{ex.name}</p>
                        <p className="text-xs text-gray-500 mt-1">{ex.description}</p>
                        <p className="text-xs text-gray-600 mt-1">{ex.nodeCount} {t('dialog.save.nodes')}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {savedPipelines.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-emerald-400 uppercase tracking-wider mb-2">{t('dialog.load.saved')}</h4>
                  <div className="space-y-2">
                    {savedPipelines.map(p => (
                      <div
                        key={p.id}
                        onClick={() => loadPipeline(p.id)}
                        className="p-3 bg-gray-800/50 rounded-lg border border-gray-700/50 hover:border-emerald-500/50 cursor-pointer transition-colors group"
                      >
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-gray-200">{p.name}</p>
                          <button
                            onClick={(e) => deletePipeline(p.id, e)}
                            className="opacity-0 group-hover:opacity-100 text-xs text-red-400 hover:text-red-300 transition-all px-1.5 py-0.5 rounded hover:bg-red-900/30"
                          >{t('dialog.load.delete')}</button>
                        </div>
                        <p className="text-xs text-gray-600 mt-1">{p.nodeCount} {t('dialog.save.nodes')}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {examples.length === 0 && savedPipelines.length === 0 && (
                <p className="text-sm text-gray-500 text-center py-8">{t('dialog.load.empty')}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  return (
    <I18nProvider>
      <AppInner />
    </I18nProvider>
  );
}
