import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function EmergencySafety() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState('')
  const [msg, setMsg] = useState('')
  const [reason, setReason] = useState('')

  useEffect(() => {
    api.getAutomationStatus().then(setStatus).catch(() => {})
  }, [])

  async function doKillSwitch() {
    setLoading('Stopping all automation...')
    setMsg('')
    try {
      const r = await api.activateKillSwitch(reason || 'Manual emergency stop')
      setMsg('Kill switch activated: ' + r.disabled_services?.join(', '))
      api.getAutomationStatus().then(setStatus).catch(() => {})
    } catch (e) {
      setMsg('Error: ' + e.message)
    } finally {
      setLoading('')
    }
  }

  async function doResume() {
    setLoading('Resuming automation...')
    setMsg('')
    try {
      const r = await api.resumeAutomation()
      setMsg('Kill switch deactivated. Automation may resume for enabled services.')
      api.getAutomationStatus().then(setStatus).catch(() => {})
    } catch (e) {
      setMsg('Error: ' + e.message)
    } finally {
      setLoading('')
    }
  }

  return (
    <div className="card">
      <h2>Emergency Safety Controls</h2>
      {msg && <p className={msg.startsWith('Error') ? 'error' : msg.includes('activated') ? 'error' : 'success'}>{msg}</p>}
      {loading && <p className="status">{loading}</p>}

      {status && (
        <div className="status-bar">
          <span className={`badge ${status.kill_switch_active ? 'badge--danger' : 'badge--ok'}`}>
            Kill Switch: {status.kill_switch_active ? 'ACTIVE' : 'Inactive'}
          </span>
          <span className={`badge ${status.browser_automation_blocked ? '' : 'badge--ok'}`}>
            Browser: {status.browser_automation_blocked ? 'Blocked' : 'Allowed'}
          </span>
          <span className={`badge ${status.screen_control_blocked ? '' : 'badge--ok'}`}>
            Screen: {status.screen_control_blocked ? 'Blocked' : 'Allowed'}
          </span>
          <span className={`badge ${status.workflow_recording_blocked ? '' : 'badge--ok'}`}>
            Recording: {status.workflow_recording_blocked ? 'Blocked' : 'Allowed'}
          </span>
          <span className={`badge ${status.accounting_sync_blocked ? '' : 'badge--ok'}`}>
            Accounting: {status.accounting_sync_blocked ? 'Blocked' : 'Allowed'}
          </span>
        </div>
      )}

      {!status?.kill_switch_active ? (
        <div className="card" style={{ border: '2px solid red' }}>
          <h3 style={{ color: 'red' }}>Emergency Stop</h3>
          <p>Pressing this button will immediately stop all automation:</p>
          <ul>
            <li>Browser automation</li>
            <li>Screen control</li>
            <li>Workflow recording &amp; replay</li>
            <li>Accounting sync</li>
          </ul>
          <div className="field">
            <label>Reason (optional)</label>
            <input type="text" value={reason} onChange={e => setReason(e.target.value)} placeholder="Why are you stopping automation?" />
          </div>
          <button className="btn btn--danger" onClick={doKillSwitch} disabled={loading !== ''}>
            {loading || 'STOP ALL AUTOMATION'}
          </button>
        </div>
      ) : (
        <div className="card" style={{ border: '2px solid orange' }}>
          <h3 style={{ color: 'orange' }}>Automation Paused</h3>
          <p>The global kill switch is active. All automation services are blocked.</p>
          <button className="btn btn--warning" onClick={doResume} disabled={loading !== ''}>
            {loading || 'Resume Automation'}
          </button>
        </div>
      )}
    </div>
  )
}
