import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function PermissionsManager() {
  const [permissions, setPermissions] = useState([])
  const [myPerms, setMyPerms] = useState(null)
  const [roles, setRoles] = useState([])
  const [permNames, setPermNames] = useState([])
  const [selectedRole, setSelectedRole] = useState('')
  const [msg, setMsg] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getMyPermissions().then(setMyPerms).catch(() => {})
    api.listPermissions().then(setPermissions).catch(() => {})
    api.listRoles().then(setRoles).catch(() => {})
    api.listPermissionNames().then(setPermNames).catch(() => {})
  }, [])

  const isManager = myPerms?.permissions?.includes('manage_permissions') || myPerms?.role === 'owner'

  const rolePerms = permissions.filter(p => p.role === selectedRole)

  function getEnabled(name) {
    const rp = rolePerms.find(p => p.permission_name === name)
    return rp ? rp.enabled : true
  }

  async function togglePermission(name) {
    const current = getEnabled(name)
    setSaving(true)
    setMsg('')
    try {
      const result = await api.updateRolePermissions(selectedRole, [
        { permission_name: name, enabled: !current },
      ])
      setPermissions(prev => prev.map(p => {
        const upd = result.find(r => r.id === p.id)
        return upd || p
      }))
      setMsg('Permission updated.')
    } catch (e) {
      setMsg('Error: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card">
      <h2>Role Permissions</h2>
      {!isManager && <p className="error">You do not have permission to manage roles.</p>}
      {msg && <p className={msg.startsWith('Error') ? 'error' : 'success'}>{msg}</p>}

      <div className="field">
        <label>Select role</label>
        <select value={selectedRole} onChange={e => setSelectedRole(e.target.value)}>
          <option value="">-- Choose a role --</option>
          {roles.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
      </div>

      {selectedRole && (
        <div>
          <h3>Permissions for: <code>{selectedRole}</code></h3>
          <table>
            <thead>
              <tr>
                <th>Permission</th>
                <th>Enabled</th>
                <th>Toggle</th>
              </tr>
            </thead>
            <tbody>
              {permNames.map(name => (
                <tr key={name}>
                  <td><code>{name}</code></td>
                  <td>{getEnabled(name) ? 'Yes' : 'No'}</td>
                  <td>
                    {isManager && (
                      <button
                        className="btn btn--small"
                        onClick={() => togglePermission(name)}
                        disabled={saving}
                      >
                        {getEnabled(name) ? 'Disable' : 'Enable'}
                      </button>
                    )}
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
