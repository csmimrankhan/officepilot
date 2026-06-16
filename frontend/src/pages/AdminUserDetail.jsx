import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { api } from '../api.js'
import PageHeader from '../components/layout/PageHeader.jsx'

export default function AdminUserDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState({ full_name: '', role: '', status: '', is_active: true })

  useEffect(() => {
    setLoading(true)
    api.adminGetUser(id).then(u => {
      setUser(u)
      setEditForm({ full_name: u.full_name, role: u.role, status: u.status, is_active: u.is_active })
    }).catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [id])

  async function saveEdit() {
    try {
      const updated = await api.adminUpdateUser(id, editForm)
      setUser(updated)
      setEditing(false)
      setMessage('User updated')
    } catch (err) { setError(err.message) }
  }

  async function handleSuspend() {
    if (!window.confirm(`Suspend user ${user.email}? This will prevent them from signing in.`)) return
    try {
      await api.adminSuspendUser(id)
      setMessage('User suspended')
      setUser(u => ({ ...u, status: 'suspended' }))
    } catch (err) { setError(err.message) }
  }

  async function handleActivate() {
    try {
      await api.adminActivateUser(id)
      setMessage('User activated')
      setUser(u => ({ ...u, status: 'active', is_active: true }))
    } catch (err) { setError(err.message) }
  }

  async function handleForceLogout() {
    if (!window.confirm(`Force logout user ${user.email}? All current sessions will be revoked.`)) return
    try {
      await api.adminForceLogout(id)
      setMessage('Sessions revoked')
    } catch (err) { setError(err.message) }
  }

  async function handleResetPasswordLink() {
    try {
      const res = await api.adminResetPasswordLink(id)
      setMessage(`Reset token: ${res.reset_token}`)
      navigator.clipboard.writeText(res.reset_token)
    } catch (err) { setError(err.message) }
  }

  if (loading) return <div><PageHeader title="User Detail" subtitle="Loading..." /><div className="loading-state"><div className="spinner" /><p>Loading user...</p></div></div>
  if (error) return <div><PageHeader title="Error" /><div className="error-state"><h3>Error</h3><p>{error}</p></div></div>
  if (!user) return <div><PageHeader title="User not found" /><div className="error-state"><h3>User not found</h3></div></div>

  return (
    <div>
      <PageHeader title={user.full_name || user.email}
        subtitle={`User ID: ${user.id}`}
        actions={<Link to="/admin/users" className="btn btn--sm">Back to users</Link>}
      />
      {message && <div className="alert success" style={{ marginBottom: 12 }}>{message}</div>}
      {error && <div className="alert error">{error}</div>}

      <div className="admin-detail-sections">
        <div className="card admin-detail-section">
          <h3>Profile</h3>
          <div className="admin-detail-grid">
            <div className="admin-detail-item"><span className="admin-detail-label">Full Name</span><span>{user.full_name || '—'}</span></div>
            <div className="admin-detail-item"><span className="admin-detail-label">Email</span><span>{user.email}</span></div>
            {editing && (
              <div className="admin-detail-item" style={{ gridColumn: '1 / -1' }}>
                <input value={editForm.full_name} onChange={e => setEditForm(f => ({ ...f, full_name: e.target.value }))} placeholder="Full name" />
              </div>
            )}
          </div>
        </div>

        <div className="card admin-detail-section">
          <h3>Security</h3>
          <div className="admin-detail-grid">
            <div className="admin-detail-item"><span className="admin-detail-label">Role</span>
              {editing ? (
                <select value={editForm.role} onChange={e => setEditForm(f => ({ ...f, role: e.target.value }))}>
                  <option value="owner">Owner</option>
                  <option value="admin">Admin</option>
                  <option value="user">User</option>
                  <option value="viewer">Viewer</option>
                </select>
              ) : <span className={`badge badge--${user.role === 'owner' || user.role === 'admin' ? 'info' : 'success'}`}>{user.role}</span>}
            </div>
            <div className="admin-detail-item"><span className="admin-detail-label">Status</span>
              {editing ? (
                <select value={editForm.status} onChange={e => setEditForm(f => ({ ...f, status: e.target.value }))}>
                  <option value="active">Active</option>
                  <option value="suspended">Suspended</option>
                  <option value="pending_verification">Pending Verification</option>
                </select>
              ) : <span className={`badge badge--${user.status === 'active' ? 'success' : 'danger'}`}>{user.status}</span>}
            </div>
            <div className="admin-detail-item"><span className="admin-detail-label">Email Verified</span><span>{user.email_verified ? '✓' : '—'}</span></div>
            <div className="admin-detail-item"><span className="admin-detail-label">Active</span><span>{user.is_active ? 'Yes' : 'No'}</span></div>
            <div className="admin-detail-item"><span className="admin-detail-label">Login Count</span><span>{user.login_count}</span></div>
            <div className="admin-detail-item"><span className="admin-detail-label">Failed Logins</span><span>{user.failed_login_count}</span></div>
          </div>
        </div>

        <div className="card admin-detail-section">
          <h3>Sessions</h3>
          <div className="admin-detail-grid">
            <div className="admin-detail-item"><span className="admin-detail-label">Last Login</span><span>{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : '—'}</span></div>
            <div className="admin-detail-item"><span className="admin-detail-label">Last Active</span><span>{user.last_active_at ? new Date(user.last_active_at).toLocaleString() : '—'}</span></div>
          </div>
        </div>

        <div className="card admin-detail-section">
          <h3>Connected Accounts</h3>
          <div className="admin-detail-grid">
            <div className="admin-detail-item"><span className="admin-detail-label">Auth Provider</span><span>{user.auth_provider || 'email'}</span></div>
            <div className="admin-detail-item"><span className="admin-detail-label">Gmail Connected</span><span>{user.gmail_connected ? '✓' : '—'}</span></div>
            <div className="admin-detail-item"><span className="admin-detail-label">Cloud AI Allowed</span><span>{user.cloud_ai_allowed ? '✓' : '—'}</span></div>
          </div>
        </div>

        <div className="card admin-detail-section">
          <h3>Permissions</h3>
          <div className="admin-detail-grid">
            <div className="admin-detail-item"><span className="admin-detail-label">Created</span><span>{user.created_at ? new Date(user.created_at).toLocaleString() : '—'}</span></div>
            <div className="admin-detail-item"><span className="admin-detail-label">Updated</span><span>{user.updated_at ? new Date(user.updated_at).toLocaleString() : '—'}</span></div>
          </div>
        </div>
      </div>

      {!editing && (
        <div className="admin-detail-actions">
          <button className="btn btn--sm" onClick={() => setEditing(true)}>✏️ Edit User</button>
          {user.status !== 'suspended' && <button className="btn btn--sm btn--danger" onClick={handleSuspend}>🚫 Suspend</button>}
          {user.status === 'suspended' && <button className="btn btn--sm" style={{ background: 'var(--success)', color: '#fff' }} onClick={handleActivate}>✅ Activate</button>}
          <button className="btn btn--sm" onClick={handleForceLogout}>🔑 Force Logout</button>
          <button className="btn btn--sm" onClick={handleResetPasswordLink}>🔗 Reset Password Link</button>
        </div>
      )}
      {editing && (
        <div className="admin-detail-actions">
          <button className="btn btn--primary btn--sm" onClick={saveEdit}>Save Changes</button>
          <button className="btn btn--sm" onClick={() => setEditing(false)}>Cancel</button>
        </div>
      )}
    </div>
  )
}
