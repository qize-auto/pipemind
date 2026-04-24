/**
 * Output node: displays/packages results
 * Config: { format: "text" | "json" | "markdown" }
 */
export async function output(data = {}, inputs) {
  const inputText = inputs.join('\n\n') || '[空输入]';
  const format = data.format || 'text';

  if (format === 'json') {
    return JSON.stringify({ content: inputText, timestamp: new Date().toISOString() }, null, 2);
  }

  if (format === 'markdown') {
    const lines = inputText.split('\n').filter(l => l.trim());
    let md = '## PipeMind 输出结果\n\n';
    md += `| 项目 | 值 |\n|------|-----|\n`;
    md += `| 生成时间 | ${new Date().toLocaleString('zh-CN')} |\n`;
    md += `| 内容长度 | ${inputText.length} 字符 |\n`;
    md += `| 行数 | ${lines.length} |\n\n`;
    md += '### 内容预览\n\n```\n' + inputText.slice(0, 2000) + '\n```\n';
    return md;
  }

  // Default: text
  const separator = '─'.repeat(40);
  return `${separator}\n📋 输出结果\n${separator}\n\n${inputText}`;
}
