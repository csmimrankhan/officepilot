import { useEffect, useState, useCallback } from 'react'
import { api, formatDateTime } from '../api.js'

export default function AccountingSyncLogs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filterProvider, setFilterProvider] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [selected, setSelected] = useState(null)
  const [validations, setValidations] = useState([])
  const [showFailed, setShowFailed] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const opts = {}
      if (filterProvider) opts.provider = filterProvider
      if (filterStatus) opts.status = filterStatus
      const rows = showFailed
        ? await api.listFailedAccountingSyncs(50)
        : await api.listAccountingSyncLogs({ ...opts, limit: 100 })
      setLogs(rows)
    } catch (err) {
      setError(err.message || 'Failed to load sync logs.')
    } finally {
      setLoading(false)
    }
  }, [filterProvider, filterStatus, showFailed])

  useEffect(() => { load() }, [load])

  const inspect = async (log) => {
    setSelected(log)
    try {
      const v = await api.getAccountingValidations(log.invoice_id)
      setValidations(v)
    } catch (_) {
      setValidations([])
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Accounting Sync Logs</h2>
        <span className="subtle">{logs.length} logs</span>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="card">
        <div className="field-row">
          <select value={filterProvider} onChange={(e) => setFilterProvider(e.target.value)} style={{ maxWidth: 160 }}>
            <option value="">All providers</option>
            <option value="quickbooks">QuickBooks</option>
            <option value="xero">Xero</option>
          </select>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)} style={{ maxWidth: 160 }}>
            <option value="">All statuses</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
            <option value="needs_review">Needs Review</option>
          </select>
          <label className="field-row">
            <input type="checkbox" checked={showFailed} onChange={(e) => setShowFailed(e.target.checked)} />
            <span>Failed / Needs review only</span>
          </label>
          <button className="secondary" onClick={load} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>
      {logs.length === 0 ? (
        <div className="card muted">No sync logs yet.</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Invoice</th>
              <th>Provider</th>
              <th>External ID</th>
              <th>Type</th>
              <th>Status</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id}>
                <td>#{l.id}</td>
                <td>#{l.invoice_id}</td>
                <td><code className="mono">{l.provider}</code></td>
                <td className="mono">{(l.external_record_id || '').substring(0, 16)}{(l.external_record_id || '').length > 16 ? '…' : '—'}</td>
                <td><code className="mono">{l.external_record_type || '—'}</code></td>
                <td><span className={`badge ${l.status === 'success' ? 'ok' : l.status === 'failed' ? 'failed' : 'warning'}`}>{l.status}</span></td>
                <td className="subtle">{formatDateTime(l.created_at)}</td>
                <td><button className="secondary" onClick={() => inspect(l)}>Inspect</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {selected && (
        <div className="card">
          <h3>Sync Log #{selected.id} — {selected.provider}</h3>
          <div className="modal-grid">
            <div>
              <div className="modal-row"><span className="subtle">Invoice:</span> <code className="mono">#{selected.invoice_id}</code></div>
              <div className="modal-row"><span className="subtle">External ID:</span> <code className="mono">{selected.external_record_id || '—'}</code></div>
              <div className="modal-row"><span className="subtle">Status:</span> <span className={`badge ${selected.status === 'success' ? 'ok' : selected.status === 'failed' ? 'failed' : 'warning'}`}>{selected.status}</span></div>
            </div>
            <div>
              <div className="modal-row"><span className="subtle">Created:</span> <span>{formatDateTime(selected.created_at)}</span></div>
              <div className="modal-row"><span className="subtle">Type:</span> <code className="mono">{selected.external_record_type || '—'}</code></div>
            </div>
          </div>
          {selected.error_message && <div className="alert error">{selected.error_message}</div>}
          {validations.length > 0 && (
            <div>
              <h4>Validations</h4>
              {validations.map((v) => (
                <div key={v.id} className="card" style={{ background: '#f9fbfd' }}>
                  <div className="field-row">
                    <span className="subtle">Status:</span>
                    <span className={`badge ${v.validation_status === 'validated' ? 'ok' : v.validation_status === 'mismatch' ? 'warning' : 'failed'}`}>
                      {v.validation_status}
                    </span>
                  </div>
                  {v.differences_json && v.differences_json.length > 0 && (
                    <table className="data-table">
                      <thead>
                        <tr><th>Field</th><th>Source</th><th>Accounting</th><th>Match</th></tr>
                      </thead>
                      <tbody>
                        {v.differences_json.map((d, i) => (
                          <tr key={i}>
                            <td><code className="mono">{d.field}</code></td>
                            <td>{d.source_value || '—'}</td>
                            <td>{d.accounting_value || '—'}</td>
                            <td>{d.match ? <span className="badge ok">✓</span> : <span className="badge failed">✗</span>}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              ))}
            </div>
          )}
          <div className="toolbar">
            <button className="secondary" onClick={() => { setSelected(null); setValidations([]) }}>Close</button>
          </div>
        </div>
      )}
    </div>
  )
}
