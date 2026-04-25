import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { runWorkflow, getExecutionPlan, runSingleNode, pipelineEvents } from './engine.js';
import { getRun, getNodeExecutions, createRun, completeRun } from './db.js';
import * as mcpManager from './mcp-manager.js';
import { getDb } from './db.js';
import mempalace from './mempalace-daemon.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PIPELINES_DIR = path.join(__dirname, '..', 'pipelines');
const EXAMPLES_DIR = path.join(PIPELINES_DIR, 'examples');

// Ensure pipeline storage dirs
if (!fs.existsSync(PIPELINES_DIR)) fs.mkdirSync(PIPELINES_DIR, { recursive: true });
if (!fs.existsSync(EXAMPLES_DIR)) fs.mkdirSync(EXAMPLES_DIR, { recursive: true });

// SSE client set
const sseClients = new Set();

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// -- Health check --
// Start MemPalace daemon (background, non-blocking)
mempalace.start();

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', version: '0.1.0', mempalace: mempalace.ready });
});

function saveRunToDb(pipelineName, nodes, edges, status, results) {
  try {
    const db = getDb();
    const id = `run_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    const startedAt = new Date().toISOString();
    const completedAt = status !== 'running' ? new Date().toISOString() : null;
    const nodeCount = nodes.length;
    const stmt = db.prepare(`
      INSERT INTO pipeline_runs (id, pipeline_name, nodes_json, edges_json, status, started_at, completed_at, results_json, node_count)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    stmt.run(id, pipelineName || 'unnamed', JSON.stringify(nodes), JSON.stringify(edges), status, startedAt, completedAt, JSON.stringify(results || {}), nodeCount);
    return id;
  } catch (err) {
    console.error('[PipeMind] Failed to save run:', err.message);
    return null;
  }
}

// -- Execute workflow --
app.post('/api/run', async (req, res) => {
  const { nodes = [], edges = [], pipelineName } = req.body;

  if (!nodes.length) {
    return res.status(400).json({ error: 'No nodes in workflow' });
  }

  try {
    // Create run record
    const runId = createRun(pipelineName || 'unnamed', nodes, edges);

    // Run with observability wrappers
    const origOnNodeStart = pipelineEvents.listeners('node:start');
    const origOnNodeError = pipelineEvents.listeners('node:error');

    // Set up run-scoped broadcast
    const broadcast = (eventType) => (data) => {
      const evt = { type: eventType, runId, ...data };
      const msg = 'data: ' + JSON.stringify(evt) + String.fromCharCode(0x0a, 0x0a);
      for (const client of sseClients) {
        client.write(msg);
      }
    };
    const onStart = broadcast('node:start');
    const onComplete = broadcast('node:complete');
    const onError = broadcast('node:error');
    const onPipelineComplete = broadcast('pipeline:complete');

    pipelineEvents.on('node:start', onStart);
    pipelineEvents.on('node:complete', onComplete);
    pipelineEvents.on('node:error', onError);
    pipelineEvents.on('pipeline:complete', onPipelineComplete);

    const results = await runWorkflow(nodes, edges);
    completeRun(runId, results);

    pipelineEvents.off('node:start', onStart);
    pipelineEvents.off('node:complete', onComplete);
    pipelineEvents.off('node:error', onError);
    pipelineEvents.off('pipeline:complete', onPipelineComplete);

    res.json({ success: true, results, runId });
  } catch (err) {
    console.error('[PipeMind] Workflow error:', err.message);
    // We can't easily get runId here if createRun failed
    res.status(500).json({ error: err.message, stack: err.stack?.split('\n').slice(0, 3).join('\n') });
  }
});

// -- Initialize step-by-step execution (return plan, don't execute) --
app.post('/api/run-init', async (req, res) => {
  const { nodes = [], edges = [] } = req.body;

  if (!nodes.length) {
    return res.status(400).json({ error: 'No nodes in workflow' });
  }

  try {
    const plan = getExecutionPlan(nodes, edges);
    res.json({ success: true, plan, nodeCount: plan.length });
  } catch (err) {
    console.error('[PipeMind] Init error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// -- Execute one step --
app.post('/api/run-step', async (req, res) => {
  const { nodes = [], edges = [], nodeId, resultsSoFar = {} } = req.body;

  if (!nodeId) {
    return res.status(400).json({ error: 'nodeId is required' });
  }

  try {
    const result = await runSingleNode(nodeId, nodes, edges, resultsSoFar);
    const results = { ...resultsSoFar, [nodeId]: result };
    res.json({ success: true, nodeId, result, results });
  } catch (err) {
    console.error('[PipeMind] Step error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// -- Pipeline CRUD --

// List saved pipelines
app.get('/api/pipelines', (_req, res) => {
  try {
    const files = fs.readdirSync(PIPELINES_DIR).filter(f => f.endsWith('.json') && f !== 'index.json');
    const pipelines = files.map(f => {
      const filePath = path.join(PIPELINES_DIR, f);
      const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      const stats = fs.statSync(filePath);
      return {
        id: f.replace('.json', ''),
        name: data.name || f.replace('.json', ''),
        createdAt: stats.birthtime,
        updatedAt: stats.mtime,
        nodeCount: data.nodes?.length || 0,
      };
    });
    res.json({ success: true, pipelines });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Save pipeline
app.post('/api/pipelines', (req, res) => {
  try {
    const { id, name, nodes, edges } = req.body;
    const pipelineId = id || `pipeline_${Date.now()}`;
    const data = { id: pipelineId, name: name || pipelineId, nodes, edges, savedAt: new Date().toISOString() };
    fs.writeFileSync(path.join(PIPELINES_DIR, `${pipelineId}.json`), JSON.stringify(data, null, 2), 'utf-8');
    res.json({ success: true, id: pipelineId });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// List example templates
app.get('/api/pipelines/examples', (_req, res) => {
  try {
    const files = fs.readdirSync(EXAMPLES_DIR).filter(f => f.endsWith('.json'));
    const examples = files.map(f => {
      const data = JSON.parse(fs.readFileSync(path.join(EXAMPLES_DIR, f), 'utf-8'));
      return {
        id: f.replace('.json', ''),
        name: data.name || f.replace('.json', ''),
        description: data.description || '',
        nodeCount: data.nodes?.length || 0,
      };
    });
    res.json({ success: true, examples });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Load pipeline (or example)
app.get('/api/pipelines/:id', (req, res) => {
  try {
    const directPath = path.join(PIPELINES_DIR, `${req.params.id}.json`);
    const examplePath = path.join(EXAMPLES_DIR, `${req.params.id}.json`);

    let filePath = null;
    if (fs.existsSync(directPath)) filePath = directPath;
    else if (fs.existsSync(examplePath)) filePath = examplePath;

    if (!filePath) return res.status(404).json({ error: 'Pipeline not found' });

    const data = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    res.json({ success: true, pipeline: data });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Delete pipeline
app.delete('/api/pipelines/:id', (req, res) => {
  try {
    const filePath = path.join(PIPELINES_DIR, `${req.params.id}.json`);
    if (!fs.existsSync(filePath)) return res.status(404).json({ error: 'Pipeline not found' });
    fs.unlinkSync(filePath);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// -- Run History CRUD --

// Save a run record
app.post('/api/runs', (req, res) => {
  try {
    const { pipelineName, nodes, edges, status, results } = req.body;
    const runId = saveRunToDb(pipelineName, nodes, edges, status || 'unknown', results || {});
    res.json({ success: true, runId });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// List recent runs
// SSE event stream (real-time pipeline execution events)
app.get('/api/stream/events', (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'X-Accel-Buffering': 'no',
  });
  res.write('data: {}' + String.fromCharCode(0x0a, 0x0a));

  sseClients.add(res);
  const keepAlive = setInterval(() => res.write(':keepalive\n\n'), 15000);

  req.on('close', () => {
    sseClients.delete(res);
    clearInterval(keepAlive);
  });
});

// Run detail (with node executions)
app.get('/api/runs/:id', (req, res) => {
  try {
    const run = getRun(req.params.id);
    if (!run) return res.status(404).json({ error: 'Run not found' });
    const nodes = getNodeExecutions(req.params.id);
    res.json({ success: true, run, nodes });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/runs', (_req, res) => {
  try {
    const db = getDb();
    const rows = db.prepare('SELECT id, pipeline_name, status, started_at, completed_at, node_count FROM pipeline_runs ORDER BY started_at DESC LIMIT 20').all();
    const runs = rows.map(r => ({
      id: r.id,
      pipelineName: r.pipeline_name,
      status: r.status,
      startedAt: r.started_at,
      completedAt: r.completed_at,
      nodeCount: r.node_count,
    }));
    res.json({ success: true, runs });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get single run details
app.get('/api/runs/:id', (req, res) => {
  try {
    const db = getDb();
    const row = db.prepare('SELECT * FROM pipeline_runs WHERE id = ?').get(req.params.id);
    if (!row) return res.status(404).json({ error: 'Run not found' });
    res.json({
      success: true,
      run: {
        id: row.id,
        pipelineName: row.pipeline_name,
        nodes: JSON.parse(row.nodes_json || '[]'),
        edges: JSON.parse(row.edges_json || '[]'),
        status: row.status,
        startedAt: row.started_at,
        completedAt: row.completed_at,
        results: JSON.parse(row.results_json || '{}'),
        nodeCount: row.node_count,
      },
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Delete a run
app.delete('/api/runs/:id', (req, res) => {
  try {
    const db = getDb();
    const result = db.prepare('DELETE FROM pipeline_runs WHERE id = ?').run(req.params.id);
    if (result.changes === 0) return res.status(404).json({ error: 'Run not found' });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// -- Export results --
app.post('/api/export', (req, res) => {
  try {
    const { results } = req.body;
    if (!results) return res.status(400).json({ error: 'No results to export' });

    let content = '# PipeMind 运行结果\n\n';
    content += `导出时间: ${new Date().toISOString()}\n\n---\n\n`;

    for (const [id, r] of Object.entries(results)) {
      content += `## ${r.label} (${r.type})\n\n`;
      content += `- 节点ID: ${id}\n`;
      content += `- 耗时: ${r.duration}ms\n\n`;
      content += '```\n';
      content += String(r.output || '').slice(0, 5000);
      content += '\n```\n\n---\n\n';
    }

    const filename = `pipemind-export-${Date.now()}.md`;
    const outputPath = path.join(PIPELINES_DIR, filename);
    fs.writeFileSync(outputPath, content, 'utf-8');

    res.json({ success: true, filename, content });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});


// -- MCP Server Management --
app.post('/api/mcp/connect', async (req, res) => {
  try {
    const { serverId, command, args, env, sseUrl } = req.body;
    if (sseUrl) {
      const result = await mcpManager.connectSSE(serverId, sseUrl);
      return res.json({ success: true, ...result });
    }
    const result = await mcpManager.connectStdio(serverId, command, args, env);
    res.json({ success: true, ...result });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/mcp/disconnect', async (req, res) => {
  try {
    const { serverId } = req.body;
    await mcpManager.disconnect(serverId);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/mcp/status', (_req, res) => {
  try {
    const status = mcpManager.getStatus();
    res.json({ success: true, connections: status });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/mcp/tools/:serverId', async (req, res) => {
  try {
    const tools = await mcpManager.listTools(req.params.serverId);
    res.json({ success: true, tools });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// -- Agent API endpoints (小李集成层) --

// Quick memory search (no pipeline, direct)
app.post('/api/agent/memory', async (req, res) => {
  try {
    const { query, n_results = 5, wing, room } = req.body;
    if (!query) return res.status(400).json({ error: 'query required' });
    const result = await mempalace.search(query, n_results, wing, room);
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Smart solve: routes task to the right pipeline
app.post('/api/agent/solve', async (req, res) => {
  try {
    const { task, mode = 'auto' } = req.body;
    if (!task) return res.status(400).json({ error: 'task required' });

    const taskLower = task.toLowerCase();

    // Mode detection
    const isMemory = mode === 'memory' || taskLower.includes('记忆') || taskLower.includes('记得');
    const isResearch = mode === 'research' || (taskLower.includes('搜索') && !taskLower.includes('记忆')) || (taskLower.includes('查') && !taskLower.includes('记忆')) || taskLower.includes('分析');

    if (isMemory) {
      // Memory search — use raw task as query (semantic search handles full sentences)
      const result = await mempalace.search(task, 8);
      return res.json({ mode: 'memory', task, result });
    }

    if (isResearch) {
      // Build and run a search pipeline
      // For now: just return structured response with what would run
      return res.json({
        mode: 'research',
        task,
        message: 'Research pipeline not yet implemented — use manual pipeline for now',
        hint: 'POST /api/run with search+llm+review nodes'
      });
    }

    // Default: direct LLM reasoning
    return res.json({
      mode: 'reason',
      task,
      message: 'LLM reasoning not yet wired as direct endpoint — use pipelines',
      hint: 'POST /api/run with llm node'
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Daemon status
app.get('/api/agent/status', (_req, res) => {
  res.json({
    ready: mempalace.ready,
    processAlive: !!mempalace.process,
    cacheSize: mempalace.cache.size,
    pendingSearches: mempalace.pending.size
  });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`🔧 PipeMind Engine running on http://localhost:${PORT}`);
});
