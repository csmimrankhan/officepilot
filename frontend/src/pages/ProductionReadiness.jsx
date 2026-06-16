import { useState, useEffect } from 'react'
import { api } from '../api.js'

const STATUS_COLORS = {
  green: 'badge--ok',
  yellow: 'badge--warn',
  red: 'badge--danger',
}

export default function ProductionReadiness() {
  const [report, setReport] = useState(null)
  const [backup, setBackup] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadAll()
  }, [])

  async function loadAll() {
    setLoading(true)
    try {
      const [r, b] = await Promise.all([
        api.getSystemReadiness(),
        api.getBackupStatus(),
      ])
      setReport(r)
      setBackup(b)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card">
      <h2>Production Readiness</h2>
      {loading && <p className="status">Loading...</p>}

      <button className="btn" onClick={loadAll} disabled={loading}>Refresh</button>

      {report && (
        <div>
          <div className="status-bar">
            <span className={`badge ${STATUS_COLORS[report.overall] || ''}`}>
              Overall: {report.overall?.toUpperCase()}
            </span>
          </div>

          <div className="card-grid">
            {report.items?.map((item, i) => (
              <div key={i} className={`card card--${item.status}`}>
                <h4>{item.name}</h4>
                <span className={`badge ${STATUS_COLORS[item.status] || ''}`}>{item.status}</span>
                <p className="msg">{item.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {backup && (
        <div className="card">
          <h3>Backup Status</h3>
          <table>
            <tbody>
              <tr><td>Database Path</td><td>{backup.database_path}</td></tr>
              <tr><td>Snapshot Path</td><td>{backup.snapshot_path}</td></tr>
              <tr><td>Last Backup</td><td>{backup.last_backup_time || 'Never'}</td></tr>
              <tr><td>Restore Test</td><td>{backup.last_restore_test_status}</td></tr>
              <tr><td>Disk Free</td><td>{backup.disk_free_gb} GB / {backup.disk_total_gb} GB</td></tr>
              <tr><td>Disk Warning</td><td>{backup.disk_warning ? 'Yes' : 'No'}</td></tr>
            </tbody>
          </table>
          <div className="button-row">
            <button className="btn btn--small" onClick={async () => { const r = await api.runLocalBackup(); alert(r.message) }}>Run Backup</button>
            <button className="btn btn--small" onClick={async () => { const r = await api.testRestore(); alert(r.message) }}>Test Restore</button>
          </div>
        </div>
      )}
    </div>
  )
}
