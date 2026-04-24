import { useState, useCallback, useRef, useEffect } from 'react';
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
import { SearchNode, LLMNode, OutputNode, ReviewNode } from './nodes/index.js';

const nodeTypes = {
  search: SearchNode,
  llm: LLMNode,
  output: OutputNode,
  review: ReviewNode,
};

const initialNodes = [];

const initialEdges = [];

let nodeId = 0;

export default function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const reactFlowWrapper = useRef(null);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
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
    },
    [reactFlowInstance, setNodes]
  );

  const getDefaultLabel = (type) => {
    const labels = { search: '搜索', llm: 'LLM 处理', output: '输出', review: '审查' };
    return labels[type] || type;
  };

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
      // Highlight executed nodes
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

  const clearCanvas = () => {
    setNodes([]);
    setEdges([]);
    setResults(null);
    setError(null);
    nodeId = 0;
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🔧</span>
          <h1 className="text-lg font-semibold text-white tracking-tight">PipeMind</h1>
          <span className="px-2 py-0.5 text-xs bg-indigo-600/20 text-indigo-300 rounded-full border border-indigo-500/30">
            v0.1 MVP
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearCanvas}
            className="px-3 py-1.5 text-sm text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            清空
          </button>
          <button
            onClick={runWorkflow}
            disabled={running || nodes.length === 0}
            className="flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
          >
            <span>{running ? '⏳ 运行中...' : '▶ 运行'}</span>
          </button>
        </div>
      </header>

      {/* Main */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Palette */}
        <NodePalette />

        {/* Center: Canvas */}
        <div className="flex-1" ref={reactFlowWrapper}>
          <ReactFlowProvider>
            <ReactFlow
              nodes={nodes}
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
          <h2 className="text-sm font-medium text-gray-400 px-4 py-3 border-b border-gray-800">
            {results ? '📋 运行结果' : error ? '❌ 错误' : '💡 提示'}
          </h2>
          <div className="flex-1 overflow-y-auto p-4 text-sm space-y-3">
            {!results && !error && (
              <div className="text-gray-500 space-y-2">
                <p>从左侧拖拽节点到画布</p>
                <p>连接节点形成工作流</p>
                <p>点击「运行」执行</p>
                <div className="mt-4 p-3 bg-gray-800/50 rounded-lg border border-gray-700/50">
                  <p className="text-gray-400 text-xs font-medium mb-2">快速开始:</p>
                  <ol className="text-gray-500 text-xs space-y-1 list-decimal list-inside">
                    <li>拖入 搜索节点</li>
                    <li>连接到 LLM 节点</li>
                    <li>连接到 输出节点</li>
                    <li>点击运行</li>
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
                  <span className="text-xs text-gray-500">{r.duration}ms</span>
                </div>
                <pre className="p-3 text-xs text-gray-400 whitespace-pre-wrap break-all max-h-48 overflow-y-auto">
                  {String(r.output || '').slice(0, 2000)}
                </pre>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </div>
  );
}
