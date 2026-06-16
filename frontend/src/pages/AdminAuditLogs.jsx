import { useState, useEffect, useCallback } from 'react'
import { api } from '../api.js'

export default function AdminAuditLogs() {
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionFilter, setActionFilter] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await api.adminListAuditLogs(page, 50, actionFilter)
      setLogs(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err.message)
    } finally { setLoading(false) }
  }, [page, actionFilter])

  useEffect(() => { load() }, [load])

  const totalPages = Math.ceil(total / 50)

  return (
    <div>
      <div className="page-header">
        <h2>Audit Logs</h2>
        <span className="subtle">Admin · {total} entries</span>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        <input placeholder="Filter by action..." value={actionFilter} onChange={e => { setActionFilter(e.target.value); setPage(1) }} style={{ flex: 1, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)' }} />
      </div>
      <div className="card">
        {loading && <p className="subtle">Loading...</p>}
        {!loading && logs.length === 0 && <p className="subtle">No audit logs found.</p>}
        {!loading && logs.length > 0 && (
          <table className="table" style={{ width: '100%', fontSize: '0.85em' }}>
            <thead>
              <tr>
                <th>Time</th>
                <th>Actor</th>
                <th>Action</th>
                <th>Type</th>
                <th>Entity ID</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id}>
                  <td style={{ whiteSpace: 'nowrap' }}>{new Date(log.timestamp).toLocaleString()}</td>
                  <td>{log.actor}</td>
                  <td><code>{log.action}</code></td>
                  <td>{log.entity_type}</td>
                  <td>{log.entity_id || '—'}</td>
                  <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>{log.details || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginTop: 16 }}>
          <button className="btn btn--sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</button>
          <span style={{ padding: '4px 12px' }}>Page {page} / {totalPages}</span>
          <button className="btn btn--sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
        </div>
      )}
    </div>
  )
}
