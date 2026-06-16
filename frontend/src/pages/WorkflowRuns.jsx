import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  api,
  formatDateTime,
  WORKFLOW_STATUS_LABELS
} from '../api.js'

const STATUS_FILTERS = [
  { value: '', label: 'All' },
  { value: 'awaiting_approval', label: 'Awaiting Approval' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'cancelled', label: 'Cancelled' }
]

export default function WorkflowRuns() {
  const [runs, setRuns] = useState([])
  const [graphs, setGraphs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [graphFilter, setGraphFilter] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [runsRes, graphsRes] = await Promise.all([
        api.listWorkflowRuns({
          status: statusFilter || undefined,
          workflow_name: graphFilter || undefined,
          limit: 100
        }),
        graphs.length ? Promise.resolve({ graphs }) : api.listWorkflowGraphs()
      ])
      setRuns(runsRes.runs || [])
      if (graphsRes && Array.isArray(graphsRes.graphs)) {
        setGraphs(graphsRes.graphs)
      }
    } catch (err) {
      setError(err.message || 'Failed to load workflow runs.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [statusFilter, graphFilter])

  return (
    <div>
      <div className="page-header">
        <h2>Workflow Runs</h2>
        <span className="subtle">{runs.length} run(s)</span>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="toolbar" style={{ flexWrap: 'wrap' }}>
        <label className="subtle">
          Status:&nbsp;
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            {STATUS_FILTERS.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </label>
        <label className="subtle">
          Workflow:&nbsp;
          <select
            value={graphFilter}
            onChange={(e) => setGraphFilter(e.target.value)}
          >
            <option value="">All</option>
            {graphs.map((g) => (
              <option key={g.name} value={g.name}>{g.name}</option>
            ))}
          </select>
        </label>
        <button type="button" className="secondary" onClick={load} disabled={loading}>
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {loading && runs.length === 0 ? (
        <div className="subtle">Loading…</div>
      ) : runs.length === 0 ? (
        <div className="muted">No workflow runs match these filters.</div>
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
              <th>Completed</th>
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
                <td className="subtle">{formatDateTime(r.completed_at) || '—'}</td>
                <td>
                  <Link to={`/workflows/${r.id}`} className="secondary" style={{ padding: '4px 10px' }}>
                    Open
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
