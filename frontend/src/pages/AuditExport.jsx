import { useState, useEffect } from 'react'
import { api } from '../api.js'

const LOG_TYPES = [
  { key: 'audit_logs', label: 'Audit Logs' },
  { key: 'browser_actions', label: 'Browser Actions' },
  { key: 'browser_steps', label: 'Browser Steps' },
  { key: 'accounting_sync', label: 'Accounting Sync' },
  { key: 'screen_actions', label: 'Screen Actions' },
  { key: 'screen_sessions', label: 'Screen Sessions' },
  { key: 'workflow_runs', label: 'Workflow Runs' },
  { key: 'restore_logs', label: 'Restore Logs' },
]

export default function AuditExport() {
  const [exportType, setExportType] = useState('json')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selectedTypes, setSelectedTypes] = useState(LOG_TYPES.map(t => t.key))
  const [exports, setExports] = useState([])
  const [loading, setLoading] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => {
    api.listAuditExports().then(setExports).catch(() => {})
  }, [])

  function toggleType(key) {
    setSelectedTypes(prev =>
      prev.includes(key) ? prev.filter(t => t !== key) : [...prev, key]
    )
  }

  async function doExport() {
    setLoading('Building export...')
    setMsg('')
    try {
      const r = await api.createAuditExport({
        export_type: exportType,
        date_from: dateFrom,
        date_to: dateTo,
        log_types: selectedTypes,
      })
      setMsg(`Export #${r.id} created. Status: ${r.status}`)
      api.listAuditExports().then(setExports).catch(() => {})
    } catch (e) {
      setMsg('Error: ' + e.message)
    } finally {
      setLoading('')
    }
  }

  function downloadUrl(id) {
    return api.downloadAuditExportUrl(id)
  }

  return (
    <div className="card">
      <h2>Audit Export</h2>
      {msg && <p className={msg.startsWith('Error') ? 'error' : 'success'}>{msg}</p>}
      {loading && <p className="status">{loading}</p>}

      <h3>Create Export</h3>
      <div className="field">
        <label>Export format</label>
        <select value={exportType} onChange={e => setExportType(e.target.value)}>
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
          <option value="zip">ZIP Package</option>
        </select>
      </div>
      <div className="field">
        <label>Date from</label>
        <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
      </div>
      <div className="field">
        <label>Date to</label>
        <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
      </div>
      <div className="field">
        <label>Log types to include</label>
        <div className="toggle-group">
          {LOG_TYPES.map(t => (
            <label key={t.key} className="toggle">
              <input type="checkbox" checked={selectedTypes.includes(t.key)} onChange={() => toggleType(t.key)} />
              {t.label}
            </label>
          ))}
        </div>
      </div>
      <button className="btn" onClick={doExport} disabled={loading !== ''}>
        {loading || 'Export'}
      </button>

      <h3>Previous Exports</h3>
      {exports.length === 0 && <p>No exports yet.</p>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Format</th>
            <th>Status</th>
            <th>Created</th>
            <th>Download</th>
          </tr>
        </thead>
        <tbody>
          {exports.map(e => (
            <tr key={e.id}>
              <td>{e.id}</td>
              <td>{e.export_type}</td>
              <td>{e.status}</td>
              <td>{e.created_at || '-'}</td>
              <td>
                {e.status === 'completed' && e.file_path ? (
                  <a href={downloadUrl(e.id)} className="btn btn--small" target="_blank" rel="noopener noreferrer">Download</a>
                ) : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
