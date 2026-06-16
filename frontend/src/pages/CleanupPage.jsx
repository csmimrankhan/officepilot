import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || ''

async function authFetch(url, options = {}) {
  const token = localStorage.getItem('access_token')
  const headers = { ...options.headers }
  if (token) headers['Authorization'] = `Bearer ${token}`
  const res = await fetch(url, { ...options, headers })
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`)
  return res.json()
}

function formatSize(bytes) {
  if (bytes == null) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const STORAGE_LABELS = {
  bug_reports: 'Bug Reports',
  audit_exports: 'Audit Exports',
  browser_screenshots: 'Browser Screenshots',
  cache_dir: 'Cache Directory',
}

export default function CleanupPage() {
  const [storageUsage, setStorageUsage] = useState(null)
  const [storageLoading, setStorageLoading] = useState(true)
  const [storageError, setStorageError] = useState('')

  const [preview, setPreview] = useState(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState('')

  const [confirmed, setConfirmed] = useState(false)
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState(null)
  const [runError, setRunError] = useState('')

  const loadStorage = async () => {
    setStorageLoading(true)
    setStorageError('')
    try {
      const data = await authFetch(`${API_BASE}/api/system/storage-usage`)
      setStorageUsage(data)
    } catch (err) {
      setStorageError(err.message || 'Failed to load storage usage.')
    } finally {
      setStorageLoading(false)
    }
  }

  const loadPreview = async () => {
    setPreviewLoading(true)
    setPreviewError('')
    setRunResult(null)
    setConfirmed(false)
    try {
      const data = await authFetch(`${API_BASE}/api/system/cleanup-preview`)
      setPreview(data)
    } catch (err) {
      setPreviewError(err.message || 'Failed to load cleanup preview.')
    } finally {
      setPreviewLoading(false)
    }
  }

  const runCleanup = async () => {
    setRunning(true)
    setRunError('')
    setRunResult(null)
    try {
      const data = await authFetch(`${API_BASE}/api/system/cleanup-run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed: true }),
      })
      setRunResult(data)
    } catch (err) {
      setRunError(err.message || 'Cleanup failed.')
    } finally {
      setRunning(false)
    }
  }

  useEffect(() => { loadStorage() }, [])

  const totalPreviewBytes = preview && preview.items
    ? preview.items.reduce((sum, item) => sum + (item.size || 0), 0)
    : 0

  return (
    <div>
      <style>{`
        .cleanup-page { max-width: 960px; margin: 0 auto; padding: 24px; }
        .cleanup-page h2 { margin: 0 0 4px 0; font-size: 22px; color: #1a1f36; }
        .cleanup-page h3 { margin: 24px 0 12px 0; font-size: 16px; color: #1a1f36; }
        .cleanup-page .subtle { color: #6b7294; font-size: 13px; }
        .cleanup-page .page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
        .cleanup-page .page-header h2 { margin: 0; }
        .storage-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-bottom: 24px; }
        .storage-card { border: 1px solid #d8dce6; border-radius: 8px; padding: 16px; background: #fff; }
        .storage-card h4 { margin: 0 0 8px 0; font-size: 14px; color: #1a1f36; }
        .storage-card .stat { font-size: 12px; color: #6b7294; margin: 2px 0; }
        .storage-card .stat strong { color: #1a1f36; }
        .cleanup-page .data-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 16px; }
        .cleanup-page .data-table th { text-align: left; padding: 8px 10px; background: #f4f6fa; border-bottom: 2px solid #d8dce6; color: #1a1f36; font-weight: 600; }
        .cleanup-page .data-table td { padding: 8px 10px; border-bottom: 1px solid #e8ebf2; color: #1a1f36; }
        .cleanup-page .data-table tr:hover td { background: #f8f9fd; }
        .cleanup-page .btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 18px; font-size: 13px; font-weight: 500; border: 1px solid transparent; border-radius: 6px; cursor: pointer; }
        .cleanup-page .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .cleanup-page .btn-primary { background: #2a5cff; color: #fff; border-color: #2a5cff; }
        .cleanup-page .btn-primary:hover:not(:disabled) { background: #1a4ce0; }
        .cleanup-page .btn-secondary { background: #fff; color: #1a1f36; border-color: #d8dce6; }
        .cleanup-page .btn-secondary:hover:not(:disabled) { background: #f4f6fa; }
        .cleanup-page .btn-danger { background: #e04f4f; color: #fff; border-color: #e04f4f; }
        .cleanup-page .btn-danger:hover:not(:disabled) { background: #cc3d3d; }
        .cleanup-page .warning-box { background: #fff8e6; border: 1px solid #f5d68a; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px; font-size: 13px; color: #7a5c00; }
        .cleanup-page .alert { padding: 10px 14px; border-radius: 6px; font-size: 13px; margin-bottom: 12px; }
        .cleanup-page .alert-error { background: #fef0ef; border: 1px solid #f5a3a3; color: #b33; }
        .cleanup-page .alert-success { background: #e8f7ed; border: 1px solid #8fd6a5; color: #1a6e3a; }
        .cleanup-page .checkbox-row { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 16px; font-size: 13px; color: #1a1f36; }
        .cleanup-page .checkbox-row input { margin-top: 2px; }
        .cleanup-page .summary-line { font-size: 13px; color: #6b7294; margin: 8px 0 16px 0; }
        .cleanup-page .result-box { background: #fff; border: 1px solid #d8dce6; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
        .cleanup-page .result-box h4 { margin: 0 0 8px 0; font-size: 14px; color: #1a1f36; }
        .cleanup-page .result-box p { margin: 4px 0; font-size: 13px; color: #1a1f36; }
        .cleanup-page .retry-link { color: #2a5cff; cursor: pointer; text-decoration: underline; }
        .cleanup-page .retry-link:hover { color: #1a4ce0; }
        .cleanup-page .section { margin-bottom: 32px; }
        .cleanup-page .toolbar { display: flex; align-items: center; gap: 12px; margin-top: 16px; }
      `}</style>
      <div className="cleanup-page">
        <div className="page-header">
          <div>
            <h2>Data Cleanup &amp; Retention</h2>
            <span className="subtle">Remove temporary files, demo data, and old exports</span>
          </div>
          <button type="button" className="btn btn-secondary" onClick={loadStorage}>
            Refresh
          </button>
        </div>

        <div className="section">
          <h3>Storage Usage</h3>
          {storageLoading && <div className="subtle">Loading storage usage…</div>}
          {storageError && (
            <div className="alert alert-error">
              {storageError}
              <span className="retry-link" onClick={loadStorage}> Retry</span>
            </div>
          )}
          {storageUsage && (
            <div className="storage-grid">
              {Object.entries(STORAGE_LABELS).map(([key, label]) => {
                const area = storageUsage[key] || storageUsage.areas?.[key] || {}
                return (
                  <div className="storage-card" key={key}>
                    <h4>{label}</h4>
                    <div className="stat">Size: <strong>{formatSize(area.size || area.size_bytes)}</strong></div>
                    <div className="stat">Files: <strong>{area.file_count ?? area.count ?? 0}</strong></div>
                    <div className="stat">Path: <strong style={{ wordBreak: 'break-all' }}>{area.path || '—'}</strong></div>
                  </div>
                )
              })}
            </div>
          )}
          {!storageLoading && !storageError && !storageUsage && (
            <div className="subtle">No storage data available.</div>
          )}
        </div>

        <div className="section">
          <h3>Cleanup Preview</h3>
          <div className="toolbar">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={loadPreview}
              disabled={previewLoading}
            >
              {previewLoading ? 'Loading…' : 'Preview Cleanup'}
            </button>
          </div>
          {previewLoading && <div className="subtle" style={{ marginTop: 12 }}>Calculating items to remove…</div>}
          {previewError && (
            <div className="alert alert-error" style={{ marginTop: 12 }}>
              {previewError}
              <span className="retry-link" onClick={loadPreview}> Retry</span>
            </div>
          )}
          {preview && (
            <>
              {preview.items && preview.items.length > 0 ? (
                <>
                  <table className="data-table" style={{ marginTop: 12 }}>
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Path</th>
                        <th>Size</th>
                        <th>Reason</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.items.map((item, idx) => (
                        <tr key={idx}>
                          <td>{item.type || '—'}</td>
                          <td style={{ wordBreak: 'break-all', maxWidth: 300 }}>
                            {item.path || item.file_path || '—'}
                          </td>
                          <td>{formatSize(item.size || item.size_bytes)}</td>
                          <td>{item.reason || item.retention_reason || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="summary-line">
                    {preview.items.length} item{preview.items.length !== 1 ? 's' : ''} found,
                    estimating {formatSize(totalPreviewBytes)} to free.
                  </div>
                </>
              ) : (
                <div className="subtle" style={{ marginTop: 12 }}>No removable items found.</div>
              )}
            </>
          )}
        </div>

        {preview && preview.items && preview.items.length > 0 && (
          <div className="section">
            <h3>Run Cleanup</h3>
            <div className="warning-box">
              This will remove the items shown in the preview. Real invoices, audit logs,
              backups, and version history are protected.
            </div>
            {runError && <div className="alert alert-error">{runError}</div>}
            {runResult && (
              <div className="result-box">
                <h4>Cleanup Completed</h4>
                <p>Removed: <strong>{runResult.removed_count ?? runResult.removed ?? 0}</strong> item(s)</p>
                <p>Freed: <strong>{formatSize(runResult.freed_bytes ?? runResult.freed ?? 0)}</strong></p>
                {runResult.details && runResult.details.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {runResult.details.map((d, i) => (
                      <p key={i} className="subtle" style={{ margin: '2px 0' }}>{d}</p>
                    ))}
                  </div>
                )}
              </div>
            )}
            {!runResult && (
              <>
                <label className="checkbox-row">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(e) => setConfirmed(e.target.checked)}
                  />
                  <span>
                    I understand that old demo data, bug report packages, and audit exports
                    will be removed
                  </span>
                </label>
                <button
                  type="button"
                  className="btn btn-danger"
                  disabled={!confirmed || running}
                  onClick={runCleanup}
                >
                  {running ? 'Running…' : 'Run Cleanup'}
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
