import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import os from 'os';

const WORKSPACE = os.homedir() + '/.qclaw/workspace';

/**
 * Memory node — lightweight file-based memory search.
 * Uses Node.js grep/search instead of ChromaDB for reliability.
 * Two modes: search (default), save
 */
export async function memory(data, inputs, _results) {
  const mode = data.mode || 'search';

  try {
    if (mode === 'search') {
      const query = data.query || (inputs && inputs[0]) || '';
      if (!query) return '\u26a0\ufe0f \u8bf7\u8f93\u5165\u641c\u7d22\u5173\u952e\u8bcd';

      const results = searchFiles(query, WORKSPACE, data.n_results || 5);
      return formatResults(results, query);
    }

    /* save mode is deprecated — currently search-only */
    return '\u2705 \u8bb0\u5fc6\u8282\u70b9\u4ec5\u652f\u6301\u641c\u7d22\u6a21\u5f0f';
  } catch (err) {
    return '\u274c \u8bb0\u5fc6\u8282\u70b9\u9519\u8bef: ' + err.message;
  }
}

/** Search workspace files for query */
function searchFiles(query, dir, maxResults) {
  const keywords = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (keywords.length === 0) return [];

  const results = [];
  const root = path.resolve(dir);

  // Walk files recursively (depth 3, max 200 files)
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
    return '\ud83d\udd0d \u672a\u627e\u5230\u4e0e\u300c' + query + '\u300d\u76f8\u5173\u7684\u8bb0\u5fc6';
  }
  let output = '\ud83d\udd0d \u6587\u4ef6\u641c\u7d22\u300c' + query + '\u300d\u627e\u5230 ' + results.length + ' \u4e2a\u6587\u4ef6\n\n';
  for (const r of results) {
    output += '\ud83d\udcc4 ' + r.file + ' (score: ' + r.score + ')\n';
    output += '  ' + r.snippet + '\n\n';
  }
  return output.trim();
}
