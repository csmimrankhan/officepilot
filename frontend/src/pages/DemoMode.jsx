import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function DemoMode() {
  const [status, setStatus] = useState(null)
  const [files, setFiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [seeding, setSeeding] = useState(false)
  const [resetting, setResetting] = useState(false)

  function load() {
    setLoading(true)
    Promise.all([api.demoStatus(), api.sampleFiles()])
      .then(([s, f]) => { setStatus(s); setFiles(f.files || []) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  function seed() {
    setSeeding(true)
    api.seedDemoData().then(r => {
      alert(`Demo data seeded: ${JSON.stringify(r.counts)}`)
      load()
    }).catch(e => alert('Error: ' + e.message)).finally(() => setSeeding(false))
  }

  function reset() {
    if (!confirm('This will remove all demo data. Continue?')) return
    setResetting(true)
    api.resetDemoData().then(r => {
      alert(`Demo data reset: ${JSON.stringify(r.counts)}`)
      load()
    }).catch(e => alert('Error: ' + e.message)).finally(() => setResetting(false))
  }

  if (loading) return <div className="card">Loading demo status...</div>

  return (
    <div className="card">
      <h2>Demo Mode</h2>
      <div className="badge" style={{ background: '#4caf50', color: '#fff', padding: '4px 12px', borderRadius: '4px', display: 'inline-block' }}>
        {status?.demo_mode_enabled ? 'Demo Mode Active' : 'Demo Mode Disabled'}
      </div>
      <p>Demo mode uses only fake/sample data. No real Gmail, QuickBooks, or Xero connections are made.</p>

      <div style={{ margin: '16px 0' }}>
        <p><strong>Demo data status:</strong> {status?.demo_data_seeded ? 'Seeded' : 'Not seeded'}</p>
        {status?.demo_invoice_count > 0 && <p>Demo invoices: {status.demo_invoice_count}</p>}
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <button className="btn" onClick={seed} disabled={seeding}>{seeding ? 'Seeding...' : 'Load Sample Data'}</button>
        <button className="btn btn--secondary" onClick={reset} disabled={resetting || !status?.demo_data_seeded}>{resetting ? 'Resetting...' : 'Reset Demo Data'}</button>
      </div>

      <h3>Sample Files</h3>
      {files.length === 0 ? <p>No sample files found.</p> : (
        <table className="table">
          <thead><tr><th>Name</th><th>Path</th><th>Size</th></tr></thead>
          <tbody>
            {files.map((f, i) => (
              <tr key={i}><td>{f.name}</td><td><code>{f.path}</code></td><td>{f.size} bytes</td></tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
