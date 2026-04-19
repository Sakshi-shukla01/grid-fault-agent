import React from 'react';

const SEVERITY_COLOR = { critical: '#ef4444', major: '#f59e0b', minor: '#3b82f6' };
const ACTION_COLOR   = { identify_fault: '#8b5cf6', query_telemetry: '#06b6d4', isolate_breaker: '#f97316', submit_rca: '#22c55e' };

export default function ActionLog({ history, faults }) {
  return (
    <div>
      <div style={{ display: 'flex', gap: 20, marginBottom: 16 }}>
        <div style={{ background: '#f3f3f0', borderRadius: 8, padding: '8px 14px', fontSize: 12 }}>
          <div style={{ color: '#888', marginBottom: 2 }}>Faults identified</div>
          <div style={{ fontSize: 20, fontWeight: 500 }}>{faults.length}</div>
        </div>
        <div style={{ background: '#f3f3f0', borderRadius: 8, padding: '8px 14px', fontSize: 12 }}>
          <div style={{ color: '#888', marginBottom: 2 }}>Total steps</div>
          <div style={{ fontSize: 20, fontWeight: 500 }}>{history.length}</div>
        </div>
      </div>

      {faults.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 11, fontWeight: 500, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Confirmed faults</p>
          {faults.map((f, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, padding: '8px 0', borderBottom: '0.5px solid #f0efe8', alignItems: 'flex-start' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: SEVERITY_COLOR[f.severity] ?? '#888', marginTop: 4, flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 2 }}>
                  <span style={{ fontSize: 12, fontWeight: 500, fontFamily: 'monospace' }}>{f.component_id}</span>
                  <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 4, background: '#f3f3f0', color: '#666' }}>{f.fault_type}</span>
                  <span style={{ fontSize: 10, color: SEVERITY_COLOR[f.severity] ?? '#888' }}>{f.severity}</span>
                </div>
                <div style={{ fontSize: 11, color: '#666', lineHeight: 1.5 }}>{f.description}</div>
              </div>
              <div style={{ fontSize: 11, color: '#22c55e', fontWeight: 500, flexShrink: 0 }}>+{f.reward?.toFixed(2)}</div>
            </div>
          ))}
        </div>
      )}

      <p style={{ fontSize: 11, fontWeight: 500, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Step history</p>
      {history.length === 0
        ? <p style={{ fontSize: 12, color: '#aaa' }}>No steps yet</p>
        : [...history].reverse().map((h, i) => (
            <div key={i} style={{ padding: '8px 0', borderBottom: '0.5px solid #f0efe8', fontSize: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                <span style={{ color: ACTION_COLOR[h.action?.action_type] ?? '#888', fontWeight: 500 }}>
                  Step {h.step} — {h.action?.action_type ?? 'unknown'}
                </span>
                <span style={{ color: h.reward >= 0 ? '#22c55e' : '#ef4444', fontWeight: 500 }}>
                  {h.reward >= 0 ? '+' : ''}{h.reward?.toFixed(3)}
                </span>
              </div>
              <div style={{ color: '#666' }}>{h.feedback?.slice(0, 100)}{h.feedback?.length > 100 ? '…' : ''}</div>
            </div>
          ))
      }
    </div>
  );
}