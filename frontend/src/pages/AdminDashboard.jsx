import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import PageHeader from '../components/layout/PageHeader.jsx'
import AdminMetricCard from '../components/admin/AdminMetricCard.jsx'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const [users, setUsers] = useState([])
  const [health, setHealth] = useState(null)
  const [aiStatus, setAiStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.adminListUsers(1, 1000).catch(() => ({ items: [], total: 0 })),
      api.getAdminSystemHealth().catch(() => null),
      api.getAdminAIStatus().catch(() => null),
    ]).then(([userData, healthData, aiData]) => {
      setUsers(userData?.items || [])
      setHealth(healthData)
      setAiStatus(aiData)
    }).catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const totalUsers = users.length
  const activeUsers = users.filter(u => u.status === 'active').length
  const suspendedUsers = users.filter(u => u.status === 'suspended').length
  const adminUsers = users.filter(u => u.role === 'admin' || u.role === 'owner').length
  const recentLogins = users.filter(u => u.last_login_at && new Date(u.last_login_at) > new Date(Date.now() - 7 * 86400000)).length

  if (loading) {
    return (
      <div>
        <PageHeader title="Admin Dashboard" subtitle="System overview" />
        <div className="loading-state"><div className="spinner" /><p>Loading dashboard...</p></div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Admin Dashboard" subtitle="System overview" />
        <div className="alert error">{error}</div>
      </div>
    )
  }

  return (
    <div>
      <PageHeader title="Admin Dashboard" subtitle="System overview and key metrics" />

      <div className="admin-dashboard-grid">
        <AdminMetricCard label="Total Users" value={totalUsers} icon="👥" color="#2563eb" subtitle="All registered users" onClick={() => navigate('/admin/users')} />
        <AdminMetricCard label="Active Users" value={activeUsers} icon="✅" color="#16a34a" subtitle={`${totalUsers > 0 ? Math.round(activeUsers / totalUsers * 100) : 0}% of total`} />
        <AdminMetricCard label="Suspended Users" value={suspendedUsers} icon="🚫" color="#dc2626" subtitle={suspendedUsers > 0 ? 'Requires attention' : 'No suspended users'} />
        <AdminMetricCard label="Admin Users" value={adminUsers} icon="🛡️" color="#8b5cf6" subtitle="Users with admin privileges" />
      </div>

      <div className="admin-dashboard-grid">
        <AdminMetricCard label="System Health" value={health ? 'Operational' : 'Unknown'} icon="🩺" color={health ? '#16a34a' : '#d97706'} subtitle={health ? `v${health.version || '—'}` : 'Unable to check'} onClick={() => navigate('/admin/system-health')} />
        <AdminMetricCard label="AI / Cloud Status" value={aiStatus?.agent_provider === 'mock' ? 'Local Only' : aiStatus?.agent_provider || 'Unknown'} icon="🧠" color={aiStatus?.agent_provider === 'mock' ? '#16a34a' : '#d97706'} subtitle={aiStatus?.zero_cloud_by_default ? 'Zero cloud by default' : 'Cloud AI disabled'} onClick={() => navigate('/admin/ai-status')} />
        <AdminMetricCard label="Latest Version" value={health?.version || '1.0.0'} icon="📦" color="#2563eb" subtitle={`Phase ${health?.phase || '37'}`} />
        <AdminMetricCard label="Recent Logins (7d)" value={recentLogins} icon="🔑" color="#d97706" subtitle={`${totalUsers > 0 ? Math.round(recentLogins / totalUsers * 100) : 0}% active this week`} />
      </div>

      <div className="admin-dashboard-links">
        <Link to="/admin/users" className="btn btn--sm">Manage Users</Link>
        <Link to="/admin/audit-logs" className="btn btn--sm">Audit Logs</Link>
        <Link to="/admin/waitlist" className="btn btn--sm">Pilot Waitlist</Link>
        <Link to="/admin/system-health" className="btn btn--sm">System Health</Link>
        <Link to="/admin/ai-status" className="btn btn--sm">AI Status</Link>
      </div>
    </div>
  )
}
