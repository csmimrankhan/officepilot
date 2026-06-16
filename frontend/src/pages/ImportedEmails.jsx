import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatDateTime, IMPORT_STATUS_LABELS } from '../api.js'

const SCORE_BAR = (v) => {
  const pct = Math.max(0, Math.min(100, Math.round((Number(v) || 0) * 100)))
  return (
    <span className="confidence-bar"><span style={{ width: `${pct}%` }} /></span>
  )
}

export default function ImportedEmails() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')

  const load = async () => {
    setLoading(true); setError('')
    try {
      const data = await api.listEmailImports({ status: status || undefined, limit: 200 })
      setItems(data)
    } catch (err) {
      setError(err.message || 'Failed to load imported emails.')
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [status])

  return (
    <div>
      <div className="page-header">
        <h2>Imported Emails</h2>
        <Link to="/integrations" className="subtle">← Back to Integrations</Link>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="toolbar">
        <label htmlFor="st" className="subtle" style={{ margin: 0 }}>Status:</label>
        <select id="st" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All</option>
          <option value="candidate">Candidate</option>
          <option value="imported">Imported</option>
          <option value="duplicate">Duplicate</option>
          <option value="skipped">Skipped</option>
          <option value="error">Error</option>
        </select>
        <button className="secondary" onClick={load} disabled={loading}>Refresh</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Subject</th>
              <th>From</th>
              <th>Received</th>
              <th>Score</th>
              <th>Status</th>
              <th>Attachments</th>
              <th>Open</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan="8" className="muted">Loading…</td></tr>}
            {!loading && items.length === 0 && (
              <tr><td colSpan="8" className="muted">No imported emails yet. Run a sync from the Integrations page.</td></tr>
            )}
            {items.map((m) => (
              <tr key={m.id}>
                <td className="mono">#{m.id}</td>
                <td>{m.subject || <span className="muted">(no subject)</span>}</td>
                <td className="nowrap">{m.sender || <span className="muted">—</span>}</td>
                <td className="nowrap subtle">{formatDateTime(m.received_at)}</td>
                <td>
                  {SCORE_BAR(m.score)} {Math.round((m.score || 0) * 100)}%
                </td>
                <td><span className={`badge ${m.status}`}>{IMPORT_STATUS_LABELS[m.status] || m.status}</span></td>
                <td>{(m.attachments || []).length}</td>
                <td><Link to={`/imported-emails/${m.id}`}>Details</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
