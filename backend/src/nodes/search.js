/**
 * Search node: calls Auth Gateway via fetch with auth token.
 * Config: { query, freshness, count }
 */
// Auth Gateway token: read from env, fallback to known token for local dev
const AUTH_TOKEN = process.env.PIPEMIND_AUTH_TOKEN || '70150279c98c722406e952c2a203b22a4a61106427e82a3c';
const freshnessMap = { week: '7d', day: '24h', month: '30d' };

export async function search(data = {}, _inputs) {
  const query = data.query || '默认搜索';
  const freshness = data.freshness || 'week';
  const cnt = Math.min(data.count || 3, 10);
  const fv = freshnessMap[freshness] || '7d';

  try {
    const res = await fetch('http://127.0.0.1:19000/proxy/prosearch/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': AUTH_TOKEN,
        'Connection': 'close',
      },
      body: JSON.stringify({
        keyword: query,
        cnt,
        freshness: fv,
      }),
      signal: AbortSignal.timeout(12000),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      return `[搜索] HTTP ${res.status}: ${text.slice(0, 100) || '未知错误'}`;
    }

    const result = await res.json();

    if (!result.success) {
      return `[搜索失败] ${result.message || '未知错误'}`;
    }

    const docs = result.data?.docs || [];
    if (!docs.length) {
      return `[搜索] 查询 "${query}" 无结果`;
    }

    const lines = [
      `🔍 搜索结果 (${docs.length}条): "${query}"`,
      '',
      ...docs.slice(0, cnt).map((d, i) =>
        `${i + 1}. ${d.title}\n   来源: ${d.site || '网络'} | ${d.date || ''}\n   ${d.url || ''}\n   ${(d.passage || '').slice(0, 200)}...`
      ),
    ];
    return lines.join('\n\n');
  } catch (err) {
    if (err.name === 'AbortError') {
      return '[搜索] 请求超时（12秒），请稍后重试';
    }
    return `[搜索] 请求失败: ${err.message}`;
  }
}
