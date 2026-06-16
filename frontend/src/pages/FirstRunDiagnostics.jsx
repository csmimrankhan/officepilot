import { useState, useEffect } from 'react'
import { api } from '../api.js'

const STATUS_COLORS = { green: '#4caf50', yellow: '#ff9800', red: '#f44336' }
const ITEM_COLORS = { ok: '#4caf50', warning: '#ff9800', error: '#f44336', disabled: '#9e9e9e' }

export default function FirstRunDiagnostics() {
  const [diag, setDiag] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.diagnostics().then(d => setDiag(d)).catch(() => {}).finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="card">Running diagnostics...</div>
  if (!diag) return <div className="card">Failed to run diagnostics.</div>

  return (
    <div className="card">
      <h2>First-Run Diagnostics</h2>
      <p style={{ color: STATUS_COLORS[diag.overall] || '#000' }}>
        Overall status: <strong>{diag.overall.toUpperCase()}</strong>
      </p>
      <p><small>Ran at: {diag.timestamp}</small></p>

      <table className="table">
        <thead><tr><th>Component</th><th>Status</th><th>Detail</th><th>Fix</th></tr></thead>
        <tbody>
          {diag.items.map((item, i) => (
            <tr key={i}>
              <td><strong>{item.name}</strong></td>
              <td><span style={{ color: ITEM_COLORS[item.status] || '#000' }}>{item.status}</span></td>
              <td><small>{item.detail}</small></td>
              <td>{item.fix ? <small style={{ color: '#f44336' }}>{item.fix}</small> : <small style={{ color: '#4caf50' }}>OK</small>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
