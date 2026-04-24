import { useState, useEffect, useRef } from 'react';

const API_BASE = 'http://localhost:3001';

export default function LogPanel({ visible, onClose }) {
  const [logs, setLogs] = useState([]);
  const [connected, setConnected] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!visible) return;

    const evtSource = new EventSource(`${API_BASE}/api/stream/events`);

    evtSource.onopen = () => setConnected(true);
    evtSource.onerror = () => setConnected(false);

    evtSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (!data.type) return;
        setLogs(prev => [...prev.slice(-499), { ...data, ts: new Date().toLocaleTimeString() }]);
      } catch { /* ignore parse errors */ }
    };

    return () => evtSource.close();
  }, [visible]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (!visible) return null;

  const iconFor = (type) => {
    if (type === 'node:start') return '\u25b6';
    if (type === 'node:complete') return '\u2705';
    if (type === 'node:error') return '\u274c';
    if (type === 'pipeline:complete') return '\u2728';
    return '\u25cf';
  };

  const colorFor = (type) => {
    if (type === 'node:start') return '#fbbf24';
    if (type === 'node:complete') return '#4ade80';
    if (type === 'node:error') return '#f87171';
    if (type === 'pipeline:complete') return '#a78bfa';
    return '#94a3b8';
  };

  return (
    <div style={{
      position: 'fixed', right: 0, top: 0, bottom: 0, width: 340,
      background: '#0f172a', borderLeft: '1px solid #334155',
      display: 'flex', flexDirection: 'column', zIndex: 100,
      fontFamily: 'monospace', fontSize: 12, color: '#e2e8f0'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '10px 14px', borderBottom: '1px solid #334155',
        background: '#1e293b'
      }}>
        <span style={{ color: connected ? '#4ade80' : '#f87171', fontSize: 10 }}>
          {connected ? '\u25cf' : '\u25cb'}
        </span>
        <strong>Pipeline Log</strong>
        <span style={{ fontSize: 11, color: '#64748b', marginLeft: 'auto' }}>
          {logs.length} events
        </span>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', color: '#94a3b8',
          cursor: 'pointer', fontSize: 16, padding: '0 4px'
        }}>
          {'\u2716'}
        </button>
      </div>

      {/* Log entries */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
        {logs.length === 0 && (
          <div style={{ color: '#64748b', textAlign: 'center', marginTop: 40 }}>
            No events yet.<br />Run a pipeline to see logs.
          </div>
        )}
        {logs.map((log, i) => (
          <div key={i} style={{
            padding: '6px 8px', marginBottom: 2,
            borderLeft: `3px solid ${colorFor(log.type)}`,
            background: log.type === 'node:error' ? 'rgba(248, 113, 113, 0.08)' : 'transparent',
            borderRadius: 4
          }}>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <span style={{ color: colorFor(log.type) }}>{iconFor(log.type)}</span>
              <span style={{ color: '#94a3b8', fontSize: 10, whiteSpace: 'nowrap' }}>{log.ts}</span>
              <span style={{
                fontSize: 10, background: '#334155', borderRadius: 3,
                padding: '1px 5px', color: '#94a3b8'
              }}>
                {log.label || log.type}
              </span>
            </div>
            {log.type === 'node:complete' && log.duration && (
              <div style={{ fontSize: 10, color: '#64748b', marginTop: 2, marginLeft: 20 }}>
                {'\u23f1'} {log.duration}ms
              </div>
            )}
            {log.type === 'node:error' && log.error && (
              <div style={{ fontSize: 10, color: '#f87171', marginTop: 2, marginLeft: 20 }}>
                {log.error}
              </div>
            )}
            {log.type === 'node:complete' && log.output && (
              <div style={{
                fontSize: 10, color: '#94a3b8', marginTop: 2, marginLeft: 20,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                maxWidth: 260
              }}>
                {typeof log.output === 'string'
                  ? log.output.slice(0, 80)
                  : JSON.stringify(log.output).slice(0, 80)}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Footer */}
      <div style={{
        padding: '6px 14px', borderTop: '1px solid #334155',
        fontSize: 10, color: '#64748b'
      }}>
        {connected ? '\u25cf Connected' : '\u25cb Disconnected'}
        {logs.length > 0 && '  |  Clear '}
        {logs.length > 0 && (
          <button onClick={() => setLogs([])} style={{
            background: 'none', border: 'none', color: '#60a5fa',
            cursor: 'pointer', fontSize: 10, textDecoration: 'underline'
          }}>
            clear
          </button>
        )}
      </div>
    </div>
  );
}
