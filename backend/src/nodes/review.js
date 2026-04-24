/**
 * Review node: self-review/critique for anti-hallucination.
 * Takes LLM output as input, runs a critical review pass,
 * returns annotated content with confidence score and fact-check notes.
 *
 * Config: { tone, strictness }
 */
export async function review(data = {}, inputs) {
  const inputText = inputs.join('\n\n') || '[空输入 - 无内容可审查]';
  const tone = data.tone || 'balanced';
  const strictness = data.strictness || 'normal';
  const apiKey = process.env.PIPEMIND_LLM_KEY || '';
  const model = data.model || 'deepseek-chat';

  if (!inputText.trim() || inputText === '[空输入 - 无内容可审查]') {
    return formatReview({
      verdict: 'SKIP',
      confidence: 0,
      score: 0,
      summary: '无内容可审查',
      details: [],
    }, inputText);
  }

  // ── Build review prompt ──
  const strictnessGuide = {
    mild: '只标记明显错误或严重缺失引用的陈述。对合理的推测给予宽容。',
    normal: '标注缺乏依据的断言、过度的确定性表述、可能的逻辑跳跃。给出改进建议。',
    strict: '严格审查每一句陈述。任何无法从提供信息中严格推导出的内容都需标注。要求每条信息有来源支持。',
  };

  const toneGuide = {
    mild: '友善的建设性反馈，强调"可能"。',
    balanced: '客观中肯的评估，指出优缺。',
    critical: '直接指出问题，不留情面。',
  };

  const systemPrompt = `你是一个内容审查专家。你的任务是对AI生成的内容进行自我审查，检测幻觉、不准确陈述和过度确定性表述。

审查标准（${strictnessGuide[strictness] || strictnessGuide.normal}）
语气（${toneGuide[tone] || toneGuide.balanced}）

请按以下JSON格式输出审查结果（只输出JSON，不要解释）：
{
  "verdict": "PASS" | "WARN" | "FAIL",
  "confidence": 1-10,
  "score": 0-100,
  "summary": "一句话审查结论",
  "issues": [
    { "type": "hallucination" | "overconfidence" | "missing_citation" | "logic_gap", "severity": 1-5, "quote": "有问题的原文片段", "note": "问题说明" }
  ],
  "improvements": ["改进建议1", "改进建议2"]
}`;

  try {
    const response = await fetch('https://api.deepseek.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: `请审查以下AI生成的内容:\n\n${inputText.slice(0, 24000)}` },
        ],
        temperature: 0.2,
        max_tokens: 2048,
      }),
      signal: AbortSignal.timeout(15000),
    });

    if (!response.ok) {
      const errText = await response.text().catch(() => '');
      return formatReview({
        verdict: 'ERROR',
        confidence: 0,
        score: 0,
        summary: `API错误 HTTP ${response.status}`,
        issues: [{ type: 'system_error', severity: 5, quote: '', note: errText.slice(0, 200) }],
        improvements: [],
      }, inputText);
    }

    const raw = await response.json();
    const content = raw.choices?.[0]?.message?.content || '';

    // Parse JSON from LLM response
    let reviewData;
    try {
      // Try direct parse
      reviewData = JSON.parse(content);
    } catch {
      // Try extracting JSON block
      const jsonMatch = content.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try {
          reviewData = JSON.parse(jsonMatch[0]);
        } catch {
          reviewData = null;
        }
      } else {
        reviewData = null;
      }
    }

    if (!reviewData || !reviewData.verdict) {
      return formatReview({
        verdict: 'PARSE_ERR',
        confidence: 5,
        score: 50,
        summary: '审查响应解析失败，标记为待人工确认',
        issues: [{ type: 'parse_error', severity: 3, quote: '', note: 'LLM返回非标准格式' }],
        improvements: ['请人工审查内容'],
      }, inputText, `\n\n--- 审查原始响应 ---\n${content.slice(0, 1000)}`);
    }

    // ── Build annotated output ──
    return formatReview(reviewData, inputText);

  } catch (err) {
    if (err.name === 'AbortError') {
      return formatReview({
        verdict: 'TIMEOUT',
        confidence: 5,
        score: 50,
        summary: '审查超时（15秒），视为待定',
        issues: [],
        improvements: ['重试审查或人工检查'],
      }, inputText);
    }
    return formatReview({
      verdict: 'ERROR',
      confidence: 0,
      score: 0,
      summary: `审查调用异常: ${err.message}`,
      issues: [{ type: 'system_error', severity: 5, quote: '', note: err.message }],
      improvements: [],
    }, inputText);
  }
}

function formatReview(review, originalContent, extra = '') {
  const scoreBar = getScoreBar(review.score || 50);
  const issueCount = (review.issues || []).length;
  const criticalIssues = (review.issues || []).filter(i => i.severity >= 4).length;

  const header = [
    '═'.repeat(50),
    '🔍 自我审查报告',
    '═'.repeat(50),
    '',
    ` verdict : ${getVerdictEmoji(review.verdict)} ${review.verdict}`,
    ` 可信度  : ${review.confidence || '?'}/10`,
    ` 质量分  : ${review.score || '?'}/100 ${scoreBar}`,
    ` 问题数  : ${issueCount}项 (严重: ${criticalIssues}项)`,
    ` 摘要    : ${review.summary || '无'}`,
    '',
  ].join('\n');

  let issuesSection = '';
  if (review.issues && review.issues.length > 0) {
    issuesSection = '─'.repeat(50) + '\n📋 发现的问题\n' + '─'.repeat(50) + '\n\n' +
      review.issues.map((i, idx) => {
        const sevEmoji = i.severity >= 4 ? '🔴' : i.severity >= 2 ? '🟡' : '🟢';
        return `[${idx + 1}] ${sevEmoji} ${i.type}\n    严重度: ${i.severity}/5\n    ${i.quote ? `原文: "${i.quote.slice(0, 100)}"\n    ` : ''}说明: ${i.note}`;
      }).join('\n\n');
  }

  let improvementsSection = '';
  if (review.improvements && review.improvements.length > 0) {
    improvementsSection = '\n\n' + '─'.repeat(50) + '\n💡 改进建议\n' + '─'.repeat(50) + '\n' +
      review.improvements.map((imp, i) => `  ${i + 1}. ${imp}`).join('\n');
  }

  const verdictLine = review.verdict === 'PASS' ? '\n✅ 审查通过，内容可靠' :
    review.verdict === 'WARN' ? '\n⚠️ 存在需关注的问题，建议核实' :
    review.verdict === 'FAIL' ? '\n❌ 存在严重问题，不建议直接使用' : '\n❓ 审查状态异常';

  const separator = '\n\n' + '┈'.repeat(50) + '\n📄 原始内容\n' + '┈'.repeat(50) + '\n\n';

  return header + issuesSection + improvementsSection + verdictLine + separator + originalContent + extra + '\n\n' + '═'.repeat(50);
}

function getVerdictEmoji(v) {
  const map = { PASS: '✅', WARN: '⚠️', FAIL: '❌', SKIP: '⏭️', ERROR: '💥', TIMEOUT: '⏰', PARSE_ERR: '🤔' };
  return map[v] || '❓';
}

function getScoreBar(score) {
  const filled = Math.round(score / 10);
  return '█'.repeat(filled) + '░'.repeat(10 - filled);
}
