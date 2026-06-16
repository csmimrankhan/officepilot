import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function ScreenSettings() {
  const [policy, setPolicy] = useState(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [status, setStatus] = useState(null)
  const [capabilities, setCapabilities] = useState(null)

  useEffect(() => {
    api.getScreenPolicies().then(setPolicy).catch(() => {})
    api.getScreenStatus().then(setStatus).catch(() => {})
    api.getScreenCapabilities().then(setCapabilities).catch(() => {})
  }, [])

  function update(field, value) {
    setPolicy(p => ({ ...p, [field]: value }))
  }

  async function save() {
    setSaving(true)
    setMsg('')
    try {
      const body = {
        enabled: policy.enabled,
        permission_level: policy.permission_level,
        screenshots_enabled: policy.screenshots_enabled,
        ocr_enabled: policy.ocr_enabled,
        click_enabled: policy.click_enabled,
        type_enabled: policy.type_enabled,
        clipboard_enabled: policy.clipboard_enabled,
        require_approval_for_click: policy.require_approval_for_click,
        require_approval_for_type: policy.require_approval_for_type,
        require_approval_for_submit: policy.require_approval_for_submit,
        require_approval_for_clipboard: policy.require_approval_for_clipboard,
        emergency_stop_enabled: policy.emergency_stop_enabled,
        allowed_apps: (policy.allowed_apps || []).filter(Boolean),
        blocked_apps: (policy.blocked_apps || []).filter(Boolean),
        allowed_folders: (policy.allowed_folders || []).filter(Boolean),
        blocked_domains: (policy.blocked_domains || []).filter(Boolean),
        notes: policy.notes || '',
      }
      const result = await api.updateScreenPolicies(body)
      setPolicy(result)
      setMsg('Settings saved')
    } catch (e) {
      setMsg('Error: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  if (!policy) return <div className="card">Loading...</div>

  const LEVELS = [
    { value: 0, label: '0 - Disabled' },
    { value: 1, label: '1 - Read-only screen assistance' },
    { value: 2, label: '2 - Copy/open only' },
    { value: 3, label: '3 - Edit with approval' },
    { value: 4, label: '4 - Controlled automation (approved apps)' },
  ]

  return (
    <div className="card">
      <h2>Screen Control Settings</h2>
      {msg && <p className={msg.startsWith('Error') ? 'error' : 'success'}>{msg}</p>}
      {status && (
        <div className="status-bar">
          <span className={status.session_active ? 'badge badge--ok' : 'badge'}>
            Session: {status.session_active ? 'Active' : 'Inactive'}
          </span>
          <span className="badge">
            App: {status.active_app || 'unknown'}
          </span>
        </div>
      )}

      {capabilities && (
        <div className="status-bar" style={{marginBottom: '1rem'}}>
          <span className="badge">OCR: {capabilities.ocr_available ? capabilities.ocr_engine : 'Unavailable'}</span>
          <span className="badge">Click: {capabilities.click_enabled ? 'Enabled' : 'Disabled'}</span>
          <span className="badge">Type: {capabilities.type_enabled ? 'Enabled' : 'Disabled'}</span>
          <span className="badge">Clipboard: {capabilities.clipboard_enabled ? 'Enabled' : 'Disabled'}</span>
          <span className="badge">PyAutoGUI: {capabilities.pyautogui_available ? 'Available' : 'N/A'}</span>
        </div>
      )}

      <label className="toggle">
        <input type="checkbox" checked={policy.enabled} onChange={e => update('enabled', e.target.checked)} />
        Enable screen control
      </label>

      <div className="field">
        <label>Permission level</label>
        <select value={policy.permission_level} onChange={e => update('permission_level', Number(e.target.value))}>
          {LEVELS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
        </select>
      </div>

      <h3>Capabilities</h3>
      <label className="toggle">
        <input type="checkbox" checked={policy.screenshots_enabled} onChange={e => update('screenshots_enabled', e.target.checked)} />
        Screenshots enabled
      </label>
      <label className="toggle">
        <input type="checkbox" checked={policy.ocr_enabled} onChange={e => update('ocr_enabled', e.target.checked)} />
        OCR enabled
      </label>
      <label className="toggle">
        <input type="checkbox" checked={policy.click_enabled} onChange={e => update('click_enabled', e.target.checked)} />
        Click enabled
      </label>
      <label className="toggle">
        <input type="checkbox" checked={policy.type_enabled} onChange={e => update('type_enabled', e.target.checked)} />
        Type enabled
      </label>
      <label className="toggle">
        <input type="checkbox" checked={policy.clipboard_enabled} onChange={e => update('clipboard_enabled', e.target.checked)} />
        Clipboard enabled
      </label>

      <h3>Approval requirements</h3>
      <label className="toggle">
        <input type="checkbox" checked={policy.require_approval_for_click} onChange={e => update('require_approval_for_click', e.target.checked)} />
        Require approval for click
      </label>
      <label className="toggle">
        <input type="checkbox" checked={policy.require_approval_for_type} onChange={e => update('require_approval_for_type', e.target.checked)} />
        Require approval for type
      </label>
      <label className="toggle">
        <input type="checkbox" checked={policy.require_approval_for_submit} onChange={e => update('require_approval_for_submit', e.target.checked)} />
        Require approval for submit
      </label>
      <label className="toggle">
        <input type="checkbox" checked={policy.require_approval_for_clipboard} onChange={e => update('require_approval_for_clipboard', e.target.checked)} />
        Require approval for clipboard
      </label>
      <label className="toggle">
        <input type="checkbox" checked={policy.emergency_stop_enabled} onChange={e => update('emergency_stop_enabled', e.target.checked)} />
        Emergency stop enabled
      </label>

      <h3>Allow/Block lists</h3>
      <div className="field">
        <label>Allowed apps (one per line)</label>
        <textarea
          rows={3}
          value={(policy.allowed_apps || []).join('\n')}
          onChange={e => update('allowed_apps', e.target.value.split('\n').map(s => s.trim()).filter(Boolean))}
        />
      </div>
      <div className="field">
        <label>Blocked apps (one per line)</label>
        <textarea
          rows={3}
          value={(policy.blocked_apps || []).join('\n')}
          onChange={e => update('blocked_apps', e.target.value.split('\n').map(s => s.trim()).filter(Boolean))}
        />
      </div>
      <div className="field">
        <label>Allowed folders (one per line)</label>
        <textarea
          rows={2}
          value={(policy.allowed_folders || []).join('\n')}
          onChange={e => update('allowed_folders', e.target.value.split('\n').map(s => s.trim()).filter(Boolean))}
        />
      </div>
      <div className="field">
        <label>Blocked domains (one per line)</label>
        <textarea
          rows={2}
          value={(policy.blocked_domains || []).join('\n')}
          onChange={e => update('blocked_domains', e.target.value.split('\n').map(s => s.trim()).filter(Boolean))}
        />
      </div>

      <div className="field">
        <label>Notes</label>
        <input type="text" value={policy.notes || ''} onChange={e => update('notes', e.target.value)} />
      </div>

      <button className="btn" onClick={save} disabled={saving}>
        {saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  )
}
