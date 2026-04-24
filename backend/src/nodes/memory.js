import { execSync } from 'child_process';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const BRIDGE = path.resolve(__dirname, '../mempalace_bridge.py');
const DEFAULT_PALACE = path.resolve(os.homedir(), '.mempalace/palace');

/**
 * Memory node — bridges PipeMind pipelines with MemPalace memory system.
 *
 * Two modes:
 *  1. search: search MemPalace (query from data.query || upstream input)
 *  2. save:   save upstream content to MemPalace
 *
 * Configurable via data: { mode, wing, room, n_results }
 */
export async function memory(data, inputs, results) {
  const mode = data.mode || 'search';
  const wing = data.wing || 'pipemind';
  const room = data.room || 'general';

  try {
    if (mode === 'search') {
      const query = data.query || inputs[0] || '';
      if (!query) return '⚠️ 请输入搜索关键词或连接上游节点';

      const n_results = data.n_results || 5;

      const payload = JSON.stringify({
        action: 'search',
        query,
        wing,
        room,
        n_results,
        palace_path: data.palace_path || DEFAULT_PALACE,
        max_distance: data.max_distance || 1.5,
      });

      const result = execSync(`python "${BRIDGE}"`, {
        input: payload,
        encoding: 'utf8',
        timeout: 30000,
      });

      const parsed = JSON.parse(result);
      if (!parsed.success) throw new Error(parsed.error);

      return formatSearchResults(parsed.data, query);

    } else if (mode === 'save') {
      const content = inputs[0] || data.content || '';
      if (!content) return '⚠️ 没有内容可保存，请连接上游节点';

      const source_label = data.source_label || 'pipemind-pipeline';

      const payload = JSON.stringify({
        action: 'save',
        wing,
        room,
        content,
        source_file: source_label,
      });

      const result = execSync(`python "${BRIDGE}"`, {
        input: payload,
        encoding: 'utf8',
        timeout: 15000,
      });

      const parsed = JSON.parse(result);
      if (!parsed.success) throw new Error(parsed.error);

      return `✅ 已保存到记忆宫殿：${wing}/${room}\n${JSON.stringify(parsed.data, null, 2)}`;
    }
  } catch (err) {
    return `❌ 记忆节点错误: ${err.message}`;
  }
}

function formatSearchResults(data, query) {
  if (!data || !data.results || data.results.length === 0) {
    return `🔍 未找到与「${query}」相关的记忆`;
  }

  let output = `🔍 记忆搜索「${query}」共 ${data.total || data.results.length} 条结果\n\n`;

  for (const r of data.results) {
    output += `--- ${r.metadata?.wing || '?'}/${r.metadata?.room || '?'} ---\n`;
    if (r.metadata?.source_file) output += `来源: ${r.metadata.source_file}\n`;
    if (r.distance !== undefined) output += `相似度: ${(1 - r.distance).toFixed(3)}\n`;
    output += `${(r.content || '').slice(0, 500)}\n\n`;
  }

  return output;
}
