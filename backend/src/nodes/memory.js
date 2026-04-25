import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import os from 'os';

const WORKSPACE = os.homedir() + '/.qclaw/workspace';

/**
 * Memory node — dual-mode memory search
 *   mode='search' (default): lightning-fast file keyword search (41ms)
 *   mode='semantic': MemPalace-based semantic search (slower, smarter)
 *   mode='status': check MemPalace status
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
    return '\u274c \u8bb0\u5fc6\u8282\u70b9\u9519\u8bef: ' + err.message;
  }
}

/* ---------- Semantic search via MemPalace ---------- */
async function semanticSearch(data, inputs) {
  const query = data.query || (inputs && inputs[0]) || '';
  if (!query) return '\u26a0\ufe0f \u8bf7\u8f93\u5165\u641c\u7d22\u5173\u952e\u8bcd';

  const limit = data.n_results || 3;
  const wing = data.wing || '';
  const room = data.room || '';

  try {
    let cmd = `mempalace search "${query.replace(/"/g, '\\"')}" --results ${limit}`;
    if (wing) cmd += ` --wing "${wing}"`;
    if (room) cmd += ` --room "${room}"`;

    const output = execSync(cmd, {
      encoding: 'utf-8',
      maxBuffer: 1024 * 100,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    });

    // Parse matches
    const lines = output.split('\n');
    const results = [];
    let current = null;
    let collecting = false;

    for (const line of lines) {
      const match = line.match(/\[(\d+)\]\s+(.+?)\s+\/\s+(.+)/);
      if (match) {
        if (current) results.push(current);
        current = { rank: parseInt(match[1]), wing: match[2].trim(), room: match[3].trim(), snippet: '', source: '' };
        collecting = true;
      } else if (current && collecting) {
        if (line.includes('Source:')) {
          current.source = line.replace(/Source:\s*/g, '').trim();
        } else if (line.includes('Match:')) {
          current.score = parseFloat(line.match(/[\d.]+/)?.[0] || '0');
        } else if (line.trim() && !line.startsWith('\u2500') && !line.startsWith('=')) {
          current.snippet += line.trim() + '\n';
        }
      }
    }
    if (current) results.push(current);

    if (results.length === 0) {
      return '\ud83d\udd0d \u8bed\u4e49\u641c\u7d22\u300c' + query + '\u300d\u672a\u627e\u5230\u7ed3\u679c';
    }

    let output_formatted = '\ud83e\udde0 \u8bed\u4e49\u641c\u7d22\u300c' + query + '\u300d\u627e\u5230 ' + results.length + ' \u4e2a\u7ed3\u679c\n\n';
    for (const r of results) {
      const scorePct = (r.score * 100).toFixed(0);
      output_formatted += '\ud83d\udcc4 ' + (r.source || r.room) + ' (\u76f8\u4f3c\u5ea6: ' + scorePct + '%)\n';
      const snippet = r.snippet.replace(/\n/g, ' ').slice(0, 200);
      if (snippet) output_formatted += '  ' + snippet + '\n\n';
    }
    return output_formatted.trim();
  } catch (err) {
    return '\u26a0\ufe0f \u8bed\u4e49\u641c\u7d22\u5931\u8d25: ' + err.message + '\n（\u8bf7\u786e\u8ba4 \u2764\ufe0f MemPalace \u5df2\u5b89\u88c5\u5e76\u521d\u59cb\u5316）';
  }
}

/* ---------- Lightning keyword search ---------- */
async function keywordSearch(data, inputs) {
  const query = data.query || (inputs && inputs[0]) || '';
  if (!query) return '\u26a0\ufe0f \u8bf7\u8f93\u5165\u641c\u7d22\u5173\u952e\u8bcd';

  const results = searchFiles(query, WORKSPACE, data.n_results || 5);
  return formatResults(results, query);
}

/* ---------- MemPalace status ---------- */
async function mempalaceStatus() {
  try {
    const output = execSync('mempalace status', {
      encoding: 'utf-8',
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
    });
    return '```\n' + output.trim() + '\n```';
  } catch (err) {
    return '\u26a0\ufe0f MemPalace \u672a\u5b89\u88c5\u6216\u672a\u521d\u59cb\u5316: ' + err.message;
  }
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
          } catch { /* skip unreadable */ }
        }
      }
    } catch { /* skip unreadable dirs */ }
  }
  walk(root);
  results.sort((a, b) => b.score - a.score);
  return results.slice(0, maxResults);
}

function formatResults(results, query) {
  if (results.length === 0) {
    return '\ud83d\udd0d \u5173\u952e\u8bcd\u641c\u7d22\u300c' + query + '\u300d\u672a\u627e\u5230\u76f8\u5173\u6587\u4ef6';
  }
  let output = '\ud83d\udd0d \u5173\u952e\u8bcd\u641c\u7d22\u300c' + query + '\u300d\u627e\u5230 ' + results.length + ' \u4e2a\u6587\u4ef6\n\n';
  for (const r of results) {
    output += '\ud83d\udcc4 ' + r.file + ' (score: ' + r.score + ')\n';
    output += '  ' + r.snippet + '\n\n';
  }
  return output.trim();
}
