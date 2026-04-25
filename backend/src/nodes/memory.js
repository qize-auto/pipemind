import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import os from 'os';
import mempalace from '../mempalace-daemon.js';

const WORKSPACE = os.homedir() + '/.qclaw/workspace';

/**
 * Memory node — dual-mode memory search
 *   mode='search' (default): lightning-fast file keyword search (34ms)
 *   mode='semantic': MemPalace persistent daemon (200ms, semantic)
 *   mode='status': MemPalace daemon status
 */
export async function memory(data, inputs, _results) {
  const mode = data.mode || 'search';

  try {
    switch (mode) {
      case 'semantic': return await semanticSearch(data, inputs);
      case 'status':   return await mempalaceStatus();
      default:         return await keywordSearch(data, inputs);
    }
  } catch (err) {
    return '❌ 记忆节点错误: ' + err.message;
  }
}

/* ---------- Semantic search (persistent daemon, ~200ms) ---------- */
async function semanticSearch(data, inputs) {
  const query = data.query || (inputs && inputs[0]) || '';
  if (!query) return '⚠️ 请输入搜索关键词';

  const limit = data.n_results || 3;
  const wing = data.wing || '';
  const room = data.room || '';

  try {
    const result = await mempalace.search(query, limit, wing, room);

    if (result.type === 'error' || result.type === 'fatal') {
      return '⚠️ 语义搜索失败: ' + (result.message || 'unknown');
    }

    const items = result.results || [];
    if (items.length === 0) {
      return '🔍 语义搜索「' + query + '」未找到结果';
    }

    let output = '🧠 语义搜索「' + query + '」找到 ' + items.length + ' 个结果\n\n';
    for (const r of items) {
      const scorePct = (r.score * 100).toFixed(0);
      const source = r.source || r.room || 'unknown';
      output += '📄 ' + source + ' (相似度: ' + scorePct + '%)\n';
      if (r.snippet) output += '  ' + r.snippet.replace(/\n/g, ' ').slice(0, 250) + '\n\n';
    }
    return output.trim();
  } catch (err) {
    return '⚠️ 语义搜索失败: ' + err.message;
  }
}

/* ---------- Lightning keyword search (34ms) ---------- */
async function keywordSearch(data, inputs) {
  const query = data.query || (inputs && inputs[0]) || '';
  if (!query) return '⚠️ 请输入搜索关键词';

  const results = searchFiles(query, WORKSPACE, data.n_results || 5);
  return formatResults(results, query);
}

/* ---------- MemPalace daemon status ---------- */
async function mempalaceStatus() {
  return mempalace.ready
    ? '🧠 MemPalace 就绪 🟢'
    : '🧠 MemPalace 启动中… 🔴';
}

/* ---------- File-based keyword search ---------- */
function searchFiles(query, dir, maxResults) {
  const keywords = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (keywords.length === 0) return [];

  const results = [];
  const root = path.resolve(dir);
  let fileCount = 0;
  function walk(d) {
    if (results.length >= maxResults || fileCount >= 200) return;
    try {
      const entries = fs.readdirSync(d, { withFileTypes: true });
      for (const entry of entries) {
        if (results.length >= maxResults) break;
        const fp = path.join(d, entry.name);
        if (entry.isDirectory() && !entry.name.startsWith('node_modules') && !entry.name.startsWith('.git') && !entry.name.startsWith('dist')) {
          walk(fp);
        } else if (entry.isFile() && /\.(md|txt|json|js|jsx|ts|tsx|py|yaml|yml|cfg|conf|env|css|html)$/i.test(entry.name)) {
          fileCount++;
          try {
            const content = fs.readFileSync(fp, 'utf-8');
            const lines = content.split('\n');
            let score = 0;
            const matchedLines = [];
            for (let i = 0; i < lines.length; i++) {
              const lowerLine = lines[i].toLowerCase();
              const matchCount = keywords.filter(k => lowerLine.includes(k)).length;
              if (matchCount > 0) {
                score += matchCount;
                matchedLines.push({ line: i + 1, text: lines[i].trim().slice(0, 120) });
              }
            }
            if (score > 0) {
              const rel = path.relative(root, fp);
              results.push({
                file: rel,
                score,
                snippet: matchedLines.slice(0, 3).map(l => l.text).join(' | ').slice(0, 200),
                matchedLines: matchedLines.slice(0, 5),
              });
            }
          } catch { /* skip */ }
        }
      }
    } catch { /* skip */ }
  }
  walk(root);
  results.sort((a, b) => b.score - a.score);
  return results.slice(0, maxResults);
}

function formatResults(results, query) {
  if (results.length === 0) {
    return '🔍 关键词搜索「' + query + '」未找到相关文件';
  }
  let output = '🔍 关键词搜索「' + query + '」找到 ' + results.length + ' 个文件\n\n';
  for (const r of results) {
    output += '📄 ' + r.file + ' (score: ' + r.score + ')\n';
    output += '  ' + r.snippet + '\n\n';
  }
  return output.trim();
}
