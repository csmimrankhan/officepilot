import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatDateTime } from '../api.js'

export default function ReplayLogs() {
  const [runs, setRuns] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    api.listReplayRuns()
      .then(setRuns)
      .catch((err) => setError(err.message))
  }, [])

  const statusClass = (s) => {
    if (s === 'completed') return 'success'
    if (s === 'failed' || s === 'stopped') return 'danger'
    if (s === 'running') return 'warning'
    return 'info'
  }

  return (
    <div>
      <div className="page-header"><h2>Workflow Replay Logs</h2></div>
      {error && <div className="alert error">{error}</div>}
      {runs.length === 0 && <div className="card muted">No replay runs yet.</div>}
      {runs.map((r) => (
        <Link to={`/recording/replay/${r.id}`} key={r.id} style={{ textDecoration: 'none' }}>
          <div className="card" style={{ marginBottom: 6, cursor: 'pointer' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong>Run #{r.id}</strong> · Workflow #{r.workflow_id} · {r.mode}
                <div className="subtle">{formatDateTime(r.started_at)}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className={`alert ${statusClass(r.status)}`} style={{ padding: '2px 8px' }}>{r.status}</span>
                {r.stopped_by && <span className="subtle">Stopped by: {r.stopped_by}</span>}
              </div>
            </div>
            {r.error_message && <div className="alert error" style={{ marginTop: 4, fontSize: '0.9em' }}>{r.error_message}</div>}
          </div>
        </Link>
      ))}
    </div>
  )
}
