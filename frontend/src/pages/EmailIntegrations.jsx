import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api, formatDateTime } from '../api.js'

export default function EmailIntegrations() {
  const location = useLocation()
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [lastSync, setLastSync] = useState(null)
  const [report, setReport] = useState(null)

  const load = async () => {
    setError('')
    try {
      const s = await api.gmailStatus()
      setStatus(s)
    } catch (err) {
      setError(err.message || 'Failed to load Gmail status.')
    }
  }

  useEffect(() => { load() }, [])

  // Show a success banner if we just returned from the OAuth callback.
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    if (params.get('gmail') === 'connected') {
      setLastSync(new Date())
      load()
    }
  }, [location.search])

  const onConnect = async () => {
    setError(''); setBusy(true)
    try {
      const { authorization_url } = await api.gmailConnect()
      window.location.assign(authorization_url)
    } catch (err) {
      setError(err.message || 'Failed to start Gmail connection.')
      setBusy(false)
    }
  }

  const onSync = async () => {
    setError(''); setBusy(true); setReport(null)
    try {
      const r = await api.gmailSync('user')
      setReport(r)
      setLastSync(new Date())
    } catch (err) {
      setError(err.message || 'Sync failed.')
    } finally { setBusy(false) }
  }

  const onDisconnect = async () => {
    if (!window.confirm('Disconnect Gmail? Existing invoices are kept; future syncs will be disabled.')) return
    setError(''); setBusy(true)
    try {
      await api.gmailDisconnect('user')
      await load()
    } catch (err) {
      setError(err.message || 'Disconnect failed.')
    } finally { setBusy(false) }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Email Integrations</h2>
        <Link to="/imported-emails" className="subtle">View imported emails →</Link>
      </div>

      {error && <div className="alert error">{error}</div>}
      {lastSync && status?.connected && (
        <div className="alert success">
          Gmail is connected. Last sync at {formatDateTime(lastSync)}.
        </div>
      )}

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Gmail (read-only)</h3>
        {!status && <div className="muted">Loading…</div>}
        {status && (
          <>
            <div className="grid-2">
              <div>
                <label>Connection</label>
                <div>
                  {status.connected ? (
                    <span className="badge approved">Connected</span>
                  ) : status.configured ? (
                    <span className="badge pending">Not connected</span>
                  ) : (
                    <span className="badge needs_review">Not configured</span>
                  )}
                </div>
              </div>
              <div>
                <label>Account</label>
                <div>{status.account?.email || '—'}</div>
              </div>
              <div>
                <label>Connected since</label>
                <div>{formatDateTime(status.account?.connected_at) || '—'}</div>
              </div>
              <div>
                <label>Scopes requested</label>
                <div className="mono subtle">
                  {(status.scopes || []).map(s => s.split('/').pop()).join(', ')}
                </div>
              </div>
            </div>

            {status.note && <div className="alert info" style={{ marginTop: 12 }}>{status.note}</div>}

            <div className="toolbar" style={{ marginTop: 12, flexWrap: 'wrap' }}>
              {!status.connected ? (
                <button onClick={onConnect} disabled={busy || !status.configured}>
                  Connect Gmail
                </button>
              ) : (
                <>
                  <button onClick={onSync} disabled={busy}>
                    {busy ? 'Syncing…' : 'Sync Invoice Emails'}
                  </button>
                  <button className="danger" onClick={onDisconnect} disabled={busy}>
                    Disconnect
                  </button>
                </>
              )}
            </div>

            {report && (
              <div style={{ marginTop: 12 }}>
                <h4 style={{ marginBottom: 6 }}>Last sync report</h4>
                <table>
                  <tbody>
                    <tr><th>Candidates</th><td>{report.candidates}</td></tr>
                    <tr><th>Imported</th><td>{report.imported}</td></tr>
                    <tr><th>Duplicates</th><td>{report.duplicates}</td></tr>
                    <tr><th>Skipped</th><td>{report.skipped}</td></tr>
                    <tr><th>Errors</th><td>{report.errors}</td></tr>
                    <tr><th>New invoices</th><td className="mono">{(report.invoice_ids || []).join(', ') || '—'}</td></tr>
                  </tbody>
                </table>
              </div>
            )}

            <details style={{ marginTop: 12 }}>
              <summary>Security notes</summary>
              <ul>
                <li>We request only the <code>gmail.readonly</code> scope.</li>
                <li>We never send, delete, modify, mark-as-read, or archive emails.</li>
                <li>OAuth tokens are encrypted at rest with Fernet (AES-128 + HMAC).</li>
                <li>Disconnect removes stored tokens immediately.</li>
              </ul>
            </details>
          </>
        )}
      </div>
    </div>
  )
}
