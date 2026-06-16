import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  api,
  formatDateTime,
  WORKFLOW_STATUS_LABELS
} from '../api.js'

/**
 * Lists every workflow run whose status is `awaiting_approval` and
 * gives the user a one-click path to the detail page (where they
 * can approve/reject).
 */
export default function PendingApprovals() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.listWorkflowRuns({ status: 'awaiting_approval', limit: 100 })
      setRuns(res.runs || [])
    } catch (err) {
      setError(err.message || 'Failed to load pending approvals.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div>
      <div className="page-header">
        <h2>Pending Approvals</h2>
        <span className="subtle">{runs.length} awaiting</span>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="toolbar">
        <button type="button" className="secondary" onClick={load} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {loading && runs.length === 0 ? (
        <div className="subtle">Loading…</div>
      ) : runs.length === 0 ? (
        <div className="muted">No workflow runs are currently awaiting approval.</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Workflow</th>
              <th>Status</th>
              <th>Current node</th>
              <th>Actor</th>
              <th>Started</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td>#{r.id}</td>
                <td><code className="mono">{r.workflow_name}</code></td>
                <td>
                  <span className={`badge ${r.status}`}>
                    {WORKFLOW_STATUS_LABELS[r.status] || r.status}
                  </span>
                </td>
                <td><code className="mono">{r.current_node || '—'}</code></td>
                <td>{r.actor || '—'}</td>
                <td className="subtle">{formatDateTime(r.started_at) || '—'}</td>
                <td>
                  <Link to={`/workflows/${r.id}`} className="primary" style={{ padding: '4px 10px' }}>
                    Review
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
