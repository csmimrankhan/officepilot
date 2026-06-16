import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function SafetyPolicyCenter() {
  const [policy, setPolicy] = useState(null)
  const [myPerms, setMyPerms] = useState(null)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    api.getSafetyPolicies().then(setPolicy).catch(() => {})
    api.getMyPermissions().then(setMyPerms).catch(() => {})
  }, [])

  function update(field, value) {
    setPolicy(p => ({ ...p, [field]: value }))
  }

  async function save() {
    setSaving(true)
    setMsg('')
    try {
      const body = {
        cloud_ai_allowed: policy.cloud_ai_allowed,
        browser_automation_enabled: policy.browser_automation_enabled,
        screen_control_enabled: policy.screen_control_enabled,
        workflow_recording_enabled: policy.workflow_recording_enabled,
        accounting_sync_enabled: policy.accounting_sync_enabled,
        voice_enabled: policy.voice_enabled,
        screenshots_enabled: policy.screenshots_enabled,
        ocr_enabled: policy.ocr_enabled,
        require_approval_for_write: policy.require_approval_for_write,
        require_snapshot_for_file_changes: policy.require_snapshot_for_file_changes,
        block_unknown_apps: policy.block_unknown_apps,
        block_unknown_domains: policy.block_unknown_domains,
      }
      await api.updateSafetyPolicies(body)
      setMsg('Safety policies saved.')
    } catch (e) {
      setMsg('Error: ' + e.message)
    } finally {
      setSaving(false)
    }
  }

  const canManage = myPerms?.permissions?.includes('manage_safety_policies') || myPerms?.role === 'owner'

  if (!policy) return <div className="card">Loading...</div>

  return (
    <div className="card">
      <h2>Safety Policy Center</h2>
      {!canManage && (
        <p className="error">You do not have permission to change safety policies.</p>
      )}
      {msg && <p className={msg.startsWith('Error') ? 'error' : 'success'}>{msg}</p>}

      <div className="status-bar">
        <span className={`badge ${policy.cloud_ai_allowed ? 'badge--ok' : ''}`}>Cloud AI: {policy.cloud_ai_allowed ? 'Allowed' : 'Disabled'}</span>
        <span className={`badge ${policy.browser_automation_enabled ? 'badge--warn' : ''}`}>Browser: {policy.browser_automation_enabled ? 'Enabled' : 'Disabled'}</span>
        <span className={`badge ${policy.screen_control_enabled ? 'badge--warn' : ''}`}>Screen: {policy.screen_control_enabled ? 'Enabled' : 'Disabled'}</span>
        <span className={`badge ${policy.workflow_recording_enabled ? 'badge--warn' : ''}`}>Recording: {policy.workflow_recording_enabled ? 'Enabled' : 'Disabled'}</span>
        <span className={`badge ${policy.accounting_sync_enabled ? 'badge--warn' : ''}`}>Accounting: {policy.accounting_sync_enabled ? 'Enabled' : 'Disabled'}</span>
      </div>

      <h3>Feature Toggles</h3>
      <label className="toggle"><input type="checkbox" checked={policy.cloud_ai_allowed} disabled={!canManage} onChange={e => update('cloud_ai_allowed', e.target.checked)} /> Cloud AI processing</label>
      <label className="toggle"><input type="checkbox" checked={policy.browser_automation_enabled} disabled={!canManage} onChange={e => update('browser_automation_enabled', e.target.checked)} /> Browser automation</label>
      <label className="toggle"><input type="checkbox" checked={policy.screen_control_enabled} disabled={!canManage} onChange={e => update('screen_control_enabled', e.target.checked)} /> Screen control</label>
      <label className="toggle"><input type="checkbox" checked={policy.workflow_recording_enabled} disabled={!canManage} onChange={e => update('workflow_recording_enabled', e.target.checked)} /> Workflow recording</label>
      <label className="toggle"><input type="checkbox" checked={policy.accounting_sync_enabled} disabled={!canManage} onChange={e => update('accounting_sync_enabled', e.target.checked)} /> Accounting sync</label>
      <label className="toggle"><input type="checkbox" checked={policy.voice_enabled} disabled={!canManage} onChange={e => update('voice_enabled', e.target.checked)} /> Voice commands</label>
      <label className="toggle"><input type="checkbox" checked={policy.screenshots_enabled} disabled={!canManage} onChange={e => update('screenshots_enabled', e.target.checked)} /> Screenshots</label>
      <label className="toggle"><input type="checkbox" checked={policy.ocr_enabled} disabled={!canManage} onChange={e => update('ocr_enabled', e.target.checked)} /> OCR</label>

      <h3>Safety Requirements</h3>
      <label className="toggle"><input type="checkbox" checked={policy.require_approval_for_write} disabled={!canManage} onChange={e => update('require_approval_for_write', e.target.checked)} /> Require approval for all data-changing actions</label>
      <label className="toggle"><input type="checkbox" checked={policy.require_snapshot_for_file_changes} disabled={!canManage} onChange={e => update('require_snapshot_for_file_changes', e.target.checked)} /> Require snapshot before file changes</label>
      <label className="toggle"><input type="checkbox" checked={policy.block_unknown_apps} disabled={!canManage} onChange={e => update('block_unknown_apps', e.target.checked)} /> Block unknown apps</label>
      <label className="toggle"><input type="checkbox" checked={policy.block_unknown_domains} disabled={!canManage} onChange={e => update('block_unknown_domains', e.target.checked)} /> Block unknown domains</label>

      {canManage && (
        <button className="btn" onClick={save} disabled={saving}>
          {saving ? 'Saving...' : 'Save Policies'}
        </button>
      )}
    </div>
  )
}
