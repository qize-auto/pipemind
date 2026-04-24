import React, { useState, useEffect, useCallback } from 'react';
import { Handle, Position } from 'reactflow';

const API_BASE = 'http://localhost:3001';

export default function MCPNode({ id, data, selected }) {
  const [serverId, setServerId] = useState(data.serverId || '');
  const [toolName, setToolName] = useState(data.toolName || '');
  const [toolArgs, setToolArgs] = useState(data.toolArgs || '{}');
  const [servers, setServers] = useState({});
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/mcp/status`);
      const j = await r.json();
      setServers(j.connections || {});
    } catch (e) { /* ignore polling errors */ }
  }, []);

  useEffect(() => { fetchStatus(); const iv = setInterval(fetchStatus, 5000); return () => clearInterval(iv); }, [fetchStatus]);
  useEffect(() => { if (serverId && servers[serverId]) setTools(servers[serverId].tools || []); }, [serverId, servers]);

  const update = (field, val) => {
    const n = { serverId, toolName, toolArgs };
    n[field] = val;
    if (field === 'serverId') { setServerId(val); n.toolName = ''; n.toolArgs = '{}'; setToolName(''); setToolArgs('{}'); }
    if (field === 'toolName') { setToolName(val); n.toolName = val; }
    if (field === 'toolArgs') setToolArgs(val);
    data.onUpdate?.(id, n);
  };

  const connectServer = async () => {
    if (!serverId) return;
    setLoading(true); setError('');
    try {
      const r = await fetch(`${API_BASE}/api/mcp/connect`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ serverId, command: 'node', args: [] })
      });
      const j = await r.json();
      if (j.error) { setError(j.error); return; }
      await fetchStatus();
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div style={{
      background: '#1e293b', border: selected ? '2px solid #60a5fa' : '1px solid #334155',
      borderRadius: 12, padding: 14, minWidth: 260, color: '#e2e8f0', fontFamily: 'monospace', fontSize: 13
    }}>
      <Handle type="target" position={Position.Left} style={{ background: '#60a5fa', width: 10, height: 10 }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <span>{'\ud83e\udd16'}</span>
        <strong>MCP Tool</strong>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: servers[serverId] ? '#4ade80' : '#f87171' }}>
          {servers[serverId] ? '\u25cf Online' : '\u25cb Offline'}
        </span>
      </div>

      <label style={{ fontSize: 11, color: '#94a3b8' }}>Server ID</label>
      <input value={serverId} onChange={e => update('serverId', e.target.value)}
        style={inputStyle} placeholder="e.g. math-server" />

      <button onClick={connectServer} disabled={loading || !serverId}
        style={{ ...btnStyle, marginBottom: 8 }}>
        {loading ? 'Connecting...' : 'Connect'}
      </button>
      {error && <div style={{ color: '#f87171', fontSize: 11, marginBottom: 4 }}>{error}</div>}

      {servers[serverId] && servers[serverId].tools && <>
        <label style={{ fontSize: 11, color: '#94a3b8' }}>Tool</label>
        <select value={toolName} onChange={e => update('toolName', e.target.value)} style={inputStyle}>
          <option value="">Select tool...</option>
          {servers[serverId].tools.map(t => (
            <option key={t.name} value={t.name}>{t.name}</option>
          ))}
        </select>
      </>}

      {toolName && <>
        <label style={{ fontSize: 11, color: '#94a3b8' }}>Args (JSON)</label>
        <textarea value={toolArgs} onChange={e => update('toolArgs', e.target.value)}
          style={{ ...inputStyle, minHeight: 60, resize: 'vertical', fontFamily: 'monospace' }}
          placeholder='{"key": "value"}' />
      </>}

      <Handle type="source" position={Position.Right} style={{ background: '#60a5fa', width: 10, height: 10 }} />
    </div>
  );
}

const inputStyle = {
  width: '100%', background: '#0f172a', border: '1px solid #334155',
  borderRadius: 6, padding: '6px 8px', color: '#e2e8f0', fontSize: 12,
  outline: 'none', marginBottom: 6, boxSizing: 'border-box'
};

const btnStyle = {
  width: '100%', background: '#2563eb', border: 'none',
  borderRadius: 6, padding: '6px 12px', color: 'white', cursor: 'pointer',
  fontSize: 12
};
