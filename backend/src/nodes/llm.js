/**
 * LLM node: calls an OpenAI-compatible API for text processing
 * Config: { prompt, model, apiKey, apiBase }
 * If no apiKey configured, falls back to simple text transform
 * Standalone mode: when no inputs, generates learning content from prompt only
 */
export async function llm(data = {}, inputs) {
  const inputText = inputs.join('\n\n') || '';
  const prompt = data.prompt || '请总结以下内容';
  const model = data.model || 'deepseek-chat';
  const apiKey = data.apiKey || process.env.PIPEMIND_LLM_KEY || '';
  const apiBase = data.apiBase || 'https://api.deepseek.com/v1';

  const standalone = !inputText.trim();

  // ── Fallback: simple text transform ──
  if (!apiKey || apiKey === 'sk-your-key-here') {
    const lines = inputText.split('\n').filter(l => l.trim());
    const summary = lines.slice(0, 5).map(l => {
      const clean = l.replace(/["\[\]{}]/g, '').trim();
      return clean.length > 80 ? clean.slice(0, 80) + '...' : clean;
    }).join('\n');

    return `📝 LLM 摘要 (模拟模式 — 请配置 API Key 启用真实 LLM)\n\n输入长度: ${inputText.length} 字符\n\n${summary}`;
  }

  // ── Real LLM call ──
  try {
    const messages = standalone
      ? [{ role: 'system', content: prompt }]
      : [
          { role: 'system', content: prompt },
          { role: 'user', content: `请处理以下内容:\n\n${inputText.slice(0, 32000)}` }
        ];

    const response = await fetch(`${apiBase}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages,
        temperature: 0.3,
        max_tokens: 2048,
      }),
    });

    if (!response.ok) {
      const errText = await response.text().catch(() => 'unknown error');
      return `[LLM API 错误] HTTP ${response.status}: ${errText.slice(0, 200)}`;
    }

    const data_ = await response.json();
    return data_.choices?.[0]?.message?.content || '[LLM 返回为空]';
  } catch (err) {
    return `[LLM 调用失败] ${err.message}`;
  }
}
