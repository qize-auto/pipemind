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
import ConfigSidebar from './ConfigSidebar.jsx';
import { SearchNode, LLMNode, OutputNode, ReviewNode, KBNode } from './nodes/SearchNode.jsx';
import { MindMapNode } from './nodes/MindMapNode.jsx';
import { MemoryNode } from './nodes/MemoryNode.jsx';
import { I18nProvider, useI18n } from './i18n.jsx';

const nodeTypes = {
  search: SearchNode,
  llm: LLMNode,
  output: OutputNode,
  review: ReviewNode,
  kb: KBNode,
  mindmap: MindMapNode,
  memory: MemoryNode,
};

const NEXT_TYPES = {
  search: ['llm', 'review', 'kb', 'memory', 'mindmap', 'output'],
  llm: ['review', 'memory', 'mindmap', 'output'],
  review: ['memory', 'mindmap', 'output'],
  kb: ['llm', 'review', 'memory', 'mindmap', 'output'],
  mindmap: [],
  memory: ['llm', 'review', 'output', 'mindmap'],
};

const AUTOSAVE_KEY = 'pipemind_autosave';

let nodeId = 0;

function AppInner() {
  const { t, lang, setLang } = useI18n();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [resultTab, setResultTab] = useState('all');

  // Step-by-step execution state
  const [stepMode, setStepMode] = useState(false);
  const [executionPlan, setExecutionPlan] = useState([]);
  const [executionStep, setExecutionStep] = useState(0);
  const [executingNodeId, setExecutingNodeId] = useState(null);

  // Autosave recovery banner
  const [showRestoreBanner, setShowRestoreBanner] = useState(false);

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
  const autosaveTimerRef = useRef(null);

  const getDefaultLabel = useCallback((type) => {
    const labels = { search: t('node.search'), llm: t('node.llm'), output: t('node.output'), review: t('node.review'), kb: t('node.kb'), mindmap: t('node.mindmap'), memory: t('node.memory') };
    return labels[type] || type;
  }, [t]);

  // -- Check for autosaved pipeline on mount --
  useEffect(() => {
    try {
      const saved = localStorage.getItem(AUTOSAVE_KEY);
      if (saved) {
        const data = JSON.parse(saved);
        if (data.nodes && data.nodes.length > 0) {
          setShowRestoreBanner(true);
        }
      }
    } catch (e) {
      // ignore parse errors
    }

    fetch('/api/pipelines').then(r => r.json()).then(d => {
      if (d.success) setSavedPipelines(d.pipelines);
    }).catch(() => {});
    fetch('/api/pipelines/examples').then(r => r.json()).then(d => {
      if (d.success) setExamples(d.examples);
    }).catch(() => {});
  }, []);

  // -- Autosave with debounce (2s) --
  useEffect(() => {
    if (autosaveTimerRef.current) {
      clearTimeout(autosaveTimerRef.current);
    }

    autosaveTimerRef.current = setTimeout(() => {
      if (nodes.length > 0) {
        try {
          localStorage.setItem(AUTOSAVE_KEY, JSON.stringify({ nodes, edges }));
        } catch (e) {
          // localStorage quota exceeded or unavailable
        }
      }
    }, 2000);

    return () => {
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
      }
    };
  }, [nodes, edges]);

  // -- Clear autosave when pipeline is explicitly loaded or canvas cleared --
  const clearAutosave = useCallback(() => {
    try {
      localStorage.removeItem(AUTOSAVE_KEY);
    } catch (e) {}
    setShowRestoreBanner(false);
  }, []);

  const handleRestore = useCallback(() => {
    try {
      const saved = localStorage.getItem(AUTOSAVE_KEY);
      if (saved) {
        const data = JSON.parse(saved);
        setNodes(data.nodes || []);
        setEdges(data.edges || []);
        setResults(null);
        setError(null);
        let maxId = 0;
        for (const n of (data.nodes || [])) {
          const num = parseInt(n.id.replace('node_', ''));
          if (num > maxId) maxId = num;
        }
        nodeId = maxId;
        lastPlacedRef.current = null;
      }
    } catch (e) {}
    clearAutosave();
  }, [setNodes, setEdges, clearAutosave]);

  const handleDiscard = useCallback(() => {
    clearAutosave();
  }, [clearAutosave]);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // -- Drop from palette (with auto-connect) --
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

  // -- Quick-add from node button (auto-connected) --
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

  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const updateNodeData = useCallback((nodeId, newData) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId
          ? { ...n, data: { ...n.data, ...newData } }
          : n
      )
    );
    setSelectedNode((prev) => {
      if (prev && prev.id === nodeId) {
        return { ...prev, data: { ...prev.data, ...newData } };
      }
      return prev;
    });
  }, [setNodes]);

  // -- Node visual helpers --
  const markNodesExecuting = useCallback((nodeIds) => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          executing: nodeIds.includes(n.id),
          executed: nodeIds.includes(n.id) ? false : n.data.executed,
          error: null,
          result: null,
        },
      }))
    );
  }, [setNodes]);

  const clearNodeExecutionState = useCallback(() => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: { ...n.data, executing: false, executed: false, error: null, result: null },
      }))
    );
  }, [setNodes]);

  const markNodeCompleted = useCallback((nodeId, result) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId
          ? {
              ...n,
              data: {
                ...n.data,
                executing: false,
                executed: true,
                result: result || null,
              },
            }
          : n
      )
    );
  }, [setNodes]);

  // -- Run all (original workflow) --
  const runAll = useCallback(async () => {
    // Exit step mode if active
    setStepMode(false);
    setExecutionPlan([]);
    setExecutionStep(0);
    setExecutingNodeId(null);

    setRunning(true);
    setResults(null);
    setError(null);
    setSelectedNode(null);
    setResultTab('all');

    clearNodeExecutionState();

    setTimeout(async () => {
      markNodesExecuting(nodes.map(n => n.id));
      try {
        const res = await fetch('/api/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nodes, edges, pipelineName: pipelineName || 'unnamed' }),
        });
        const data = await res.json();
        if (!res.ok || data.error) {
          throw new Error(data.error || `HTTP ${res.status}`);
        }
        setResults(data.results);
        setShowHistory(false);
        setNodes((nds) =>
          nds.map((n) => {
            const result = data.results[n.id];
            return {
              ...n,
              data: {
                ...n.data,
                executing: false,
                executed: true,
                result: result || null,
              },
            };
          })
        );
      } catch (err) {
        setError(err.message);
        setNodes((nds) =>
          nds.map((n) => ({
            ...n,
            data: { ...n.data, executing: false, error: err.message },
          }))
        );
      } finally {
        setRunning(false);
      }
    }, 150);
  }, [nodes, edges, clearNodeExecutionState, markNodesExecuting, setNodes]);

  // -- Step-by-step execution: init --
  const runInit = useCallback(async () => {
    setRunning(true);
    setResults(null);
    setError(null);
    setSelectedNode(null);
    setResultTab('all');

    clearNodeExecutionState();

    try {
      const res = await fetch('/api/run-init', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodes, edges }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || `HTTP ${res.status}`);
      }

      setExecutionPlan(data.plan);
      setExecutionStep(0);
      setStepMode(true);
      setRunning(false);
    } catch (err) {
      setError(err.message);
      setRunning(false);
    }
  }, [nodes, edges, clearNodeExecutionState]);

  // -- Step-by-step execution: next step --
  const runStep = useCallback(async () => {
    if (executionStep >= executionPlan.length) return;

    const nodeId = executionPlan[executionStep];
    setExecutingNodeId(nodeId);

    // Mark current node as executing
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          executing: n.id === nodeId,
          executed: n.data.executed || false,
        },
      }))
    );

    setRunning(true);

    try {
      const currentResults = results || {};
      const res = await fetch('/api/run-step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nodes, edges, nodeId, resultsSoFar: currentResults }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || `HTTP ${res.status}`);
      }

      setResults(data.results);
      setExecutionStep(executionStep + 1);
      setExecutingNodeId(null);

      // Mark node as completed
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId
            ? {
                ...n,
                data: {
                  ...n.data,
                  executing: false,
                  executed: true,
                  result: data.result || null,
                },
              }
            : n
        )
      );
    } catch (err) {
      setError(err.message);
      setExecutingNodeId(null);
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId
            ? { ...n, data: { ...n.data, executing: false, error: err.message } }
            : n
        )
      );
    } finally {
      setRunning(false);
    }
  }, [executionPlan, executionStep, nodes, edges, results, setNodes]);

  // -- Pipeline Save --
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

  // -- Pipeline Load --
  const loadPipeline = async (id) => {
    setLoadError(null);
    try {
      const res = await fetch(`/api/pipelines/${id}`);
      const data = await res.json();
      if (data.success && data.pipeline) {
        setNodes(data.pipeline.nodes || []);
        setEdges(data.pipeline.edges || []);
        setShowHistory(false);
        setResults(null);
        setError(null);
        setStepMode(false);
        setExecutionPlan([]);
        setExecutionStep(0);
        setExecutingNodeId(null);
        clearAutosave();
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

  const fileInputRef = useRef(null);
  const [importSuccess, setImportSuccess] = useState(null);

  const exportPipeline = () => {
    if (!nodes.length) return;
    const name = pipelineName || 'pipeline';
    const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const data = {
      name: name,
      description: `PipeMind pipeline exported at ${ts}`,
      nodes,
      edges,
      createdAt: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `pipeline-${name}-${ts}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      try {
        const data = JSON.parse(evt.target.result);
        if (!data.nodes || !data.edges) {
          setImportSuccess('error');
          setTimeout(() => setImportSuccess(null), 3000);
          return;
        }
        setNodes(data.nodes);
        setEdges(data.edges);
        if (data.name) setPipelineName(data.name);
        setResults(null);
        setError(null);
        let maxId = 0;
        for (const n of (data.nodes || [])) {
          const num = parseInt(n.id.replace('node_', ''));
          if (num > maxId) maxId = num;
        }
        nodeId = maxId;
        lastPlacedRef.current = null;
        setImportSuccess('success');
        setTimeout(() => setImportSuccess(null), 3000);
      } catch (err) {
        setImportSuccess('error');
        setTimeout(() => setImportSuccess(null), 3000);
      }
    };
    reader.readAsText(file);
    // Reset input so same file can be re-imported
    e.target.value = '';
  };

  const clearCanvas = () => {
    setNodes([]);
    setEdges([]);
    setResults(null);
    setError(null);
    setStepMode(false);
    setExecutionPlan([]);
    setExecutionStep(0);
    setExecutingNodeId(null);
    clearAutosave();
    nodeId = 0;
    lastPlacedRef.current = null;
  };

  const isStepComplete = stepMode && executionStep >= executionPlan.length;

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
          <button
            onClick={exportPipeline}
            disabled={nodes.length === 0}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 disabled:text-gray-600 rounded-lg transition-colors flex items-center gap-1"
          >
            {t('app.export')}
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors flex items-center gap-1"
          >
            {t('app.import')}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            onChange={handleImport}
          />
          <span className="w-px h-6 bg-gray-800 mx-1"></span>
          <button
            onClick={clearCanvas}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            {t('app.clear')}
          </button>
          {!stepMode && (
            <button
              onClick={runInit}
              disabled={running || nodes.length === 0}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-emerald-700 hover:bg-emerald-600 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
            >
              <span>▶ {t('step.title')}</span>
            </button>
          )}
          <button
            onClick={runAll}
            disabled={running || nodes.length === 0}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
          >
            <span>{running ? t('app.running') : t('app.run')}</span>
          </button>
        </div>
      </header>

      {/* Import success/error toast */}
      {importSuccess && (
        <div className={`flex items-center justify-center gap-2 px-4 py-2 text-sm ${
          importSuccess === 'success' ? 'bg-emerald-600/20 text-emerald-300 border-b border-emerald-500/30' : 'bg-red-600/20 text-red-300 border-b border-red-500/30'
        }`}>
          {importSuccess === 'success' ? '✅ ' + t('app.import.success') : '❌ ' + t('app.import.error')}
        </div>
      )}

      {/* Autosave Recovery Banner */}
      {showRestoreBanner && (
        <div className="autosave-banner">
          <span>{t('autosave.banner')}</span>
          <div className="flex items-center gap-2">
            <button onClick={handleRestore} className="px-3 py-1 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white rounded transition-colors">
              {t('autosave.restore')}
            </button>
            <button onClick={handleDiscard} className="px-3 py-1 text-xs font-medium bg-gray-600 hover:bg-gray-500 text-white rounded transition-colors">
              {t('autosave.discard')}
            </button>
          </div>
        </div>
      )}

      {/* Main */}
      <div className="flex flex-1 overflow-hidden">
        <NodePalette />

        <div className="flex flex-col flex-1">
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
                onNodeClick={onNodeClick}
                onPaneClick={onPaneClick}
                connectionLineStyle={{ stroke: '#6366f1', strokeWidth: 3 }}
                connectionLineType="smoothstep"
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

          {/* Step Mode Status Bar */}
          {stepMode && (
            <div className="step-bar">
              <div className="flex items-center gap-3">
                <span className="text-xs font-medium text-gray-300">
                  {t('step.label')} {Math.min(executionStep + 1, executionPlan.length)}{t('step.of')}{executionPlan.length}
                </span>
                <div className="step-progress">
                  <div
                    className="step-progress-fill"
                    style={{ width: `${(executionStep / executionPlan.length) * 100}%` }}
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                {isStepComplete ? (
                  <>
                    <span className="text-xs text-emerald-400">{t('step.finish')}</span>
                    <button
                      onClick={() => { setStepMode(false); setExecutionPlan([]); setExecutionStep(0); }}
                      className="px-3 py-1 text-xs font-medium bg-gray-700 hover:bg-gray-600 text-gray-300 rounded transition-colors"
                    >
                      {t('dialog.save.cancel')}
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={runStep}
                      disabled={running}
                      className="flex items-center gap-1 px-3 py-1 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded transition-colors"
                    >
                      {running ? t('app.running') : t('step.next')}
                    </button>
                    <button
                      onClick={() => {
                        setStepMode(false);
                        setExecutionPlan([]);
                        setExecutionStep(0);
                        runAll();
                      }}
                      disabled={running}
                      className="px-3 py-1 text-xs font-medium bg-gray-700 hover:bg-gray-600 disabled:text-gray-600 text-gray-300 rounded transition-colors"
                    >
                      {t('step.runAll')}
                    </button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right: Config Sidebar or Results Panel or Tips */}
        {/* Floating history tab */}
        <button
          onClick={() => setShowHistory(s => !s)}
          className={`absolute right-4 top-20 z-40 px-3 py-2 text-sm rounded-lg shadow-lg transition-colors ${
            showHistory ? 'bg-indigo-600 text-white border border-indigo-500' : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700 border border-gray-700'
          }`}
          style={{ position: 'fixed', right: showHistory ? '436px' : '16px' }}
        >
          {t('app.history')}
        </button>
        {showHistory ? (
          <HistoryPanel t={t} />
        ) : selectedNode ? (
          <ConfigSidebar selectedNode={selectedNode} updateNodeData={updateNodeData} t={t} />
        ) : results ? (
          <aside className="w-80 border-l border-gray-800 bg-gray-900/50 flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
              <h2 className="text-sm font-medium text-gray-400">{t('panel.results')}</h2>
              <button onClick={exportResults} className="text-xs text-gray-500 hover:text-emerald-400 transition-colors">
                {t('panel.export')}
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 text-sm space-y-3">
              <div className="flex gap-1 flex-wrap mb-3">
                <button onClick={() => setResultTab('all')} className={`px-2 py-1 text-xs rounded ${resultTab === 'all' ? 'bg-indigo-600/30 text-indigo-300' : 'text-gray-500 hover:text-gray-300'}`}>
                  {t('panel.all')}
                </button>
                {Object.entries(results).map(([id, r]) => (
                  <button key={id} onClick={() => setResultTab(id)} className={`px-2 py-1 text-xs rounded ${resultTab === id ? 'bg-indigo-600/30 text-indigo-300' : 'text-gray-500 hover:text-gray-300'}`}>
                    {r.label}
                  </button>
                ))}
              </div>
              {resultTab === 'all' ? (
                Object.entries(results).map(([id, r]) => (
                  <ResultCard key={id} id={id} result={r} t={t} />
                ))
              ) : (
                results[resultTab] && <ResultCard id={resultTab} result={results[resultTab]} t={t} expanded />
              )}
            </div>
          </aside>
        ) : (
          <aside className="w-80 border-l border-gray-800 bg-gray-900/50 flex flex-col">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
              <h2 className="text-sm font-medium text-gray-400">
                {error ? t('panel.error') : t('panel.tips')}
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto p-4 text-sm space-y-3">
              {error ? (
                <div className="p-3 bg-red-900/30 border border-red-800/50 rounded-lg text-red-300 text-xs whitespace-pre-wrap">
                  {error}
                </div>
              ) : (
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
            </div>
          </aside>
        )}
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

function ResultCard({ id, result, t, expanded }) {
  const [isExpanded, setIsExpanded] = useState(!!expanded);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(result.output || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const typeColors = {
    search: 'border-l-cyan-500',
    llm: 'border-l-purple-500',
    review: 'border-l-amber-500',
    kb: 'border-l-blue-500',
    mindmap: 'border-l-emerald-500',
    memory: 'border-l-violet-500',
    output: 'border-l-emerald-500',
  };

  return (
    <div className={`bg-gray-800/50 rounded-lg border border-gray-700/50 overflow-hidden border-l-4 ${typeColors[result.type] || 'border-l-gray-500'}`}>
      <div className="flex items-center justify-between px-3 py-2 bg-gray-800/80 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-300">{result.label}</span>
          <span className="text-xs text-gray-600">{result.type}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">{result.duration}{t('node.duration')}</span>
          <button onClick={handleCopy} className="text-xs text-gray-500 hover:text-emerald-400 transition-colors px-1">
            {copied ? '✅' : '📋'}
          </button>
          <button onClick={() => setIsExpanded(!isExpanded)} className="text-xs text-gray-500 hover:text-gray-300">
            {isExpanded ? '▲' : '▼'}
          </button>
        </div>
      </div>
      {isExpanded && (
        <pre className="p-3 text-xs text-gray-400 whitespace-pre-wrap break-all max-h-96 overflow-y-auto">
          {String(result.output || '').slice(0, 10000)}
        </pre>
      )}
      {!isExpanded && (
        <pre className="p-3 text-xs text-gray-400 whitespace-pre-wrap break-all max-h-24 overflow-y-hidden truncate">
          {String(result.output || '').slice(0, 200)}
        </pre>
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
