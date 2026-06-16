import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function RecordingSettings() {
  const [policy, setPolicy] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')

  const load = async () => {
    try {
      const data = await api.getRecordingPolicies()
      setPolicy(data)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [])

  const save = async () => {
    setBusy(true); setError(''); setSaved('')
    try {
      const updated = await api.updateRecordingPolicies(policy)
      setPolicy(updated)
      setSaved('Settings saved.')
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  const toggle = (k) => setPolicy((p) => ({ ...p, [k]: !p[k] }))

  if (!policy) return <div className="card">Loading recording settings…</div>

  return (
    <div>
      <div className="page-header"><h2>Workflow Recording Settings</h2></div>
      {error && <div className="alert error">{error}</div>}
      {saved && <div className="alert success">{saved}</div>}
      <div className="card">
        <h3>Recording</h3>
        <label className="toggle-row">
          <input type="checkbox" checked={policy.recording_enabled} onChange={() => toggle('recording_enabled')} />
          Enable workflow recording
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={policy.screenshots_enabled} onChange={() => toggle('screenshots_enabled')} />
          Capture screenshots during recording
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={policy.redact_sensitive_inputs} onChange={() => toggle('redact_sensitive_inputs')} />
          Redact sensitive input values
        </label>
      </div>
      <div className="card">
        <h3>Replay Approval</h3>
        <label className="toggle-row">
          <input type="checkbox" checked={policy.require_approval_for_replay} onChange={() => toggle('require_approval_for_replay')} />
          Require approval for replay
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={policy.require_approval_for_submit} onChange={() => toggle('require_approval_for_submit')} />
          Require approval for submit/save actions
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={policy.require_approval_for_write} onChange={() => toggle('require_approval_for_write')} />
          Require approval for write actions
        </label>
      </div>
      <div className="card">
        <h3>Allowed Apps</h3>
        <textarea rows={3} value={(policy.allowed_apps_json || []).join('\n')} onChange={(e) => setPolicy((p) => ({ ...p, allowed_apps_json: e.target.value.split('\n').filter(Boolean) }))} placeholder="One app per line" />
        <h3>Blocked Apps</h3>
        <textarea rows={3} value={(policy.blocked_apps_json || []).join('\n')} onChange={(e) => setPolicy((p) => ({ ...p, blocked_apps_json: e.target.value.split('\n').filter(Boolean) }))} placeholder="One app per line" />
        <h3>Allowed Domains</h3>
        <textarea rows={3} value={(policy.allowed_domains_json || []).join('\n')} onChange={(e) => setPolicy((p) => ({ ...p, allowed_domains_json: e.target.value.split('\n').filter(Boolean) }))} placeholder="One domain per line" />
        <h3>Blocked Domains</h3>
        <textarea rows={3} value={(policy.blocked_domains_json || []).join('\n')} onChange={(e) => setPolicy((p) => ({ ...p, blocked_domains_json: e.target.value.split('\n').filter(Boolean) }))} placeholder="One domain per line" />
      </div>
      <div className="card">
        <label>Notes</label>
        <textarea rows={2} value={policy.notes || ''} onChange={(e) => setPolicy((p) => ({ ...p, notes: e.target.value }))} placeholder="Optional notes" />
      </div>
      <button className="primary" onClick={save} disabled={busy}>Save Settings</button>
    </div>
  )
}
