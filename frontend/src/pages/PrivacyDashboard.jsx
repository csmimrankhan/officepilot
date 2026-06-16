import { useEffect, useState, useCallback } from 'react'
import { api, formatDateTime } from '../api.js'

function StatusPill({ ok, label }) {
  return (
    <span className={`badge ${ok ? 'ok' : 'bad'}`}>
      {ok ? '● ' : '○ '}{label}
    </span>
  )
}

function formatBytes(n) {
  if (!n) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let f = Number(n)
  let i = 0
  while (f >= 1024 && i < units.length - 1) {
    f /= 1024
    i += 1
  }
  return `${f.toFixed(1)} ${units[i]}`
}

export default function PrivacyDashboard() {
  const [status, setStatus] = useState(null)
  const [storage, setStorage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionMsg, setActionMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [lastExport, setLastExport] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [s, st] = await Promise.all([api.localStatus(), api.localStorage()])
      setStatus(s)
      setStorage(st)
    } catch (err) {
      setError(err.message || 'Failed to load privacy dashboard.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const onExport = async () => {
    setBusy(true)
    setActionMsg('')
    try {
      const res = await api.exportAudit(1000)
      setLastExport(res)
      setActionMsg(`Exported ${res.rows_exported} audit row(s) to ${res.path}.`)
    } catch (err) {
      setActionMsg('')
      setError(err.message || 'Failed to export audit log.')
    } finally {
      setBusy(false)
    }
  }

  const onClearCache = async () => {
    if (!confirm('Clear the cache directory? This cannot be undone. Originals, exports, and audit logs are not touched.')) return
    setBusy(true)
    setActionMsg('')
    try {
      const res = await api.clearLocalCache(true)
      if (res.cleared) {
        setActionMsg(
          `Cleared ${res.removed_files} cache file(s) (${res.removed_bytes_human || formatBytes(res.removed_bytes)}).`
        )
        await load()
      } else {
        setActionMsg(res.message || 'Cache not cleared.')
      }
    } catch (err) {
      setError(err.message || 'Failed to clear cache.')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <div className="subtle">Loading privacy dashboard…</div>
  if (error) return <div className="alert error">{error}</div>
  if (!status || !storage) return <div className="muted">No data.</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Privacy &amp; Local Data</h2>
          <span className="subtle">Phase 7 · local-first transparency</span>
        </div>
        <button type="button" className="secondary" onClick={load} disabled={busy}>
          Refresh
        </button>
      </div>

      <div className="alert info">
        <strong>Local-first.</strong> All invoice data, exports, and
        audit logs stay on this machine. No cloud AI is used in any
        phase of this build. You can confirm every directory below and
        export the full audit trail at any time.
      </div>

      <h3>Connected accounts</h3>
      <table className="data-table">
        <tbody>
          <tr>
            <th>Gmail</th>
            <td>
              <StatusPill ok={status.gmail_configured} label={status.gmail_configured ? 'configured' : 'not configured'} />
              <span className="subtle"> · reads from your local OAuth tokens; never auto-uploads.</span>
            </td>
          </tr>
          <tr>
            <th>Cloud AI</th>
            <td>
              <StatusPill ok={false} label="disabled" />
              <span className="subtle"> · no external LLM or OCR cloud is contacted in this build.</span>
            </td>
          </tr>
          <tr>
            <th>OCR</th>
            <td>
              <StatusPill ok={status.ocr_enabled} label={status.ocr_enabled ? 'local Tesseract enabled' : 'disabled'} />
              <span className="subtle"> · runs offline on your machine.</span>
            </td>
          </tr>
        </tbody>
      </table>

      <h3>Local data usage</h3>
      <div className="run-summary">
        <div>
          <div className="subtle">Protected (kept forever)</div>
          <div>{storage.protected_total_human}</div>
        </div>
        <div>
          <div className="subtle">Cache (safe to clear)</div>
          <div>{storage.cache_total_human}</div>
        </div>
        <div>
          <div className="subtle">Data dir</div>
          <code className="mono">{storage.data_dir}</code>
        </div>
        <div>
          <div className="subtle">Storage root</div>
          <code className="mono">{storage.storage_root}</code>
        </div>
      </div>

      <table className="data-table">
        <thead>
          <tr>
            <th>Directory</th>
            <th>Path</th>
            <th>Files</th>
            <th>Size</th>
            <th>Protected?</th>
          </tr>
        </thead>
        <tbody>
          {storage.dirs.map((d) => (
            <tr key={d.name}>
              <td><code className="mono">{d.name}</code></td>
              <td><code className="mono">{d.path}</code></td>
              <td className="subtle">{d.file_count}</td>
              <td className="subtle">{formatBytes(d.total_bytes)}</td>
              <td>{d.protected
                ? <StatusPill ok={true} label="yes" />
                : <span className="subtle">no (cache)</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Actions</h3>
      {actionMsg && <div className="alert success">{actionMsg}</div>}

      <div className="toolbar" style={{ flexWrap: 'wrap' }}>
        <button
          type="button"
          className="primary"
          onClick={onExport}
          disabled={busy}
        >
          {busy ? 'Working…' : 'Export audit log to CSV'}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={onClearCache}
          disabled={busy}
        >
          Clear cache
        </button>
      </div>

      {lastExport && (
        <p className="subtle">
          Last export: <code className="mono">{lastExport.path}</code> ·{' '}
          {lastExport.rows_exported} row(s) · limit {lastExport.limit}
        </p>
      )}

      <h3>How the privacy model works</h3>
      <ul>
        <li>
          <strong>Invoice originals</strong> are written to
          <code className="mono"> {status.storage_root}\invoices</code> and
          never leave your machine.
        </li>
        <li>
          <strong>Excel exports</strong> go to
          <code className="mono"> {status.storage_root}\exports</code>.
        </li>
        <li>
          <strong>Audit logs</strong> live in the SQLite database and
          are exported to <code className="mono">{status.data_dir}\audit</code> on demand.
        </li>
        <li>
          <strong>Workflow recordings</strong> (Phase 9, not yet
          enabled) will live in <code className="mono">{status.data_dir}\recordings</code>.
        </li>
        <li>
          <strong>Cache</strong> is the only directory that can be
          cleared from the UI; it is recreated automatically on the
          next run.
        </li>
      </ul>
    </div>
  )
}
