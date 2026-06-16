import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import PageHeader from '../components/layout/PageHeader.jsx'
import AdminUserCard from '../components/admin/AdminUserCard.jsx'

function useIsMobile() {
  const [mobile, setMobile] = useState(window.innerWidth <= 768)
  useEffect(() => {
    const handler = () => setMobile(window.innerWidth <= 768)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])
  return mobile
}

export default function AdminUsers() {
  const isMobile = useIsMobile()
  const [users, setUsers] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [providerFilter, setProviderFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ email: '', password: '', full_name: '', role: 'user', email_verified: false })
  const [createError, setCreateError] = useState('')
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const res = await api.adminListUsers(page, 20, search, roleFilter, statusFilter, providerFilter)
      setUsers(res.items)
      setTotal(res.total)
    } catch (err) {
      setError(err.message)
    } finally { setLoading(false) }
  }, [page, search, roleFilter, statusFilter, providerFilter])

  useEffect(() => { load() }, [load])

  const totalPages = Math.ceil(total / 20)

  async function handleCreate(e) {
    e.preventDefault()
    setCreating(true)
    setCreateError('')
    try {
      await api.adminCreateUser(createForm)
      setShowCreate(false)
      setCreateForm({ email: '', password: '', full_name: '', role: 'user', email_verified: false })
      load()
    } catch (err) {
      setCreateError(err.message || 'Failed to create user')
    } finally { setCreating(false) }
  }

  return (
    <div>
      <PageHeader title="User Management"
        subtitle={`Admin · ${total} users`}
        actions={<button className="btn btn--primary btn--sm" onClick={() => setShowCreate(true)}>+ Create User</button>}
      />
      {error && <div className="alert error">{error}</div>}

      {showCreate && (
        <div className="card" style={{ padding: 16, marginBottom: 16 }}>
          <h3 style={{ margin: '0 0 12px' }}>Create User</h3>
          {createError && <div className="alert error">{createError}</div>}
          <form onSubmit={handleCreate} className="admin-create-form">
            <input placeholder="Full name" value={createForm.full_name} onChange={e => setCreateForm(f => ({ ...f, full_name: e.target.value }))} required />
            <input type="email" placeholder="Email" value={createForm.email} onChange={e => setCreateForm(f => ({ ...f, email: e.target.value }))} required />
            <input type="password" placeholder="Password (8+ chars, upper+lower+number+special)" value={createForm.password} onChange={e => setCreateForm(f => ({ ...f, password: e.target.value }))} required minLength={8} />
            <select value={createForm.role} onChange={e => setCreateForm(f => ({ ...f, role: e.target.value }))}>
              <option value="user">User</option>
              <option value="admin">Admin</option>
              <option value="viewer">Viewer</option>
            </select>
            <label className="admin-checkbox-label">
              <input type="checkbox" checked={createForm.email_verified} onChange={e => setCreateForm(f => ({ ...f, email_verified: e.target.checked }))} />
              Mark email as verified
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn--primary" type="submit" disabled={creating}>{creating ? 'Creating...' : 'Create'}</button>
              <button className="btn btn--secondary" type="button" onClick={() => { setShowCreate(false); setCreateError('') }}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      <div className="admin-filters">
        <input placeholder="Search name or email..." value={search} onChange={e => { setSearch(e.target.value); setPage(1) }} className="admin-search-input" />
        <select value={roleFilter} onChange={e => { setRoleFilter(e.target.value); setPage(1) }}>
          <option value="">All Roles</option>
          <option value="owner">Owner</option>
          <option value="admin">Admin</option>
          <option value="user">User</option>
          <option value="viewer">Viewer</option>
        </select>
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(1) }}>
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="pending_verification">Pending</option>
          <option value="deleted">Deleted</option>
        </select>
        <select value={providerFilter} onChange={e => { setProviderFilter(e.target.value); setPage(1) }}>
          <option value="">All Providers</option>
          <option value="email">Email</option>
          <option value="google">Google</option>
        </select>
      </div>

      {loading && <div className="loading-state" style={{ padding: '40px 20px' }}><div className="spinner" /><p>Loading users...</p></div>}
      {!loading && users.length === 0 && !error && (
        <div className="empty-state" style={{ padding: '40px 20px' }}>
          <p className="subtle">No users found.</p>
        </div>
      )}
      {!loading && users.length > 0 && (
        <>
          <div className="card" style={{ padding: isMobile ? 8 : 0, overflow: 'hidden' }}>
            {isMobile ? (
              <div>
                {users.map(u => <AdminUserCard key={u.id} user={u} />)}
              </div>
            ) : (
              <table className="table" style={{ width: '100%' }}>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Verified</th>
                    <th>Provider</th>
                    <th>Last Login</th>
                    <th>Created</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id}>
                      <td>{u.full_name}</td>
                      <td>{u.email}</td>
                      <td><span className={`badge badge--${u.role === 'owner' || u.role === 'admin' ? 'info' : 'success'}`}>{u.role}</span></td>
                      <td><span className={`badge badge--${u.status === 'active' ? 'success' : 'danger'}`}>{u.status}</span></td>
                      <td>{u.email_verified ? '✓' : '—'}</td>
                      <td>{u.auth_provider || 'email'}</td>
                      <td>{u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : '—'}</td>
                      <td>{u.created_at ? new Date(u.created_at).toLocaleDateString() : '—'}</td>
                      <td><Link to={`/admin/users/${u.id}`} className="btn btn--sm">View</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          {totalPages > 1 && (
            <div className="admin-pagination">
              <button className="btn btn--sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</button>
              <span className="admin-page-info">Page {page} / {totalPages}</span>
              <button className="btn btn--sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
