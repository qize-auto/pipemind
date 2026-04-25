/**
 * mempalace-daemon.js — Persistent MemPalace Python daemon manager
 * 
 * Architecture:
 *   Node.js (this) ←stdin/stdout→ Python (mempalace_server.py)
 *   - Python loads ChromaDB + model once at startup
 *   - Each search: send JSON line → receive JSON line
 *   - ≈200ms per query vs 7s per CLI spawn
 * 
 * Cache:
 *   - In-memory LRU: TTL 5min, max 32 entries
 *   - Same query ≈instant (cache hit)
 */

import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SERVER_SCRIPT = path.join(__dirname, '..', 'mempalace_server.py');
const PING_INTERVAL = 30_000;  // Keep-alive every 30s

// ---------- LRU Cache ----------
class LRUCache {
  constructor(maxSize = 32, ttlMs = 300_000) {
    this.maxSize = maxSize;
    this.ttlMs = ttlMs;
    this.map = new Map();
  }

  _makeKey(query, n_results, wing, room) {
    return `${query}|${n_results}|${wing || ''}|${room || ''}`;
  }

  get(query, n_results, wing, room) {
    const key = this._makeKey(query, n_results, wing, room);
    const entry = this.map.get(key);
    if (!entry) return null;
    if (Date.now() - entry.ts > this.ttlMs) {
      this.map.delete(key);
      return null;
    }
    // Move to end (most recently used)
    this.map.delete(key);
    this.map.set(key, entry);
    return entry.data;
  }

  set(query, n_results, wing, room, data) {
    const key = this._makeKey(query, n_results, wing, room);
    this.map.delete(key);
    this.map.set(key, { ts: Date.now(), data });
    if (this.map.size > this.maxSize) {
      const oldest = this.map.keys().next().value;
      this.map.delete(oldest);
    }
  }

  get size() { return this.map.size; }
}

// ---------- Daemon ----------
class MemPalaceDaemon {
  constructor() {
    this.process = null;
    this.pending = new Map();    // pendingId → { resolve, reject, timer }
    this.nextId = 1;
    this.cache = new LRUCache();
    this.buffer = '';            // partial line buffer
    this.ready = false;
    this.pingTimer = null;
    this._onReadyResolve = null;
    this._readyPromise = null;
    this.lastQueryTime = Date.now();
    this.idleTimer = null;
    this.IDLE_TIMEOUT = 300_000; // 5min idle before killing daemon
  }

  start() {
    if (this.process) return;

    this._readyPromise = new Promise((resolve) => {
      this._onReadyResolve = resolve;
    });

    this.process = spawn('python', [SERVER_SCRIPT], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', ANONYMIZED_TELEMETRY: 'NO' }
    });

    this.process.stdout.on('data', (chunk) => {
      this.buffer += chunk.toString('utf-8');
      this._processLines();
    });

    this.process.stderr.on('data', (chunk) => {
      // ChromaDB logs to stderr — silent
    });

    this.process.on('exit', (code, signal) => {
      console.log(`[mempalace] daemon exited (code=${code}, signal=${signal})`);
      this.ready = false;
      if (this.pingTimer) clearInterval(this.pingTimer);

      // Reject all pending
      for (const [id, entry] of this.pending) {
        clearTimeout(entry.timer);
        entry.reject(new Error('mempalace daemon died'));
      }
      this.pending.clear();

      // Auto-restart
      this.process = null;
      setTimeout(() => this.start(), 1000);
    });
  }

  _processLines() {
    const lines = this.buffer.split('\n');
    // Keep last partial line in buffer
    this.buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const msg = JSON.parse(line);
        this._handleMessage(msg);
      } catch (e) {
        // Ignore non-JSON output (e.g. ChromaDB startup logs)
      }
    }
  }

  _handleMessage(msg) {
    if (msg.type === 'ready') {
      this.ready = true;
      const collCount = msg.collection_count ?? msg.count ?? msg.collections?.length ?? '?';
      console.log(`[mempalace] daemon ready (${collCount} collections, ${msg.palace})`);
      if (this._onReadyResolve) {
        this._onReadyResolve();
        this._onReadyResolve = null;
      }
      // Start keep-alive ping
      this.pingTimer = setInterval(() => this._ping(), PING_INTERVAL);
      return;
    }

    if (msg.type === 'fatal') {
      console.error(`[mempalace] FATAL: ${msg.error}`);
      if (this._onReadyResolve) {
        this._onReadyResolve();
        this._onReadyResolve = null;
      }
      return;
    }

    if (msg.type === 'results' || msg.type === 'error') {
      // Match to pending request by query
      // Since queries are processed in order, use ordering
      const id = this._findPending();
      if (id !== null) {
        const entry = this.pending.get(id);
        if (entry) {
          clearTimeout(entry.timer);
          this.pending.delete(id);
          entry.resolve(msg);
        }
      }
    }
  }

  _findPending() {
    // Return the oldest pending ID
    return this.pending.keys().next().value || null;
  }

  _scheduleIdleCheck() {
    if (this.idleTimer) clearTimeout(this.idleTimer);
    this.idleTimer = setTimeout(() => this._killOnIdle(), this.IDLE_TIMEOUT);
  }

  _killOnIdle() {
    this.idleTimer = null;
    if (!this.process) return;
    const idleMs = Date.now() - this.lastQueryTime;
    if (idleMs >= this.IDLE_TIMEOUT && this.pending.size === 0) {
      console.log(`[mempalace] idle ${Math.round(idleMs/1000)}s — stopping daemon (restart on next query)`);
      if (this.pingTimer) clearInterval(this.pingTimer);
      if (this.process) {
        this.process.kill();
        this.process = null;
      }
      this.ready = false;
    } else if (this.pending.size > 0) {
      this._scheduleIdleCheck();
    }
  }

  _ping() {
    // Ping only if within idle window
    if (this.process && this.process.stdin.writable && Date.now() - this.lastQueryTime < this.IDLE_TIMEOUT) {
      this.process.stdin.write(JSON.stringify({ query: '', n_results: 1, _ping: true }) + '\n');
    }
  }

  async search(query, n_results = 3, wing = '', room = '') {
    if (!query) return { type: 'error', message: 'query required' };

    // Touch last query time and cancel idle timer
    this.lastQueryTime = Date.now();
    if (this.idleTimer) clearTimeout(this.idleTimer);

    // 1. Check cache
    const cached = this.cache.get(query, n_results, wing, room);
    if (cached) {
      console.log(`[mempalace] cache hit: "${query.slice(0, 30)}" (${cached.results.length} results)`);
      this._scheduleIdleCheck();
      return cached;
    }

    // 2. Auto-restart daemon if killed due to idle
    if (!this.process) {
      console.log('[mempalace] auto-restarting daemon for query');
      this.start();
    }
    if (!this.ready) {
      await this._readyPromise;
      // Still not ready? Check for fatal
      if (!this.ready) {
        return { type: 'error', message: 'mempalace daemon failed to start' };
      }
    }

    // 3. Send query
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error('mempalace search timeout (15s)'));
      }, 15_000);

      this.pending.set(id, { resolve, reject, timer });

      try {
        this.process.stdin.write(JSON.stringify({
          query, n_results, wing, room
        }) + '\n');
      } catch (e) {
        clearTimeout(timer);
        this.pending.delete(id);
        reject(e);
      }
    }).then((result) => {
      // 4. Cache successful results
      if (result.type === 'results' && result.results.length > 0) {
        this.cache.set(query, n_results, wing, room, result);
      }
      return result;
    }).finally(() => {
      this._scheduleIdleCheck();
    });
  }

  stop() {
    if (this.idleTimer) clearTimeout(this.idleTimer);
    this.idleTimer = null;
    if (this.pingTimer) clearInterval(this.pingTimer);
    this.pingTimer = null;
    if (this.process) {
      this.process.kill();
      this.process = null;
    }
    this.ready = false;
  }
}

// Singleton
const daemon = new MemPalaceDaemon();

export { daemon as default, MemPalaceDaemon };
