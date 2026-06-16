import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, formatDateTime } from '../api.js'

export default function ReplayRunner() {
  const { runId } = useParams()
  const [run, setRun] = useState(null)
  const [steps, setSteps] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = async () => {
    try {
      const [r, st] = await Promise.all([
        api.getReplayRun(runId),
        api.getReplayRunSteps(runId),
      ])
      setRun(r)
      setSteps(st)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [runId])

  const approveStep = async (stepLogId) => {
    setBusy(true); setError('')
    try {
      await api.approveReplayStep(runId, stepLogId)
      load()
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  const rejectStep = async (stepLogId) => {
    setBusy(true); setError('')
    try {
      await api.rejectReplayStep(runId, stepLogId)
      load()
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  const pause = async () => {
    try {
      await api.pauseReplay(runId)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const resume = async () => {
    try {
      await api.resumeReplay(runId)
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const emergencyStop = async () => {
    if (!window.confirm('Emergency stop — this will stop the replay immediately.')) return
    setBusy(true)
    try {
      await api.emergencyStopReplay(runId)
      load()
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  const statusClass = (s) => {
    if (s === 'completed' || s === 'approved') return 'success'
    if (s === 'failed' || s === 'rejected' || s === 'stopped') return 'danger'
    if (s === 'running') return 'warning'
    return 'info'
  }

  if (!run) return <div className="card">Loading replay…</div>

  const isActive = run.status === 'running' || run.status === 'paused'

  return (
    <div>
      <div className="page-header">
        <h2>Replay Runner <span className={`alert ${statusClass(run.status)}`} style={{ padding: '2px 8px' }}>{run.status}</span></h2>
        <Link to="/recording/runs" className="subtle">← All replay runs</Link>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="card">
        <div className="grid-3">
          <div><strong>Mode:</strong> {run.mode}</div>
          <div><strong>Started:</strong> {formatDateTime(run.started_at)}</div>
          {run.completed_at && <div><strong>Completed:</strong> {formatDateTime(run.completed_at)}</div>}
        </div>
        {run.error_message && <div className="alert error">{run.error_message}</div>}
        {isActive && (
          <div className="toolbar" style={{ marginTop: 8 }}>
            {run.status === 'paused' ? (
              <button className="primary" onClick={resume} disabled={busy}>Resume</button>
            ) : (
              <button className="secondary" onClick={pause} disabled={busy}>Pause</button>
            )}
            <button className="danger" onClick={emergencyStop} disabled={busy}>Emergency Stop</button>
          </div>
        )}
      </div>
      <div className="card">
        <h3>Step Logs</h3>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Type</th>
              <th>Status</th>
              <th>Preview</th>
              <th>Result</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {steps.length === 0 && <tr><td colSpan="6" className="muted">No step logs yet.</td></tr>}
            {steps.map((log) => (
              <tr key={log.id}>
                <td>{log.step_order}</td>
                <td><code>{log.step_type}</code></td>
                <td><span className={`alert ${statusClass(log.status)}`} style={{ padding: '1px 6px', fontSize: '0.85em' }}>{log.status}</span></td>
                <td style={{ fontSize: '0.9em' }}>
                  {log.action_preview_json?.target_description || JSON.stringify(log.action_preview_json).slice(0, 80)}
                </td>
                <td style={{ fontSize: '0.9em' }}>
                  {log.status === 'completed' ? 'OK' : log.error_message ? log.error_message : '-'}
                </td>
                <td>
                  {log.status === 'pending' && isActive && (
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="success" onClick={() => approveStep(log.id)} disabled={busy} style={{ padding: '2px 8px' }}>Approve</button>
                      <button className="danger" onClick={() => rejectStep(log.id)} disabled={busy} style={{ padding: '2px 8px' }}>Reject</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
