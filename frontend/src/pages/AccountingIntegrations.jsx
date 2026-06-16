import { useEffect, useState, useCallback } from 'react'
import { api } from '../api.js'

export default function AccountingIntegrations() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [qbSync, setQbSync] = useState(null)
  const [syncing, setSyncing] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const s = await api.getAccountingStatus()
      setStatus(s)
      if (s?.quickbooks_connected) {
        api.quickbooksSyncStatus().then(setQbSync).catch(() => {})
      }
    } catch (err) {
      setError(err.message || 'Failed to load accounting status.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const connectQuickBooks = async () => {
    setError('')
    setMessage('')
    try {
      const result = await api.quickbooksConnect()
      window.open(result.authorization_url, '_blank')
      setMessage('QuickBooks authorization opened in a new tab.')
    } catch (err) {
      setError(err.message || 'Failed to start QuickBooks connection.')
    }
  }

  const connectXero = async () => {
    setError('')
    setMessage('')
    try {
      const result = await api.xeroConnect()
      window.open(result.authorization_url, '_blank')
      setMessage('Xero authorization opened in a new tab.')
    } catch (err) {
      setError(err.message || 'Failed to start Xero connection.')
    }
  }

  const disconnect = async (provider) => {
    setError('')
    setMessage('')
    try {
      const conn = status?.[`${provider}_connection`]
      if (!conn) return
      await api.disconnectAccountingConnection(conn.id)
      setMessage(`${provider} disconnected.`)
      await load()
    } catch (err) {
      setError(err.message || `Failed to disconnect ${provider}.`)
    }
  }

  if (loading && !status) {
    return (
      <div>
        <div className="page-header"><h2>Accounting Integrations</h2></div>
        {error ? <div className="alert error">{error}</div> : <div className="subtle">Loading…</div>}
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>Accounting Integrations</h2>
        <span className="subtle">QuickBooks + Xero sync (Phase 13)</span>
      </div>
      {error && <div className="alert error">{error}</div>}
      {message && <div className="alert success">{message}</div>}
      <div className="card">
        <h3>Sync Settings</h3>
        <div className="field-row">
          <span>Sync enabled:</span>
          <span className={`badge ${status?.sync_enabled ? 'ok' : 'subtle'}`}>{status?.sync_enabled ? 'Yes' : 'No'}</span>
        </div>
        <div className="field-row">
          <span>Draft-only mode:</span>
          <span className={`badge ${status?.draft_only ? 'ok' : 'subtle'}`}>{status?.draft_only ? 'Yes' : 'No'}</span>
        </div>
        <div className="field-row">
          <span>Block duplicates:</span>
          <span className={`badge ${status?.block_duplicates ? 'ok' : 'subtle'}`}>{status?.block_duplicates ? 'Yes' : 'No'}</span>
        </div>
      </div>
      <div className="card">
        <h3>QuickBooks</h3>
        <p className="subtle">
          {status?.quickbooks_configured
            ? `Client ID configured. Environment: ${status?.quickbooks_env || 'sandbox'}.`
            : 'QuickBooks OAuth is not configured. Set QUICKBOOKS_CLIENT_ID and QUICKBOOKS_CLIENT_SECRET in the environment.'}
        </p>
        <div className="field-row">
          <span>Status:</span>
          <span className={`badge ${status?.quickbooks_connected ? 'ok' : 'subtle'}`}>
            {status?.quickbooks_connected ? `Connected (${status?.quickbooks_env || 'sandbox'})` : 'Not connected'}
          </span>
        </div>
        {status?.quickbooks_connection && (
          <div className="modal-grid">
            <div><span className="subtle">Company:</span> <code className="mono">{status.quickbooks_connection.company_name || '—'}</code></div>
            <div><span className="subtle">Realm ID:</span> <code className="mono">{status.quickbooks_connection.realm_id ? status.quickbooks_connection.realm_id.substring(0, 16) + '…' : '—'}</code></div>
          </div>
        )}
        <div className="toolbar">
          {status?.quickbooks_connected
            ? <>
                <button className="secondary" onClick={() => disconnect('quickbooks')}>Disconnect</button>
                <button className="primary" onClick={async () => { setSyncing(true); setError(''); try { const r = await api.quickbooksSync(); setQbSync(r); setMessage(`Synced: ${r.accounts_count} accounts, ${r.customers_count} customers, ${r.invoices_count} invoices`); } catch (e) { setError(e.message); } finally { setSyncing(false); await load(); } }} disabled={syncing}>
                  {syncing ? 'Syncing...' : 'Sync Now'}
                </button>
              </>
            : <button className="primary" onClick={connectQuickBooks} disabled={!status?.quickbooks_configured}>Connect QuickBooks</button>
          }
        </div>
        {qbSync?.synced && (
          <div className="sync-stats">
            <h4>Synced Data</h4>
            <div className="field-row"><span>Accounts:</span><span className="badge ok">{qbSync.accounts_count || 0}</span></div>
            <div className="field-row"><span>Customers:</span><span className="badge ok">{qbSync.customers_count || 0}</span></div>
            <div className="field-row"><span>Invoices:</span><span className="badge ok">{qbSync.invoices_count || 0}</span></div>
            {qbSync.last_sync_at && <div className="field-row"><span>Last sync:</span><span className="subtle">{new Date(qbSync.last_sync_at).toLocaleString()}</span></div>}
            {qbSync.last_error && <div className="field-row"><span className="error">Error:</span><span>{qbSync.last_error}</span></div>}
          </div>
        )}
      </div>
      <div className="card">
        <h3>Xero</h3>
        <p className="subtle">
          {status?.xero_configured
            ? `Client ID configured. Environment: ${status?.xero_env || 'demo'}.`
            : 'Xero OAuth is not configured. Set XERO_CLIENT_ID and XERO_CLIENT_SECRET in the environment.'}
        </p>
        <div className="field-row">
          <span>Status:</span>
          <span className={`badge ${status?.xero_connected ? 'ok' : 'subtle'}`}>
            {status?.xero_connected ? `Connected (${status?.xero_env || 'demo'})` : 'Not connected'}
          </span>
        </div>
        {status?.xero_connection && (
          <div className="modal-grid">
            <div><span className="subtle">Tenant:</span> <code className="mono">{status.xero_connection.company_name || '—'}</code></div>
          </div>
        )}
        <div className="toolbar">
          {status?.xero_connected
            ? <button className="secondary" onClick={() => disconnect('xero')}>Disconnect</button>
            : <button className="primary" onClick={connectXero} disabled={!status?.xero_configured}>Connect Xero</button>
          }
        </div>
      </div>
      <div className="card">
        <h3>Getting Started</h3>
        <ol className="phase-list">
          <li>Configure OAuth credentials in <code>.env</code> (or set <code>QUICKBOOKS_ENV=mock</code> / <code>XERO_ENV=mock</code> for dry-run).</li>
          <li>Connect a provider above.</li>
          <li>Go to <strong>Accounting Mappings</strong> to map vendors and categories.</li>
          <li>Open an approved invoice and click <strong>Preview QuickBooks/Xero Sync</strong>.</li>
          <li>Review the preview and approve to create a draft bill.</li>
          <li>Check <strong>Accounting Sync Logs</strong> for results and validation.</li>
        </ol>
      </div>
    </div>
  )
}
