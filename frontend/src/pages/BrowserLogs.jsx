import { useEffect, useState, useCallback } from 'react'
import { api, formatDateTime, BROWSER_STATUS_LABELS, BROWSER_RISK_LABELS } from '../api.js'

/**
 * Browser automation log viewer. Lists recent browser action
 * runs and shows the per-step detail on click. Each row links
 * to the same data the audit log will eventually surface.
 */
export default function BrowserLogs() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [steps, setSteps] = useState([])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const rows = await api.listBrowserActions({ limit: 100 })
      setRuns(rows)
    } catch (err) {
      setError(err.message || 'Failed to load browser action runs.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const open = async (row) => {
    setSelected(row)
    try {
      const s = await api.getBrowserActionSteps(row.id)
      setSteps(s)
    } catch (err) {
      setError(err.message || 'Failed to load steps.')
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Browser Automation Logs</h2>
        <span className="subtle">{runs.length} recent runs</span>
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
        <div className="muted">No browser action runs yet. Enable browser automation and build a preview from a page or voice command.</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Source</th>
              <th>Action</th>
              <th>Target</th>
              <th>Risk</th>
              <th>Approval</th>
              <th>Status</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td>#{r.id}</td>
                <td><code className="mono">{r.source_type}</code></td>
                <td><code className="mono">{r.action_type}</code></td>
                <td className="mono" title={r.target_url || ''}>
                  {r.target_domain || '—'}
                </td>
                <td>
                  <span className={`badge ${r.risk_level}`}>
                    {BROWSER_RISK_LABELS[r.risk_level] || r.risk_level}
                  </span>
                </td>
                <td>
                  <span className={`badge ${r.approval_status === 'approved' ? 'ok' : r.approval_status === 'rejected' ? 'failed' : 'subtle'}`}>
                    {r.approval_status}
                  </span>
                </td>
                <td>
                  <span className={`badge ${r.status}`}>
                    {BROWSER_STATUS_LABELS[r.status] || r.status}
                  </span>
                </td>
                <td className="subtle">{formatDateTime(r.created_at) || '—'}</td>
                <td>
                  <button type="button" className="secondary" onClick={() => open(r)}>
                    Inspect
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selected && (
        <div className="card" style={{ marginTop: 16 }}>
          <h3>Run #{selected.id} — {selected.action_type}</h3>
          <div className="modal-grid">
            <div>
              <div className="modal-row">
                <span className="subtle">Target URL:</span>
                <code className="mono">{selected.target_url || '—'}</code>
              </div>
              <div className="modal-row">
                <span className="subtle">Domain:</span>
                <code className="mono">{selected.target_domain || '—'}</code>
              </div>
              <div className="modal-row">
                <span className="subtle">Source:</span>
                <code className="mono">{selected.source_type} {selected.source_id ? `#${selected.source_id}` : ''}</code>
              </div>
            </div>
            <div>
              <div className="modal-row">
                <span className="subtle">Status:</span>
                <span className={`badge ${selected.status}`}>
                  {BROWSER_STATUS_LABELS[selected.status] || selected.status}
                </span>
              </div>
              <div className="modal-row">
                <span className="subtle">Risk:</span>
                <span className={`badge ${selected.risk_level}`}>
                  {BROWSER_RISK_LABELS[selected.risk_level] || selected.risk_level}
                </span>
              </div>
              <div className="modal-row">
                <span className="subtle">Approval:</span>
                <code className="mono">{selected.approval_status}</code>
              </div>
            </div>
          </div>
          {selected.error_message && (
            <div className="alert error">{selected.error_message}</div>
          )}

          {steps.length > 0 ? (
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Step</th>
                  <th>Description</th>
                  <th>Value (redacted)</th>
                  <th>Status</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {steps.map((s) => (
                  <tr key={s.id}>
                    <td>{s.step_order + 1}</td>
                    <td><code className="mono">{s.step_type}</code></td>
                    <td>{s.target_description}</td>
                    <td className="mono">{s.input_value_redacted || '—'}</td>
                    <td>
                      <span className={`badge ${s.status === 'completed' ? 'ok' : s.status === 'failed' ? 'failed' : 'subtle'}`}>
                        {s.status}
                      </span>
                    </td>
                    <td className="subtle">{s.error_message || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="subtle">No per-step rows recorded for this run.</div>
          )}

          <div className="toolbar" style={{ marginTop: 12 }}>
            <button type="button" className="secondary" onClick={() => { setSelected(null); setSteps([]) }}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
