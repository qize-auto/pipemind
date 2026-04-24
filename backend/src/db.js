import { randomUUID } from 'crypto';
import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.resolve(__dirname, '..', 'data');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const DB_PATH = path.join(DATA_DIR, 'pipemind.db');

let db;

export function getDb() {
  if (db) return db;

  db = new Database(DB_PATH);

  // Enable WAL mode for better concurrent performance
  db.pragma('journal_mode = WAL');

  // Create table if not exists
  db.exec(`
    CREATE TABLE IF NOT EXISTS pipeline_runs (
      id TEXT PRIMARY KEY,
      pipeline_name TEXT NOT NULL,
      nodes_json TEXT NOT NULL,
      edges_json TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'running',
      started_at TEXT NOT NULL,
      completed_at TEXT,
      results_json TEXT,
      node_count INTEGER DEFAULT 0
    )
  `);

  db.exec(`
    CREATE TABLE IF NOT EXISTS node_executions (
      id TEXT PRIMARY KEY,
      run_id TEXT NOT NULL,
      node_id TEXT NOT NULL,
      node_type TEXT NOT NULL,
      node_label TEXT,
      status TEXT NOT NULL DEFAULT 'running',
      started_at TEXT NOT NULL,
      completed_at TEXT,
      duration_ms INTEGER,
      output TEXT,
      error TEXT
    )
  `);

  // Index for fast queries by run_id
  db.exec(`CREATE INDEX IF NOT EXISTS idx_node_exec_run ON node_executions(run_id)`);
  db.exec(`CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started ON pipeline_runs(started_at)`);

  return db;
}

export function closeDb() {
  if (db) {
    db.close();
    db = null;
  }
}

export function createRun(pipelineName, nodes, edges) {
  const d = getDb();
  const id = randomUUID();
  const now = new Date().toISOString();
  d.prepare(`INSERT INTO pipeline_runs (id, pipeline_name, nodes_json, edges_json, status, started_at, node_count) VALUES (?, ?, ?, ?, 'running', ?, ?)`)
    .run(id, pipelineName, JSON.stringify(nodes), JSON.stringify(edges), now, nodes?.length || 0);
  return id;
}

export function completeRun(id, results) {
  const d = getDb();
  d.prepare(`UPDATE pipeline_runs SET status = 'completed', completed_at = ?, results_json = ? WHERE id = ?`)
    .run(new Date().toISOString(), JSON.stringify(results), id);
}

export function failRun(id, error) {
  const d = getDb();
  d.prepare(`UPDATE pipeline_runs SET status = 'failed', completed_at = ?, results_json = ? WHERE id = ?`)
    .run(new Date().toISOString(), JSON.stringify({ error }), id);
}

export function insertNodeExecution(runId, nodeId, nodeType, nodeLabel) {
  const d = getDb();
  const id = randomUUID();
  const now = new Date().toISOString();
  d.prepare(`INSERT INTO node_executions (id, run_id, node_id, node_type, node_label, status, started_at) VALUES (?, ?, ?, ?, ?, 'running', ?)`)
    .run(id, runId, nodeId, nodeType, nodeLabel || nodeType, now);
  return id;
}

export function completeNodeExecution(id, output, durationMs) {
  const d = getDb();
  d.prepare(`UPDATE node_executions SET status = 'completed', completed_at = ?, duration_ms = ?, output = ? WHERE id = ?`)
    .run(new Date().toISOString(), durationMs, typeof output === 'string' ? output : JSON.stringify(output), id);
}

export function failNodeExecution(id, errorMsg) {
  const d = getDb();
  d.prepare(`UPDATE node_executions SET status = 'failed', completed_at = ?, error = ? WHERE id = ?`)
    .run(new Date().toISOString(), errorMsg, id);
}

export function getRuns(limit = 20) {
  const d = getDb();
  return d.prepare(`SELECT id, pipeline_name, status, started_at, completed_at, node_count FROM pipeline_runs ORDER BY started_at DESC LIMIT ?`).all(limit);
}

export function getRun(runId) {
  const d = getDb();
  const run = d.prepare(`SELECT * FROM pipeline_runs WHERE id = ?`).get(runId);
  if (run) {
    run.nodes = JSON.parse(run.nodes_json || '[]');
    run.edges = JSON.parse(run.edges_json || '[]');
    run.results = JSON.parse(run.results_json || '{}');
  }
  return run;
}

export function getNodeExecutions(runId) {
  const d = getDb();
  return d.prepare(`SELECT * FROM node_executions WHERE run_id = ? ORDER BY started_at ASC`).all(runId);
}
