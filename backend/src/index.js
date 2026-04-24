import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { runWorkflow, getExecutionPlan, runSingleNode } from './engine.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PIPELINES_DIR = path.join(__dirname, '..', 'pipelines');
const EXAMPLES_DIR = path.join(PIPELINES_DIR, 'examples');

// Ensure pipeline storage dirs
if (!fs.existsSync(PIPELINES_DIR)) fs.mkdirSync(PIPELINES_DIR, { recursive: true });
if (!fs.existsSync(EXAMPLES_DIR)) fs.mkdirSync(EXAMPLES_DIR, { recursive: true });

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// -- Health check --
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', version: '0.1.0' });
});

// -- Execute workflow --
app.post('/api/run', async (req, res) => {
  const { nodes = [], edges = [] } = req.body;

  if (!nodes.length) {
    return res.status(400).json({ error: 'No nodes in workflow' });
  }

  try {
    const results = await runWorkflow(nodes, edges);
    res.json({ success: true, results });
  } catch (err) {
    console.error('[PipeMind] Workflow error:', err.message);
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

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`🔧 PipeMind Engine running on http://localhost:${PORT}`);
});
