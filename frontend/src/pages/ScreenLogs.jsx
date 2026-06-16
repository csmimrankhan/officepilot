import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function ScreenLogs() {
  const [tab, setTab] = useState('actions')
  const [actions, setActions] = useState([])
  const [sessions, setSessions] = useState([])
  const [selectedAction, setSelectedAction] = useState(null)
  const [steps, setSteps] = useState([])
  const [loading, setLoading] = useState('')

  useEffect(() => {
    loadActions()
    loadSessions()
  }, [])

  async function loadActions() {
    setLoading('Loading...')
    try {
      const r = await api.listScreenActions(null, 50)
      setActions(r)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading('')
    }
  }

  async function loadSessions() {
    try {
      const r = await api.listScreenSessions(20)
      setSessions(r)
    } catch (e) {
      console.error(e)
    }
  }

  async function viewSteps(actionId) {
    setLoading('Loading steps...')
    try {
      const r = await api.listScreenActionSteps(actionId)
      setSteps(r)
      setSelectedAction(actionId)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading('')
    }
  }

  return (
    <div className="card">
      <h2>Screen Control Logs</h2>
      {loading && <p className="status">{loading}</p>}

      <div className="tabs">
        <button className={`tab ${tab === 'actions' ? 'active' : ''}`} onClick={() => setTab('actions')}>Actions</button>
        <button className={`tab ${tab === 'sessions' ? 'active' : ''}`} onClick={() => setTab('sessions')}>Sessions</button>
      </div>

      {tab === 'actions' && (
        <div>
          <h3>Screen Actions</h3>
          {actions.length === 0 && <p>No actions yet.</p>}
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>App</th>
                <th>Window</th>
                <th>Risk</th>
                <th>Approval</th>
                <th>Status</th>
                <th>Browser Run</th>
                <th>Stopped By</th>
                <th>Error</th>
                <th>Steps</th>
              </tr>
            </thead>
            <tbody>
              {actions.map(a => (
                <tr key={a.id}>
                  <td>{a.id}</td>
                  <td>{a.action_type}</td>
                  <td>{a.app_name}</td>
                  <td>{a.window_title}</td>
                  <td><span className={`badge badge--${a.risk_level}`}>{a.risk_level}</span></td>
                  <td>{a.approval_status}</td>
                  <td>{a.status}</td>
                  <td>{a.browser_action_run_id || ''}</td>
                  <td>{a.stopped_by || ''}</td>
                  <td className="error-text">{a.error_message || ''}</td>
                  <td>
                    <button className="btn btn--small" onClick={() => viewSteps(a.id)}>Steps</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {selectedAction && steps.length > 0 && (
            <div className="card">
              <h4>Steps for Action #{selectedAction}</h4>
              <table>
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Type</th>
                    <th>Target</th>
                    <th>Status</th>
                    <th>Browser Step</th>
                    <th>Stopped By</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {steps.map(s => (
                    <tr key={s.id}>
                      <td>{s.step_order}</td>
                      <td>{s.step_type}</td>
                      <td>{s.target_description}</td>
                      <td>{s.status}</td>
                      <td>{s.browser_action_step_id || ''}</td>
                      <td>{s.stopped_by || ''}</td>
                      <td className="error-text">{s.error_message || ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === 'sessions' && (
        <div>
          <h3>Screen Sessions</h3>
          {sessions.length === 0 && <p>No sessions yet.</p>}
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>User</th>
                <th>Status</th>
                <th>Level</th>
                <th>App</th>
                <th>Window</th>
                <th>Started</th>
                <th>Ended</th>
                <th>Stopped By</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map(s => (
                <tr key={s.id}>
                  <td>{s.id}</td>
                  <td>{s.user_id}</td>
                  <td>{s.status}</td>
                  <td>{s.permission_level}</td>
                  <td>{s.active_app}</td>
                  <td>{s.active_window_title}</td>
                  <td>{s.started_at || '-'}</td>
                  <td>{s.ended_at || '-'}</td>
                  <td>{s.stopped_by || '-'}</td>
                  <td>{s.stop_reason || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
