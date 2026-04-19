import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, ReferenceLine
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#fff', border: '0.5px solid #ddd', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
      <p style={{ fontWeight: 500, marginBottom: 4 }}>Step {label}</p>
      <p>Reward: <span style={{ color: payload[0]?.value >= 0 ? '#22c55e' : '#ef4444' }}>{payload[0]?.value?.toFixed(3)}</span></p>
      <p>Cumulative: <b>{payload[1]?.value?.toFixed(3)}</b></p>
    </div>
  );
};

export default function RewardChart({ history }) {
  if (!history.length) {
    return (
      <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa', fontSize: 13 }}>
        No steps yet — reset an episode and run the agent
      </div>
    );
  }

  const data = history.map(h => ({
    step:       h.step,
    reward:     parseFloat(h.reward?.toFixed(3)      ?? 0),
    cumulative: parseFloat(h.cumulative?.toFixed(3)  ?? 0),
  }));

  return (
    <div>
      <p style={{ fontSize: 12, color: '#888', marginBottom: 12 }}>
        Step-level reward (blue) and cumulative reward (green)
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0efe8" />
          <XAxis dataKey="step" label={{ value: 'Step', position: 'insideBottomRight', offset: -5 }} tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="#ccc" />
          <Line type="monotone" dataKey="reward"     stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} name="Step reward" />
          <Line type="monotone" dataKey="cumulative" stroke="#22c55e" strokeWidth={2} dot={false}     name="Cumulative" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}