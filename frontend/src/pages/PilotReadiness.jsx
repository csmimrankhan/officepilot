import { useState, useEffect } from 'react'
import { api } from '../api.js'

const STEP_STATUS_COLORS = {
  completed: { background: '#e8f5e9', color: '#2e7d32', icon: '\u2713' },
  in_progress: { background: '#fff3e0', color: '#e65100', icon: '\u25B6' },
  pending: { background: '#f5f5f5', color: '#9e9e9e', icon: '\u25CB' },
  blocked: { background: '#ffebee', color: '#c62828', icon: '\u2717' },
}

export default function PilotReadiness() {
  const [state, setState] = useState(null)
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    api.pilotReadiness().then(s => setState(s)).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <div className="card">Loading pilot readiness...</div>
  if (!state) return <div className="card">Failed to load pilot readiness.</div>

  const { items, progress_pct, overall_status, is_ready } = state

  function handleComplete(step) {
    api.completePilotReadinessStep(step).then(s => setState(s)).catch(() => {})
  }

  function handleReset() {
    if (!confirm('Reset pilot readiness checklist?')) return
    api.resetPilotReadiness().then(s => setState(s)).catch(() => {})
  }

  return (
    <div className="card">
      <h2>Pilot Readiness</h2>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <span className={`badge ${is_ready ? 'badge--ok' : 'badge--warn'}`} style={{ fontSize: '1rem', padding: '6px 16px' }}>
          {is_ready ? 'Ready for Pilot Demo' : 'Not Yet Ready'}
        </span>
        <span>Overall: <strong>{overall_status || 'unknown'}</strong></span>
      </div>

      <p>Progress: {progress_pct}%</p>
      <div style={{ height: '10px', background: '#e0e0e0', borderRadius: '5px', marginBottom: '20px' }}>
        <div style={{ height: '100%', width: `${progress_pct}%`, background: is_ready ? '#4caf50' : '#ff9800', borderRadius: '5px', transition: 'width 0.3s' }} />
      </div>

      {(items || []).length === 0 ? <p>No readiness items defined.</p> : (
        <table className="table">
          <thead><tr><th>Step</th><th>Category</th><th>Description</th><th>Status</th><th>Action</th></tr></thead>
          <tbody>
            {items.map((item, i) => {
              const sc = STEP_STATUS_COLORS[item.status] || STEP_STATUS_COLORS.pending
              return (
                <tr key={i}>
                  <td><strong>{item.step || item.id || i + 1}</strong></td>
                  <td>{item.category || '-'}</td>
                  <td><small>{item.description || item.label || ''}</small></td>
                  <td>
                    <span style={{ ...sc, padding: '2px 10px', borderRadius: '4px', fontSize: '0.85rem' }}>
                      {sc.icon} {item.status}
                    </span>
                  </td>
                  <td>
                    {item.status === 'pending' && <button className="btn btn--small" onClick={() => handleComplete(item.step || item.id)}>Complete</button>}
                    {item.status === 'blocked' && <span style={{ fontSize: '0.8rem', color: '#c62828' }}>Blocked</span>}
                    {item.status === 'completed' && <span style={{ fontSize: '0.8rem', color: '#2e7d32' }}>Done</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      <div style={{ marginTop: '16px' }}>
        <button className="btn btn--secondary" onClick={handleReset}>Reset Checklist</button>
        <button className="btn btn--secondary" style={{ marginLeft: '8px' }} onClick={load}>Refresh</button>
      </div>
    </div>
  )
}
