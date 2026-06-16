import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function About() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.about().then(d => setData(d)).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="card">Loading...</div>
  if (!data) return <div className="card">Failed to load app info.</div>

  return (
    <div className="card">
      <h2>About OfficePilot AI</h2>
      <table className="table">
        <tbody>
          <tr><td><strong>App Name</strong></td><td>{data.app_name}</td></tr>
          <tr><td><strong>Version</strong></td><td>{data.version}</td></tr>
          <tr><td><strong>Phase</strong></td><td>{data.phase}</td></tr>
          <tr><td><strong>Backend</strong></td><td>{data.backend_healthy ? 'Healthy' : 'Unhealthy'}</td></tr>
          <tr><td><strong>Sidecar</strong></td><td>{data.sidecar_status === 'found' ? 'Found' : 'Not found'}</td></tr>
          <tr><td><strong>Database Path</strong></td><td><code>{data.database_path}</code></td></tr>
          <tr><td><strong>Storage Path</strong></td><td><code>{data.storage_path}</code></td></tr>
          <tr><td><strong>Data Directory</strong></td><td><code>{data.data_dir}</code></td></tr>
          <tr><td><strong>Logs Path</strong></td><td><code>{data.logs_path}</code></td></tr>
          <tr><td><strong>Build Date</strong></td><td>{data.build_date}</td></tr>
          <tr><td><strong>Demo Mode</strong></td><td>{data.demo_mode ? 'Enabled' : 'Disabled'}</td></tr>
        </tbody>
      </table>
    </div>
  )
}
