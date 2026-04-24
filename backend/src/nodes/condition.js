/**
 * Condition node — evaluates upstream output against a condition.
 * Returns { verdict: true/false, details: string }
 *
 * Operators:
 *  - contains: upstream output contains compareValue
 *  - equals: upstream output equals compareValue (exact match)
 *  - length_gt: upstream output length > compareValue (as number)
 *  - length_lt: upstream output length < compareValue (as number)
 *  - regex: upstream output matches compareValue regex
 */
export async function condition(data, inputs) {
  const { condition: cond = '', operator = 'contains', compareValue = '' } = data || {};

  // Get input text from upstream nodes
  const inputText = inputs[0] || '';
  const condText = cond || inputText;

  if (!condText) {
    return {
      verdict: false,
      details: '⚠️ 条件分支：未输入检查条件，也无上游输入',
    };
  }

  let verdict = false;
  let details = '';

  try {
    switch (operator) {
      case 'contains':
        verdict = condText.includes(compareValue);
        details = verdict
          ? `✅ 条件满足：输入包含 "${compareValue}"`
          : `❌ 条件不满足：输入不包含 "${compareValue}"`;
        break;

      case 'equals':
        verdict = condText === compareValue;
        details = verdict
          ? `✅ 条件满足：输入等于 "${compareValue}"`
          : `❌ 条件不满足：输入不等于 "${compareValue}"`;
        break;

      case 'length_gt': {
        const len = parseInt(compareValue, 10) || 0;
        verdict = condText.length > len;
        details = verdict
          ? `✅ 条件满足：输入长度 (${condText.length}) > ${len}`
          : `❌ 条件不满足：输入长度 (${condText.length}) <= ${len}`;
        break;
      }

      case 'length_lt': {
        const len = parseInt(compareValue, 10) || 0;
        verdict = condText.length < len;
        details = verdict
          ? `✅ 条件满足：输入长度 (${condText.length}) < ${len}`
          : `❌ 条件不满足：输入长度 (${condText.length}) >= ${len}`;
        break;
      }

      case 'regex':
        try {
          const re = new RegExp(compareValue);
          verdict = re.test(condText);
          details = verdict
            ? `✅ 条件满足：输入匹配正则 "${compareValue}"`
            : `❌ 条件不满足：输入不匹配正则 "${compareValue}"`;
        } catch (e) {
          details = `❌ 正则表达式错误: ${e.message}`;
          verdict = false;
        }
        break;

      default:
        details = `❌ 未知操作符: ${operator}`;
        verdict = false;
    }
  } catch (err) {
    details = `❌ 条件评估出错: ${err.message}`;
    verdict = false;
  }

  return { verdict, details };
}
