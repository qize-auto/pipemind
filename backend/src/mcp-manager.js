import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { accessSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

function resolveNodePath() {
  const candidates = [
    resolve(__dirname, '..', 'node.exe'),
    'D:\\Program Files\\QClaw\\resources\\node\\node.exe',
    process.env.NODE_EXE,
  ];
  for (const p of candidates) {
    try { accessSync(p); return p; } catch {}
  }
  return process.execPath;
}
const REAL_NODE = resolveNodePath();

const connections = new Map();

export async function connectStdio(serverId, command, args, env) {
  if (connections.has(serverId)) await disconnect(serverId);
  const client = new Client({ name: 'pipemind', version: '1.0.0' });
  const transport = new StdioClientTransport({
    cwd: process.cwd(),
    command: command === 'node' ? REAL_NODE : command,
    args: args || [],
    env: env || undefined
  });
  await client.connect(transport);
  const toolsResult = await client.listTools();
  connections.set(serverId, { client, transport, tools: toolsResult.tools, connected: true, type: 'stdio' });
  return { tools: toolsResult.tools };
}

export async function connectSSE(serverId, url) {
  if (connections.has(serverId)) await disconnect(serverId);
  const { SseClientTransport } = await import('@modelcontextprotocol/sdk/client/sse.js');
  const client = new Client({ name: 'pipemind', version: '1.0.0' });
  const transport = new SseClientTransport({ url });
  await client.connect(transport);
  const toolsResult = await client.listTools();
  connections.set(serverId, { client, transport, tools: toolsResult.tools, connected: true, type: 'sse' });
  return { tools: toolsResult.tools };
}

export async function listTools(serverId) {
  const conn = connections.get(serverId);
  if (!conn) throw new Error(`MCP server ${serverId} not connected`);
  const result = await conn.client.listTools();
  conn.tools = result.tools;
  return result.tools;
}

export async function callTool(serverId, toolName, args) {
  const conn = connections.get(serverId);
  if (!conn) throw new Error(`MCP server ${serverId} not connected`);
  const result = await conn.client.callTool({ name: toolName, arguments: args });
  return result;
}

export async function disconnect(serverId) {
  const conn = connections.get(serverId);
  if (conn) {
    try { await conn.client.close(); } catch (e) { /* ignore */ }
    connections.delete(serverId);
  }
}

export function getStatus() {
  const result = {};
  for (const [id, conn] of connections) {
    result[id] = { connected: conn.connected, type: conn.type, toolCount: conn.tools?.length || 0, tools: conn.tools || [] };
  }
  return result;
}