import { useState, useEffect } from 'react'
import * as api from '../api.js'
import { adminWaitlistExportCsvUrl, formatDateTime } from '../api.js'

const STATUS_STYLES = {
  new: { background: '#e3f2fd', color: '#1565c0' },
  contacted: { background: '#fff3e0', color: '#e65100' },
  demo_scheduled: { background: '#f3e5f5', color: '#7b1fa2' },
  accepted: { background: '#e8f5e9', color: '#2e7d32' },
  rejected: { background: '#ffebee', color: '#c62828' },
}

export default function AdminWaitlist() {
  const [entries, setEntries] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('')
  const [search, setSearch] = useState('')

  function loadSummary() {
    api.adminWaitlistSummary().then(s => setSummary(s)).catch(() => {})
  }

  function loadEntries() {
    setLoading(true)
    const params = {}
    if (filterStatus) params.status = filterStatus
    if (search) params.search = search
    api.listAdminWaitlist(params).then(r => {
      setEntries(r.items || r || [])
    }).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { loadSummary(); loadEntries() }, [])

  useEffect(() => { loadEntries() }, [filterStatus, search])

  async function handleStatusChange(id, newStatus) {
    try {
      await api.updateAdminWaitlistStatus(id, { status: newStatus })
      loadEntries()
      loadSummary()
    } catch (e) {
      alert('Error: ' + e.message)
    }
  }

  function handleExportCsv() {
    window.open(adminWaitlistExportCsvUrl(), '_blank')
  }

  const byRoleEntries = summary?.by_role
    ? Object.entries(summary.by_role).slice(0, 3)
    : []

  const byVolumeEntries = summary?.by_volume
    ? Object.entries(summary.by_volume).slice(0, 3)
    : []

  const statusCounts = summary?.by_status
    ? Object.entries(summary.by_status)
    : []

  return (
    <div className="card admin-waitlist">
      <style>{`
.admin-waitlist { padding: 0; }
.admin-waitlist h2 { margin-top: 0; margin-bottom: 20px; font-size: 1.5rem; color: #1a237e; }
.summary-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.summary-card { background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border: 1px solid #e0e0e0; }
.summary-card h3 { margin: 0 0 8px 0; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; color: #757575; }
.summary-card .total-value { font-size: 2rem; font-weight: 700; color: #1a237e; margin-bottom: 8px; }
.summary-card ul { list-style: none; padding: 0; margin: 0; }
.summary-card li { display: flex; justify-content: space-between; padding: 3px 0; font-size: 0.85rem; color: #424242; border-bottom: 1px solid #f5f5f5; }
.summary-card li:last-child { border-bottom: none; }
.summary-card li span:last-child { font-weight: 600; color: #37474f; }
.status-counts { display: flex; flex-direction: column; gap: 4px; }
.status-count-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem; }
.status-count-row .status-badge-sm { display: inline-block; padding: 1px 8px; border-radius: 10px; font-size: 0.75rem; font-weight: 500; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
.toolbar-filters { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.toolbar-filters label { display: flex; align-items: center; gap: 6px; font-size: 0.85rem; color: #616161; }
.toolbar-filters select, .toolbar-filters input { padding: 6px 10px; border: 1px solid #bdbdbd; border-radius: 4px; font-size: 0.85rem; background: #fff; min-width: 140px; }
.toolbar-filters select:focus, .toolbar-filters input:focus { outline: none; border-color: #1976d2; box-shadow: 0 0 0 2px rgba(25,118,210,0.15); }
.btn-export { display: inline-flex; align-items: center; gap: 6px; padding: 8px 18px; background: #1976d2; color: #fff; border: none; border-radius: 4px; font-size: 0.85rem; font-weight: 500; cursor: pointer; transition: background 0.2s; }
.btn-export:hover { background: #1565c0; }
.waitlist-table-wrap { background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.08); border: 1px solid #e0e0e0; overflow: hidden; }
.waitlist-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.waitlist-table thead { background: #f5f7fa; }
.waitlist-table th { text-align: left; padding: 10px 14px; font-weight: 600; color: #455a64; border-bottom: 2px solid #e0e0e0; white-space: nowrap; }
.waitlist-table td { padding: 10px 14px; color: #424242; border-bottom: 1px solid #f0f0f0; }
.waitlist-table tbody tr:nth-child(even) { background: #fafbfc; }
.waitlist-table tbody tr:hover { background: #e3f2fd; }
.status-badge { display: inline-block; padding: 3px 12px; border-radius: 12px; font-size: 0.78rem; font-weight: 500; white-space: nowrap; }
.inline-status-select { padding: 4px 8px; border: 1px solid #bdbdbd; border-radius: 4px; font-size: 0.8rem; background: #fff; cursor: pointer; }
.inline-status-select:focus { outline: none; border-color: #1976d2; }
.loading-state { text-align: center; padding: 40px 20px; color: #757575; font-size: 0.95rem; }
.empty-state { text-align: center; padding: 60px 20px; color: #9e9e9e; }
.empty-state p { margin: 4px 0; }
`}</style>
      <h2>Waitlist Management</h2>

      <div className="summary-cards">
        <div className="summary-card">
          <h3>Total Signups</h3>
          <div className="total-value">{summary?.total ?? '-'}</div>
        </div>

        <div className="summary-card">
          <h3>By Role</h3>
          {byRoleEntries.length === 0 ? (
            <div style={{ color: '#9e9e9e', fontSize: '0.85rem' }}>No data</div>
          ) : (
            <ul>
              {byRoleEntries.map(([role, count]) => (
                <li key={role}><span>{role}</span><span>{count}</span></li>
              ))}
            </ul>
          )}
        </div>

        <div className="summary-card">
          <h3>By Volume</h3>
          {byVolumeEntries.length === 0 ? (
            <div style={{ color: '#9e9e9e', fontSize: '0.85rem' }}>No data</div>
          ) : (
            <ul>
              {byVolumeEntries.map(([vol, count]) => (
                <li key={vol}><span>{vol}</span><span>{count}</span></li>
              ))}
            </ul>
          )}
        </div>

        <div className="summary-card">
          <h3>By Status</h3>
          {statusCounts.length === 0 ? (
            <div style={{ color: '#9e9e9e', fontSize: '0.85rem' }}>No data</div>
          ) : (
            <div className="status-counts">
              {statusCounts.map(([status, count]) => (
                <div key={status} className="status-count-row">
                  <span className="status-badge-sm" style={STATUS_STYLES[status] || { background: '#f5f5f5', color: '#616161' }}>
                    {status}
                  </span>
                  <span>{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="toolbar">
        <div className="toolbar-filters">
          <label>
            Status
            <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
              <option value="">All</option>
              <option value="new">New</option>
              <option value="contacted">Contacted</option>
              <option value="demo_scheduled">Demo Scheduled</option>
              <option value="accepted">Accepted</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>
          <label>
            Search
            <input
              type="text"
              placeholder="Name, email, company..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </label>
        </div>
        <button className="btn-export" onClick={handleExportCsv}>
          Export CSV
        </button>
      </div>

      {loading ? (
        <div className="loading-state">Loading waitlist entries...</div>
      ) : entries.length === 0 ? (
        <div className="empty-state">
          <p>No waitlist entries found.</p>
          <p style={{ fontSize: '0.85rem', color: '#bdbdbd' }}>Try adjusting your filters or check back later.</p>
        </div>
      ) : (
        <div className="waitlist-table-wrap">
          <table className="waitlist-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Company</th>
                <th>Role</th>
                <th>Invoice Volume</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {entries.map(item => (
                <tr key={item.id}>
                  <td><strong>{item.name || '-'}</strong></td>
                  <td>{item.email || '-'}</td>
                  <td>{item.company || '-'}</td>
                  <td>{item.role || '-'}</td>
                  <td>{item.invoice_volume || item.volume || '-'}</td>
                  <td>
                    <span className="status-badge" style={STATUS_STYLES[item.status] || { background: '#f5f5f5', color: '#616161' }}>
                      {item.status}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.8rem', color: '#757575' }}>{formatDateTime(item.created_at)}</td>
                  <td>
                    <select
                      className="inline-status-select"
                      value={item.status}
                      onChange={e => handleStatusChange(item.id, e.target.value)}
                    >
                      <option value="new">New</option>
                      <option value="contacted">Contacted</option>
                      <option value="demo_scheduled">Demo Scheduled</option>
                      <option value="accepted">Accepted</option>
                      <option value="rejected">Rejected</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
