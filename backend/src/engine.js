import * as nodeHandlers from './nodes/index.js';

/**
 * Build adjacency list + in-degree map from edges
 */
function buildGraph(edges) {
  const adj = {};
  const inDeg = {};

  for (const e of edges) {
    if (!adj[e.source]) adj[e.source] = [];
    adj[e.source].push(e.target);
    if (!inDeg[e.target]) inDeg[e.target] = 0;
    if (!inDeg[e.source]) inDeg[e.source] = 0;
    inDeg[e.target] = (inDeg[e.target] || 0) + 1;
  }

  return { adj, inDeg };
}

/**
 * Topological sort: return ordered node ID list
 */
export function getExecutionPlan(nodes, edges) {
  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));
  const { adj, inDeg } = buildGraph(edges);

  // Sources: nodes with no incoming edges
  let queue = nodes
    .filter(n => !inDeg[n.id])
    .sort((a, b) => a.position.y - b.position.y);

  const plan = [];
  const visited = new Set();
  let iteration = 0;

  while (queue.length > 0 && iteration < 100) {
    iteration++;
    const nextQueue = [];

    for (const node of queue) {
      if (visited.has(node.id)) continue;
      visited.add(node.id);
      plan.push(node.id);

      if (adj[node.id]) {
        for (const downstreamId of adj[node.id]) {
          if (!visited.has(downstreamId)) {
            nextQueue.push(nodeMap[downstreamId]);
          }
        }
      }
    }

    queue = nextQueue;
  }

  return plan;
}

/**
 * Execute a single node given upstream results
 */
export async function runSingleNode(nodeId, nodes, edges, results) {
  const node = nodes.find(n => n.id === nodeId);
  if (!node) throw new Error(`Node not found: ${nodeId}`);

  const handler = nodeHandlers[node.type];
  if (!handler) throw new Error(`Unknown node type: ${node.type}`);

  // Collect inputs from upstream nodes
  const upstreamIds = edges
    .filter(e => e.target === node.id)
    .map(e => e.source);

  const inputs = upstreamIds.map(id => results[id]?.output || '');

  // Execute
  const start = Date.now();
  const output = await handler(node.data || {}, inputs, results);
  const duration = Date.now() - start;

  // For condition nodes, store verdict in results for downstream edge filtering
  if (node.type === 'condition') {
    results[node.id] = {
      output,
      duration,
      type: node.type,
      label: node.data?.label || node.type,
      verdict: output?.verdict,
    };
    return results[node.id];
  }

  return {
    output,
    duration,
    type: node.type,
    label: node.data?.label || node.type,
  };
}

/**
 * Execute workflow as a DAG: find source nodes => run => propagate
 */
export async function runWorkflow(nodes, edges) {
  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));
  const { adj, inDeg } = buildGraph(edges);
  const results = {};

  // Sources: nodes with no incoming edges
  let queue = nodes
    .filter(n => !inDeg[n.id])
    .sort((a, b) => a.position.y - b.position.y);

  let iteration = 0;
  const visited = new Set();

  while (queue.length > 0 && iteration < 100) {
    iteration++;
    const nextQueue = [];

    for (const node of queue) {
      if (visited.has(node.id)) continue;
      visited.add(node.id);

      const handler = nodeHandlers[node.type];
      if (!handler) throw new Error(`Unknown node type: ${node.type}`);

      // Collect inputs from upstream nodes
      const upstreamIds = edges
        .filter(e => e.target === node.id)
        .map(e => e.source);

      const inputs = upstreamIds.map(id => results[id]?.output || '');

      // Execute
      const start = Date.now();
      const output = await handler(node.data || {}, inputs, results);
      const duration = Date.now() - start;

      // For condition nodes, store verdict in results
      const nodeResult = { output, duration, type: node.type, label: node.data?.label || node.type };
      if (node.type === 'condition') {
        nodeResult.verdict = output?.verdict;
      }
      results[node.id] = nodeResult;

      // Enqueue downstream nodes (with condition branching)
      if (adj[node.id]) {
        for (const downstreamId of adj[node.id]) {
          if (visited.has(downstreamId)) continue;

          // For condition nodes, only enqueue the matching branch
          if (node.type === 'condition') {
            const edge = edges.find(e => e.source === node.id && e.target === downstreamId);
            const sourceHandle = edge?.sourceHandle || 'true';
            const verdict = output?.verdict;

            // sourceHandle 'true' = right output, 'false' = bottom output
            if ((verdict === true && sourceHandle !== 'true') ||
                (verdict === false && sourceHandle !== 'false')) {
              continue;
            }
          }

          nextQueue.push(nodeMap[downstreamId]);
        }
      }
    }

    queue = nextQueue;
  }

  return results;
}
