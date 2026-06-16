import { useEffect, useState } from 'react'
import { api, formatDateTime } from '../api.js'

export default function AuditLogs() {
  const [logs, setLogs] = useState([])
  const [error, setError] = useState('')
  const [action, setAction] = useState('')
  const [entityType, setEntityType] = useState('')

  const load = async () => {
    setError('')
    try {
      const data = await api.listAuditLogs({
        action: action || undefined,
        entity_type: entityType || undefined,
        limit: 500
      })
      setLogs(data)
    } catch (err) {
      setError(err.message || 'Failed to load.')
    }
  }

  useEffect(() => { load() }, [action, entityType])

  return (
    <div>
      <div className="page-header">
        <h2>Audit Logs</h2>
        <span className="subtle">{logs.length} entries (newest first)</span>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="toolbar">
        <label htmlFor="action" className="subtle" style={{ margin: 0 }}>Action:</label>
        <select id="action" value={action} onChange={(e) => setAction(e.target.value)}>
          <option value="">All</option>
          <option value="upload">upload</option>
          <option value="upload.duplicate">upload.duplicate</option>
          <option value="extraction">extraction</option>
          <option value="edit">edit</option>
          <option value="approve">approve</option>
          <option value="reject">reject</option>
          <option value="export.excel">export.excel</option>
        </select>
        <label htmlFor="et" className="subtle" style={{ margin: 0 }}>Entity:</label>
        <select id="et" value={entityType} onChange={(e) => setEntityType(e.target.value)}>
          <option value="">All</option>
          <option value="invoice">invoice</option>
        </select>
        <button className="secondary" onClick={load}>Refresh</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>Time (UTC stored)</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Details</th>
              <th>Extra</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 && <tr><td colSpan="6" className="muted">No audit log entries.</td></tr>}
            {logs.map((l) => (
              <tr key={l.id}>
                <td className="nowrap subtle">{formatDateTime(l.timestamp)}</td>
                <td>{l.actor}</td>
                <td className="mono">{l.action}</td>
                <td className="mono">{l.entity_type}{l.entity_id != null ? `#${l.entity_id}` : ''}</td>
                <td>{l.details || <span className="muted">—</span>}</td>
                <td>
                  <code className="subtle" style={{ fontSize: 11 }}>
                    {l.extra_json && Object.keys(l.extra_json).length > 0 ? JSON.stringify(l.extra_json) : '—'}
                  </code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
