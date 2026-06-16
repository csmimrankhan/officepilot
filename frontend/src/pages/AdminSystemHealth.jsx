import { useState, useEffect } from 'react'
import { api } from '../api.js'

const COMPONENTS = [
  { key: 'backend', label: 'Backend' },
  { key: 'database', label: 'Database' },
  { key: 'sidecar', label: 'Sidecar' },
  { key: 'updater', label: 'Updater' },
  { key: 'gmail_readonly', label: 'Gmail Read-Only' },
  { key: 'excel_automation', label: 'Excel Automation' },
  { key: 'workflow_recorder', label: 'Workflow Recorder' },
  { key: 'browser_automation', label: 'Browser Automation' },
  { key: 'local_whisper', label: 'Local Speech-to-Text' },
  { key: 'llm_provider', label: 'LLM Provider' },
]

function statusColor(status) {
  const ok = ['ok', 'enabled', 'ready', 'bundled', 'configured']
  const warn = ['not_configured', 'system-python', 'warning']
  if (ok.includes(status)) return '#16a34a'
  if (warn.includes(status)) return '#d97706'
  if (status === 'error' || !status) return '#dc2626'
  return '#94a3b8'
}

function ComponentCard({ label, data }) {
  const status = data?.status || 'unknown'
  return (
    <div className="card admin-health-card">
      <div className="admin-health-card-header">
        <strong>{label}</strong>
        <span className="admin-status-badge" style={{ background: statusColor(status) }}>{status}</span>
      </div>
      <div className="admin-comp-detail">
        {!data && <span className="muted">No data</span>}
        {data?.error && <span style={{ color: '#dc2626' }}>Error: {data.error}</span>}
        {data && !data.error && (
          <>
            {data.bundled !== undefined && <div>Mode: {data.bundled ? 'Bundled sidecar' : 'System Python'}</div>}
            {data.configured !== undefined && <div>Configured: {data.configured ? 'Yes' : 'No'}</div>}
            {data.enabled !== undefined && <div>Enabled: {data.enabled ? 'Yes' : 'No'}</div>}
            {data.provider && <div>Provider: {data.provider}</div>}
            {data.cloud_ai_allowed !== undefined && <div>Cloud AI: {data.cloud_ai_allowed ? 'Allowed' : 'Disabled'}</div>}
            {data.cli_found !== undefined && <div>CLI: {data.cli_found ? 'Found' : 'Not found'}</div>}
            {data.model_found !== undefined && <div>Model: {data.model_found ? 'Found' : 'Not found'}</div>}
            {data.message && <div className="muted" style={{ marginTop: 4 }}>{data.message}</div>}
          </>
        )}
      </div>
    </div>
  )
}

export default function AdminSystemHealth() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    api.getAdminSystemHealth()
      .then(r => { if (!cancelled) setData(r) })
      .catch(e => { if (!cancelled) setError(e?.message || 'Failed to load system health') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div className="page-header-info">
            <h2>System Health</h2>
            <p className="page-header-subtitle">Monitor OfficePilot AI local services and components.</p>
          </div>
        </div>
        <div className="loading-state"><div className="spinner" /><p>Loading system health...</p></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div className="page-header-info">
            <h2>System Health</h2>
            <p className="page-header-subtitle">Monitor OfficePilot AI local services and components.</p>
          </div>
        </div>
        <div className="error-state">
          <h3>Failed to load</h3>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div className="page-header-info">
            <h2>System Health</h2>
            <p className="page-header-subtitle">Monitor OfficePilot AI local services and components.</p>
          </div>
        </div>
        <div className="empty-state"><p className="subtle">No system health data available.</p></div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-header-info">
          <h2>System Health</h2>
          <p className="page-header-subtitle">Monitor OfficePilot AI local services and components.</p>
        </div>
        <div className="page-header-actions">
          <span className="badge badge--info">v{data.version || '?'}</span>
          <span className="badge badge--info">Phase {data.phase || '?'}</span>
          {data.timestamp && <span className="badge badge--muted">{new Date(data.timestamp).toLocaleString()}</span>}
        </div>
      </div>
      <div className="admin-health-grid">
        {COMPONENTS.map(c => (
          <ComponentCard key={c.key} label={c.label} data={data[c.key]} />
        ))}
      </div>
    </div>
  )
}
