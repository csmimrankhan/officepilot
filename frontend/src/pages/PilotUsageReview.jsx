import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function PilotUsageReview() {
  const [summary, setSummary] = useState(null)
  const [recentEvents, setRecentEvents] = useState([])
  const [loading, setLoading] = useState(true)

  function load() {
    setLoading(true)
    Promise.all([
      api.usageSummary(),
      api.listUsageEvents({ limit: 50 }),
    ]).then(([s, r]) => {
      setSummary(s)
      setRecentEvents(r.items || r)
    }).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <div className="card">Loading usage data...</div>
  if (!summary) return <div className="card">Failed to load usage data.</div>

  const events = recentEvents || []
  const topFeatures = summary.top_features || []

  return (
    <div className="card">
      <h2>Pilot Usage Review</h2>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <div className="card" style={{ flex: '1', minWidth: '140px', textAlign: 'center' }}>
          <h3 style={{ margin: '8px 0', fontSize: '2rem', color: '#1976d2' }}>{summary.total_events ?? summary.total ?? 0}</h3>
          <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>Total Events</p>
        </div>
        <div className="card" style={{ flex: '1', minWidth: '140px', textAlign: 'center' }}>
          <h3 style={{ margin: '8px 0', fontSize: '2rem', color: '#f44336' }}>{summary.error_count ?? summary.errors ?? 0}</h3>
          <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>Error Count</p>
        </div>
        <div className="card" style={{ flex: '1', minWidth: '140px', textAlign: 'center' }}>
          <h3 style={{ margin: '8px 0', fontSize: '2rem', color: '#4caf50' }}>{summary.unique_users ?? summary.users ?? 0}</h3>
          <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>Unique Users</p>
        </div>
        <div className="card" style={{ flex: '1', minWidth: '140px', textAlign: 'center' }}>
          <h3 style={{ margin: '8px 0', fontSize: '2rem', color: '#ff9800' }}>{summary.avg_daily_events ?? summary.daily_avg ?? 0}</h3>
          <p style={{ margin: 0, fontSize: '0.85rem', color: '#666' }}>Avg Daily Events</p>
        </div>
      </div>

      <div style={{ marginBottom: '20px' }}>
        <h3>Top Features</h3>
        {topFeatures.length === 0 ? <p>No feature data yet.</p> : (
          <table className="table">
            <thead><tr><th>#</th><th>Feature</th><th>Uses</th></tr></thead>
            <tbody>
              {topFeatures.map((f, i) => (
                <tr key={i}>
                  <td>{i + 1}</td>
                  <td><strong>{f.feature || f.name || f.event_type}</strong></td>
                  <td>{f.count || f.uses || 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div>
        <h3>Recent Events</h3>
        {events.length === 0 ? <p>No recent events.</p> : (
          <table className="table" style={{ fontSize: '0.85rem' }}>
            <thead><tr><th>Time</th><th>User</th><th>Event</th><th>Detail</th></tr></thead>
            <tbody>
              {events.slice(0, 50).map((ev, i) => (
                <tr key={ev.id || i}>
                  <td>{ev.timestamp ? new Date(ev.timestamp).toLocaleString() : ev.created_at ? new Date(ev.created_at).toLocaleString() : ''}</td>
                  <td>{ev.user_id || ev.actor || '-'}</td>
                  <td><code>{ev.event_type || ev.action || ev.name}</code></td>
                  <td><small style={{ color: '#666' }}>{ev.detail || ev.description || ev.message || ''}</small></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={{ marginTop: '16px' }}>
        <button className="btn btn--secondary" onClick={load}>Refresh</button>
      </div>
    </div>
  )
}
