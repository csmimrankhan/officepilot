import { Link } from 'react-router-dom'

export default function AdminUserCard({ user }) {
  const roleColor = user.role === 'owner' || user.role === 'admin' ? '#2563eb' : '#16a34a'
  const statusColor = user.status === 'active' ? '#16a34a' : user.status === 'suspended' ? '#dc2626' : '#d97706'

  return (
    <div className="admin-user-card">
      <div className="admin-user-card-header">
        <div className="admin-user-card-avatar">
          {(user.full_name?.[0] || user.email?.[0] || '?').toUpperCase()}
        </div>
        <div>
          <div className="admin-user-card-name">{user.full_name || '—'}</div>
          <div className="admin-user-card-email">{user.email}</div>
        </div>
      </div>
      <div className="admin-user-card-body">
        <div className="admin-user-card-row">
          <span className="admin-user-card-label">Role</span>
          <span className="badge" style={{ background: '#dbeafe', color: roleColor }}>{user.role}</span>
        </div>
        <div className="admin-user-card-row">
          <span className="admin-user-card-label">Status</span>
          <span className="badge" style={{ background: statusColor === '#16a34a' ? '#dcfce7' : statusColor === '#dc2626' ? '#fee2e2' : '#fef3c7', color: statusColor }}>{user.status}</span>
        </div>
        <div className="admin-user-card-row">
          <span className="admin-user-card-label">Provider</span>
          <span>{user.auth_provider || 'email'}</span>
        </div>
        <div className="admin-user-card-row">
          <span className="admin-user-card-label">Last Login</span>
          <span>{user.last_login_at ? new Date(user.last_login_at).toLocaleDateString() : '—'}</span>
        </div>
      </div>
      <div className="admin-user-card-footer">
        <Link to={`/admin/users/${user.id}`} className="btn btn--sm" style={{ width: '100%', textAlign: 'center' }}>View</Link>
      </div>
    </div>
  )
}
