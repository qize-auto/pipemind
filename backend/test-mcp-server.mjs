import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

const server = new Server(
  { name: 'test-math-server', version: '1.0.0' },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: 'add',
      description: 'Add two numbers',
      inputSchema: {
        type: 'object',
        properties: {
          a: { type: 'number', description: 'First number' },
          b: { type: 'number', description: 'Second number' }
        },
        required: ['a', 'b']
      }
    },
    {
      name: 'echo',
      description: 'Echo back the input',
      inputSchema: {
        type: 'object',
        properties: {
          text: { type: 'string', description: 'Text to echo' }
        },
        required: ['text']
      }
    }
  ]
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  if (name === 'add') {
    const sum = (args.a || 0) + (args.b || 0);
    return { content: [{ type: 'text', text: String(sum) }] };
  }
  if (name === 'echo') {
    return { content: [{ type: 'text', text: args.text || '' }] };
  }
  throw new Error('Unknown tool: ' + name);
});

const transport = new StdioServerTransport();
await server.connect(transport);