import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

/**
 * Search node: uses online-search via prosearch.cjs
 * Config: { query, freshness, count }
 */
export async function search(data = {}, _inputs) {
  const query = data.query || '默认搜索';
  const freshness = data.freshness || 'week';
  const maxResults = data.count || 5;

  // Try prosearch.cjs (online-search skill)
  const prosearchPaths = [
    join(__dirname, '..', '..', '..', '..', '.qclaw', 'skills', 'online-search', 'prosearch.cjs'),
    join(__dirname, '..', '..', '..', '..', '.qclaw', 'workspace', 'skills', 'online-search', 'prosearch.cjs'),
  ];

  let foundPath = null;
  for (const p of prosearchPaths) {
    try {
      if (existsSync(p)) { foundPath = p; break; }
    } catch { /* ignore */ }
  }

  // If prosearch found, use it
  if (foundPath) {
    try {
      const json = JSON.stringify({ query, freshness, count: maxResults });
      const cmd = `node "${foundPath}" '${json.replace(/'/g, "'\\''")}'`;
      const raw = execSync(cmd, { encoding: 'utf-8', timeout: 15000, maxBuffer: 10 * 1024 * 1024 });
      const lines = raw.split('\n').filter(l => l.trim());
      const parsed = lines.map(l => {
        try { return JSON.parse(l); } catch { return { text: l }; }
      });
      return JSON.stringify(parsed.slice(0, maxResults), null, 2);
    } catch (err) {
      return `[搜索失败] ${err.message}`;
    }
  }

  // Fallback: web_fetch style
  return `[搜索节点]\n查询: "${query}"\n时效: ${freshness}\n\n(搜索结果待真实搜索引擎集成)`;
}
