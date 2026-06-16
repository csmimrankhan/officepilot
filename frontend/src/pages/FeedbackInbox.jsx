import { useState, useEffect } from 'react'
import { api } from '../api.js'

const STATUS_STYLES = {
  new: { background: '#e3f2fd', color: '#1565c0' },
  acknowledged: { background: '#fff3e0', color: '#e65100' },
  addressed: { background: '#e8f5e9', color: '#2e7d32' },
  closed: { background: '#f5f5f5', color: '#616161' },
}

const TYPE_LABELS = {
  bug: 'Bug',
  confusing_ux: 'Confusing UX',
  extraction_mistake: 'Extraction Mistake',
  missing_feature: 'Missing Feature',
  performance_issue: 'Performance Issue',
  security_concern: 'Security Concern',
  general_feedback: 'General Feedback',
}

export default function FeedbackInbox() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('')
  const [filterType, setFilterType] = useState('')

  function load() {
    setLoading(true)
    const params = {}
    if (filterStatus) params.status = filterStatus
    if (filterType) params.feedback_type = filterType
    api.listFeedback(params).then(r => setItems(r.items || r)).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filterStatus, filterType])

  async function updateStatus(id, status) {
    try {
      await api.updateFeedback(id, { status })
      load()
    } catch (e) {
      alert('Error: ' + e.message)
    }
  }

  return (
    <div className="card">
      <h2>Feedback Inbox</h2>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <div>
          <label>Status <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
            <option value="">All</option>
            <option value="new">New</option>
            <option value="acknowledged">Acknowledged</option>
            <option value="addressed">Addressed</option>
            <option value="closed">Closed</option>
          </select></label>
        </div>
        <div>
          <label>Type <select value={filterType} onChange={e => setFilterType(e.target.value)}>
            <option value="">All</option>
            {Object.entries(TYPE_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select></label>
        </div>
      </div>

      {loading ? <p className="status">Loading...</p> : items.length === 0 ? <p>No feedback found.</p> : (
        <table className="table">
          <thead><tr><th>Type</th><th>Title</th><th>Severity</th><th>Status</th><th>Date</th><th>Actions</th></tr></thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id}>
                <td><span style={{ fontSize: '0.85rem' }}>{TYPE_LABELS[item.feedback_type] || item.feedback_type}</span></td>
                <td><strong>{item.title}</strong><br /><small style={{ color: '#666' }}>{item.message?.substring(0, 80)}{item.message?.length > 80 ? '...' : ''}</small></td>
                <td><span className="badge" style={{ background: item.severity === 'critical' ? '#f44336' : item.severity === 'high' ? '#ff9800' : item.severity === 'medium' ? '#2196f3' : '#9e9e9e', color: '#fff' }}>{item.severity}</span></td>
                <td><span style={{ ...STATUS_STYLES[item.status] || {}, padding: '2px 8px', borderRadius: '4px', fontSize: '0.85rem' }}>{item.status}</span></td>
                <td style={{ fontSize: '0.85rem' }}>{item.created_at ? new Date(item.created_at).toLocaleDateString() : ''}</td>
                <td>
                  {item.status === 'new' && <button className="btn btn--small" onClick={() => updateStatus(item.id, 'acknowledged')}>Acknowledge</button>}
                  {item.status === 'acknowledged' && <button className="btn btn--small" onClick={() => updateStatus(item.id, 'addressed')}>Mark Addressed</button>}
                  {item.status !== 'closed' && <button className="btn btn--small btn--secondary" style={{ marginLeft: '4px' }} onClick={() => updateStatus(item.id, 'closed')}>Close</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
