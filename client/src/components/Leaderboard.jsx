import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function Leaderboard({ taskId }) {
  const [board,   setBoard]   = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchBoard = async () => {
    setLoading(true);
    try {
      const { data } = await axios.get(`/api/leaderboard?taskId=${taskId}`);
      setBoard(data);
    } catch (err) {
      console.error('Leaderboard fetch failed:', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchBoard(); }, [taskId]);

  if (loading) return <div style={{ color: '#aaa', fontSize: 13, padding: 20 }}>Loading…</div>;
  if (!board.length) return (
    <div style={{ color: '#aaa', fontSize: 13, padding: 20, textAlign: 'center' }}>
      No completed episodes yet for this task.
      <br />Run inference.py to generate scores.
    </div>
  );

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #e0dfd8' }}>
            {['Rank', 'Model', 'Avg score', 'Best score', 'Recall', 'Precision', 'Efficiency', 'Runs'].map(h => (
              <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: '#888', fontWeight: 500, whiteSpace: 'nowrap' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {board.map((row, i) => (
            <tr key={row.modelName} style={{ borderBottom: '0.5px solid #f0efe8', background: i === 0 ? '#fafff7' : 'transparent' }}>
              <td style={{ padding: '8px 12px', color: i === 0 ? '#22c55e' : '#888', fontWeight: i === 0 ? 600 : 400 }}>#{i + 1}</td>
              <td style={{ padding: '8px 12px', fontWeight: 500, fontFamily: 'monospace', fontSize: 11 }}>{row.modelName}</td>
              <td style={{ padding: '8px 12px', fontWeight: 600, color: '#1a1a1a' }}>{row.avgScore}</td>
              <td style={{ padding: '8px 12px', color: '#22c55e' }}>{row.bestScore}</td>
              <td style={{ padding: '8px 12px' }}>{row.avgRecall}</td>
              <td style={{ padding: '8px 12px' }}>{row.avgPrecision}</td>
              <td style={{ padding: '8px 12px' }}>{row.avgEfficiency}</td>
              <td style={{ padding: '8px 12px', color: '#888' }}>{row.totalRuns}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}