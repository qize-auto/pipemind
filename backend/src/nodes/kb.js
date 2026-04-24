/**
 * KB (Knowledge Base) node: searches IMA knowledge base via IMA OpenAPI.
 * 
 * Credential sources (priority order):
 *   1. Auth Gateway proxy (platform mode) — same as get-token.ps1
 *   2. Environment variables IMA_CLIENT_ID + IMA_API_KEY (local mode)
 * 
 * Config: { query, knowledge_base_id, limit }
 */

const AUTH_TOKEN = process.env.PIPEMIND_AUTH_TOKEN || '70150279c98c722406e952c2a203b22a4a61106427e82a3c';
const IMA_BASE = 'https://ima.qq.com/openapi/wiki/v1';

/**
 * Get IMA credentials via Auth Gateway (same as get-token.ps1)
 */
async function getCredsFromGateway() {
  const proxyPort = process.env.AUTH_GATEWAY_PORT || 19000;
  const remoteUrl = 'https://jprx.m.qq.com/data/4164/forward';

  const res = await fetch(`http://127.0.0.1:${proxyPort}/proxy/api`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Remote-URL': remoteUrl,
      'x-api-key': AUTH_TOKEN,
      'Connection': 'close',
    },
    body: JSON.stringify({ platform: 'ima' }),
    signal: AbortSignal.timeout(8000),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`Auth Gateway returned HTTP ${res.status}: ${text.slice(0, 100)}`);
  }

  const result = await res.json();
  if (result.ret !== 0) {
    throw new Error(`Auth Gateway error: ret=${result.ret}`);
  }

  const data = result.data?.resp?.data;
  if (!data?.access_token || !data?.extra_data?.client_id) {
    throw new Error('Auth Gateway response missing credential fields');
  }

  return { clientId: data.extra_data.client_id, apiKey: data.access_token };
}

/**
 * Get IMA credentials from environment variables
 */
function getCredsFromEnv() {
  const clientId = process.env.IMA_CLIENT_ID;
  const apiKey = process.env.IMA_API_KEY;
  if (!clientId || !apiKey) {
    throw new Error('IMA credentials not configured. Set IMA_CLIENT_ID and IMA_API_KEY in .env, or ensure Auth Gateway is running.');
  }
  return { clientId, apiKey };
}

/**
 * Get IMA credentials (try gateway first, fallback to env)
 */
async function getCreds() {
  try {
    return await getCredsFromGateway();
  } catch (gatewayErr) {
    console.warn('[kb] Auth Gateway credential fetch failed, trying env vars:', gatewayErr.message);
    return getCredsFromEnv();
  }
}

/**
 * Search IMA knowledge base
 */
export async function kb(data = {}, inputs) {
  const query = data.query || inputs.join(' ') || '默认搜索';
  const knowledgeBaseId = data.knowledge_base_id || '';
  const limit = Math.min(data.limit || 5, 50);

  if (!knowledgeBaseId) {
    return `[知识库] ⚠️ 未配置知识库 ID，请在节点配置中设置 knowledge_base_id`;
  }

  try {
    // ── Get credentials ──
    const { clientId, apiKey } = await getCreds();

    // ── Search IMA knowledge base ──
    const res = await fetch(`${IMA_BASE}/search_knowledge`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'ima-openapi-clientid': clientId,
        'ima-openapi-apikey': apiKey,
      },
      body: JSON.stringify({
        query,
        knowledge_base_id: knowledgeBaseId,
        cursor: '',
      }),
      signal: AbortSignal.timeout(15000),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      return `[知识库] HTTP ${res.status}: ${text.slice(0, 150) || '未知错误'}`;
    }

    const result = await res.json();

    // IMA API may return code/msg (like search_knowledge_base) or retcode/errmsg (like other APIs)
    const apiRetcode = result.code !== undefined ? result.code : result.retcode;
    const apiErrmsg = result.msg || result.errmsg || '';

    if (apiRetcode !== 0) {
      return `[知识库] API 错误: ${apiErrmsg || `code=${apiRetcode}`}`;
    }

    const items = result.data?.info_list || [];
    const isEnd = result.data?.is_end;

    if (!items.length) {
      return `[知识库] 在知识库中搜索 "${query}" 无结果`;
    }

    // ── Format results ──
    const kbIdShort = knowledgeBaseId.length > 32 ? knowledgeBaseId.slice(0, 32) + '...' : knowledgeBaseId;
    const lines = [
      `📚 知识库「${kbIdShort}」搜索结果 (${items.length}条): "${query}"`,
      '',
      ...items.slice(0, limit).map((item, i) => {
        const title = item.title || '无标题';
        const highlight = item.highlight_content || '';
        const folder = item.parent_folder_id ? `(文件夹: ${item.parent_folder_id})` : '';
        return `${i + 1}. 📄 ${title}${folder}\n${highlight ? `   > ${highlight.slice(0, 200)}` : ''}`;
      }),
    ];

    if (isEnd === false) {
      lines.push('');
      lines.push('--- 还有更多结果，可调整查询获取更精确的匹配 ---');
    }

    return lines.join('\n\n');
  } catch (err) {
    if (err.name === 'AbortError') {
      return '[知识库] 请求超时（15秒），请稍后重试';
    }
    return `[知识库] 请求失败: ${err.message}`;
  }
}
