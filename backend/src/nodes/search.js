import { existsSync } from 'fs';
import { join } from 'path';
import os from 'os';
import http from 'http';

/**
 * Search node: calls Auth Gateway directly (no child process).
 * Config: { query, freshness, count }
 */
export async function search(data = {}, _inputs) {
  const query = data.query || '默认搜索';
  const freshness = data.freshness || 'week';
  const maxResults = data.count || 3;

  const freshnessMap = { day: '24h', week: '7d', month: '30d' };
  const fv = freshnessMap[freshness] || '7d';

  const body = JSON.stringify({
    keyword: query,
    cnt: maxResults,
    ...(fv ? { freshness: fv } : {}),
  });

  return new Promise((resolve) => {
    const req = http.request(
      {
        host: '127.0.0.1',
        port: 19000,
        path: '/proxy/prosearch/search',
        method: 'POST',
        timeout: 12000,
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(body),
        },
      },
      (res) => {
        let data = '';
        res.setEncoding('utf8');
        res.on('data', (chunk) => { data += chunk; });
        res.on('end', () => {
          try {
            const result = JSON.parse(data);
            if (!result.success) {
              resolve(`[搜索失败] ${result.message || '未知错误'}`);
              return;
            }
            const docs = result.data?.docs || [];
            if (!docs.length) {
              resolve(`[搜索] 查询 "${query}" 无结果`);
              return;
            }
            const lines = [
              `🔍 搜索结果 (${docs.length}条): "${query}"`,
              '',
              ...docs.slice(0, maxResults).map((d, i) =>
                `${i + 1}. ${d.title}\n   来源: ${d.site || '网络'} | ${d.date || ''}\n   ${d.url || ''}\n   ${(d.passage || '').slice(0, 200)}...`
              ),
            ];
            resolve(lines.join('\n\n'));
          } catch (e) {
            resolve(`[搜索] 响应解析失败: ${e.message}`);
          }
        });
      }
    );

    req.on('timeout', () => { req.destroy(); resolve('[搜索] 请求超时（12秒）'); });
    req.on('error', (err) => { resolve(`[搜索] 请求失败: ${err.message}`); });
    req.write(body);
    req.end();
  });
}
