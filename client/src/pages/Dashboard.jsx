import React, { useState }  from 'react';
import axios                 from 'axios';
import { useSocket }         from '../hooks/useSocket.js';
import GridTopology          from '../components/GridTopology.jsx';
import RewardChart           from '../components/RewardChart.jsx';
import ActionLog             from '../components/ActionLog.jsx';
import Leaderboard           from '../components/Leaderboard.jsx';

const TASKS = [
  { id: 'radial_fault',  label: 'Easy — radial grid',    faults: 6  },
  { id: 'cascade_ring',  label: 'Medium — ring cascade', faults: 10 },
  { id: 'storm_mesh',    label: 'Hard — storm mesh',     faults: 25 },
];

export default function Dashboard() {
  const { observation, history, connected } = useSocket();
  const [taskId,   setTaskId]   = useState('radial_fault');
  const [loading,  setLoading]  = useState(false);
  const [activeTab,setActiveTab]= useState('grid');

  const handleReset = async () => {
    setLoading(true);
    try {
      await axios.post('/api/env/reset', { task_id: taskId });
    } catch (err) {
      console.error('Reset failed:', err.message);
    } finally {
      setLoading(false);
    }
  };

  const meta    = observation?.metadata ?? {};
  const faults  = observation?.identified_faults ?? [];
  const maxF    = TASKS.find(t => t.id === taskId)?.faults ?? 0;

  return (
    <div style={{ minHeight: '100vh', padding: '20px' }}>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600 }}>Grid Fault Localization Agent</h1>
          <p style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
            Real-time RL environment — power grid diagnosis
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%', display: 'inline-block',
            background: connected ? '#22c55e' : '#ef4444'
          }} />
          <span style={{ fontSize: 12, color: '#888' }}>{connected ? 'Live' : 'Disconnected'}</span>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 20, alignItems: 'center' }}>
        <select value={taskId} onChange={e => setTaskId(e.target.value)}>
          {TASKS.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
        </select>
        <button onClick={handleReset} disabled={loading}>
          {loading ? 'Resetting…' : 'Reset Episode'}
        </button>
        {observation && (
          <span style={{ fontSize: 12, color: '#888' }}>
            Step {observation.step_number}/{observation.max_steps}
            &nbsp;|&nbsp;
            Faults: {faults.length}/{maxF}
            &nbsp;|&nbsp;
            Score: {meta.final_score ?? meta.cumulative_reward?.toFixed(3) ?? '—'}
          </span>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 10, marginBottom: 20 }}>
        {[
          { label: 'Cumulative reward', value: meta.cumulative_reward?.toFixed(3) ?? '—' },
          { label: 'Faults found',      value: faults.length ? `${faults.length}/${maxF}` : '—' },
          { label: 'Final score',        value: meta.final_score ?? '—' },
          { label: 'Recall',             value: meta.recall ?? '—' },
        ].map(({ label, value }) => (
          <div key={label} style={{ background: '#f3f3f0', borderRadius: 8, padding: '10px 14px' }}>
            <div style={{ fontSize: 11, color: '#888', marginBottom: 4 }}>{label}</div>
            <div style={{ fontSize: 22, fontWeight: 500 }}>{value}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16, borderBottom: '1px solid #e0dfd8', paddingBottom: 8 }}>
        {['grid', 'reward', 'actions', 'leaderboard'].map(tab => (
          <button key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              border: 'none',
              background: activeTab === tab ? '#1a1a1a' : 'transparent',
              color:  activeTab === tab ? '#fff' : '#666',
              borderRadius: 6, padding: '5px 14px', fontSize: 12
            }}>
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      <div className="card">
        {activeTab === 'grid'        && <GridTopology  observation={observation} />}
        {activeTab === 'reward'      && <RewardChart   history={history} />}
        {activeTab === 'actions'     && <ActionLog     history={history} faults={faults} />}
        {activeTab === 'leaderboard' && <Leaderboard   taskId={taskId} />}
      </div>

    </div>
  );
}