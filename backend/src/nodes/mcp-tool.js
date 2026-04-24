import { callTool } from '../mcp-manager.js';

/**
 * MCP Tool node — calls any tool on a connected MCP server.
 * data: { serverId, toolName, toolArgs: { key: value } }
 * Returns the MCP tool call result.
 */
export async function mcp_tool(data, inputs) {
  const { serverId, toolName, toolArgs = {} } = data || {};

  if (!serverId) return { error: 'No MCP server selected', output: '' };
  if (!toolName) return { error: 'No tool selected on server: ' + serverId, output: '' };

  // Merge upstream input into tool args so pipelines chain naturally
  const args = { ...toolArgs };
  if (inputs && inputs.length > 0 && inputs[0]) {
    args._upstream = inputs[0];
  }

  try {
    const result = await callTool(serverId, toolName, args);
    const content = result.content || [];
    // Extract text from MCP content items
    const textOutput = content.map(c => c.text || JSON.stringify(c)).join('\n');
    return {
      output: textOutput,
      isError: result.isError || false,
      raw: result
    };
  } catch (err) {
    return {
      output: '⚠️ MCP Error: ' + err.message,
      isError: true
    };
  }
}