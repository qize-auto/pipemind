/**
 * MindMap node handler: pure pass-through — the actual mind map
 * visualization is rendered on the frontend by markmap.
 */
export async function mindmap(data, inputs) {
  return inputs[0] || '';
}
