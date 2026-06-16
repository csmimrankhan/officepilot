import { useState, useEffect } from 'react'
import { api } from '../api.js'

const SEVERITY_COLORS = {
  low: '#9e9e9e',
  medium: '#2196f3',
  high: '#ff9800',
  critical: '#f44336',
}

export default function BugReports() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('')

  function load() {
    setLoading(true)
    const params = {}
    if (filterStatus) params.status = filterStatus
    api.listBugReports(params).then(r => setItems(r.items || r)).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filterStatus])

  return (
    <div className="card">
      <h2>Bug Reports</h2>

      <div style={{ marginBottom: '16px' }}>
        <label>Status <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="">All</option>
          <option value="open">Open</option>
          <option value="in_progress">In Progress</option>
          <option value="fixed">Fixed</option>
          <option value="wont_fix">Won't Fix</option>
          <option value="needs_info">Needs Info</option>
        </select></label>
      </div>

      {loading ? <p className="status">Loading...</p> : items.length === 0 ? <p>No bug reports found.</p> : (
        <table className="table">
          <thead><tr><th>Title</th><th>Severity</th><th>Status</th><th>Date</th><th>Includes</th><th>Download</th></tr></thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id}>
                <td><strong>{item.title}</strong><br /><small style={{ color: '#666' }}>{item.description?.substring(0, 100)}{item.description?.length > 100 ? '...' : ''}</small></td>
                <td><span className="badge" style={{ background: SEVERITY_COLORS[item.severity] || '#9e9e9e', color: '#fff' }}>{item.severity}</span></td>
                <td><span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.85rem', background: item.status === 'open' ? '#ffebee' : item.status === 'fixed' ? '#e8f5e9' : '#f5f5f5' }}>{item.status}</span></td>
                <td style={{ fontSize: '0.85rem' }}>{item.created_at ? new Date(item.created_at).toLocaleDateString() : ''}</td>
                <td style={{ fontSize: '0.8rem' }}>
                  {item.include_logs ? 'logs ' : ''}{item.include_screenshot ? 'screenshot ' : ''}{item.include_readiness ? 'readiness' : ''}
                  {!item.include_logs && !item.include_screenshot && !item.include_readiness ? 'none' : ''}
                </td>
                <td><a href={api.downloadBugReportUrl(item.id)} className="btn btn--small" target="_blank" rel="noopener noreferrer">Download</a></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
