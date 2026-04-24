import express from 'express';
import cors from 'cors';
import { runWorkflow } from './engine.js';

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

// ── Health check ──
app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok', version: '0.1.0' });
});

// ── Execute workflow ──
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

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`🔧 PipeMind Engine running on http://localhost:${PORT}`);
});
