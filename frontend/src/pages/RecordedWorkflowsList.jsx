import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, formatDateTime } from '../api.js'

export default function RecordedWorkflowsList() {
  const [workflows, setWorkflows] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  const load = async () => {
    try {
      const data = await api.listRecordedWorkflows()
      setWorkflows(data)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [])

  const del = async (id) => {
    if (!window.confirm('Delete this workflow?')) return
    setBusy(true)
    try {
      await api.deleteRecordedWorkflow(id)
      setWorkflows((prev) => prev.filter((w) => w.id !== id))
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  const duplicate = async (id) => {
    try {
      const data = await api.duplicateRecordedWorkflow(id)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const dryRun = async (id) => {
    try {
      const data = await api.dryRunWorkflow(id)
      navigate(`/recording/replay/${data.run_id}`)
    } catch (err) {
      setError(err.message)
    }
  }

  const replay = async (id) => {
    try {
      const data = await api.replayWorkflow(id)
      navigate(`/recording/replay/${data.run_id}`)
    } catch (err) {
      setError(err.message)
    }
  }

  const riskClass = (r) => {
    if (r === 'high') return 'danger'
    if (r === 'medium') return 'warning'
    return 'info'
  }

  return (
    <div>
      <div className="page-header">
        <h2>Recorded Workflows</h2>
        <Link to="/recording/new" className="primary" style={{ padding: '6px 14px', textDecoration: 'none' }}>+ Record Workflow</Link>
      </div>
      {error && <div className="alert error">{error}</div>}
      {workflows.length === 0 && <div className="card muted">No recorded workflows yet.</div>}
      {workflows.map((w) => (
        <div className="card" key={w.id} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' }}>
            <div>
              <strong>{w.name}</strong>
              <span className={`alert ${riskClass(w.risk_level)}`} style={{ marginLeft: 8, padding: '2px 8px', fontSize: '0.85em' }}>{w.risk_level}</span>
              <span className={`alert ${w.status === 'ready' ? 'success' : 'info'}`} style={{ marginLeft: 4, padding: '2px 8px', fontSize: '0.85em' }}>{w.status}</span>
              <div className="subtle" style={{ fontSize: '0.85em', marginTop: 4 }}>
                {w.total_steps} steps · {w.source_type} · updated {formatDateTime(w.updated_at)}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              <button className="secondary" onClick={() => dryRun(w.id)} disabled={busy}>Dry Run</button>
              <button className="primary" onClick={() => replay(w.id)} disabled={busy}>Replay</button>
              <Link to={`/recording/workflows/${w.id}`} className="secondary" style={{ padding: '4px 10px', textDecoration: 'none' }}>Edit</Link>
              <button className="secondary" onClick={() => duplicate(w.id)} disabled={busy}>Duplicate</button>
              <button className="danger" onClick={() => del(w.id)} disabled={busy}>Delete</button>
            </div>
          </div>
          {w.description && <div className="subtle" style={{ marginTop: 4 }}>{w.description}</div>}
        </div>
      ))}
    </div>
  )
}
