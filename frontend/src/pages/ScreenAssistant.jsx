import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function ScreenAssistant() {
  const [status, setStatus] = useState(null)
  const [context, setContext] = useState(null)
  const [screenshot, setScreenshot] = useState(null)
  const [ocrResult, setOcrResult] = useState(null)
  const [ocrStatus, setOcrStatus] = useState(null)
  const [summary, setSummary] = useState(null)
  const [actions, setActions] = useState([])
  const [loading, setLoading] = useState('')
  const [error, setError] = useState('')
  const [sessionId, setSessionId] = useState(null)

  useEffect(() => {
    api.getScreenStatus().then(s => {
      setStatus(s)
      if (s.session_id) setSessionId(s.session_id)
    }).catch(() => {})
    api.listScreenActions(null, 10).then(setActions).catch(() => {})
    api.getScreenOcrStatus().then(setOcrStatus).catch(() => {})
  }, [])

  async function startSession() {
    setLoading('Starting session...')
    setError('')
    try {
      const r = await api.startScreenSession()
      setSessionId(r.session_id)
      setStatus(prev => ({ ...prev, session_active: true, session_id: r.session_id }))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading('')
    }
  }

  async function endSession() {
    if (!sessionId) return
    setLoading('Ending session...')
    try {
      await api.endScreenSession(sessionId)
      setSessionId(null)
      setContext(null)
      setScreenshot(null)
      setOcrResult(null)
      setStatus(prev => ({ ...prev, session_active: false, session_id: null }))
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading('')
    }
  }

  async function doRead() {
    setLoading('Reading screen...')
    setError('')
    try {
      const r = await api.readScreenContext()
      setContext(r)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading('')
    }
  }

  async function doCapture() {
    setLoading('Capturing screenshot...')
    setError('')
    try {
      const r = await api.captureScreenshot()
      setScreenshot(r)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading('')
    }
  }

  async function doOcr() {
    setLoading('Running OCR...')
    setError('')
    try {
      const r = await api.ocrScreen()
      setOcrResult(r)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading('')
    }
  }

  async function doSummarize() {
    setLoading('Summarizing...')
    setError('')
    try {
      const r = await api.summarizeScreen()
      setSummary(r)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading('')
    }
  }

  async function doEmergencyStop() {
    setLoading('Emergency stop...')
    try {
      await api.screenEmergencyStop(sessionId)
      setSessionId(null)
      setStatus(prev => ({ ...prev, session_active: false, session_id: null }))
      setContext(null)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading('')
    }
  }

  async function doExecuteAll(actionId) {
    setLoading('Executing all approved steps...')
    setError('')
    try {
      const r = await api.executeAllApprovedSteps(actionId)
      api.listScreenActions(null, 10).then(setActions).catch(() => {})
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading('')
    }
  }

  const disabled = loading !== ''

  return (
    <div className="card">
      <h2>Screen Assistant</h2>
      {error && <p className="error">{error}</p>}
      {loading && <p className="status">{loading}</p>}

      <div className="button-row">
        {!sessionId ? (
          <button className="btn" onClick={startSession} disabled={disabled}>Start Session</button>
        ) : (
          <>
            <button className="btn" onClick={endSession} disabled={disabled}>End Session</button>
            <button className="btn btn--danger" onClick={doEmergencyStop} disabled={disabled}>Emergency Stop</button>
          </>
        )}
      </div>

      {status && (
        <div className="status-bar">
          <span className="badge">Permission Level: {status.permission_level}</span>
          <span className="badge">Session: {status.session_active ? 'Active' : 'Inactive'}</span>
          {status.active_app && <span className="badge">App: {status.active_app}</span>}
          {status.active_window_title && <span className="badge">Window: {status.active_window_title}</span>}
          {ocrStatus && <span className="badge">OCR: {ocrStatus.available ? ocrStatus.engine : 'N/A'}</span>}
        </div>
      )}

      {sessionId && (
        <div className="button-row">
          <button className="btn" onClick={doRead} disabled={disabled}>Read Current Window</button>
          <button className="btn" onClick={doCapture} disabled={disabled}>Capture Screenshot</button>
          <button className="btn" onClick={doOcr} disabled={disabled}>Run OCR</button>
          <button className="btn" onClick={doSummarize} disabled={disabled}>Summarize</button>
        </div>
      )}

      {context && (
        <div className="card">
          <h3>Screen Context</h3>
          <p><strong>App:</strong> {context.active_app}</p>
          <p><strong>Window:</strong> {context.active_window_title}</p>
          <p><strong>Summary:</strong> {context.summary}</p>
          {context.ocr_text && <p><strong>OCR Text:</strong> <pre>{context.ocr_text}</pre></p>}
          {context.screenshot_path && <img src={`file:///${context.screenshot_path}`} alt="Screenshot" className="screenshot-preview" />}
        </div>
      )}

      {screenshot && screenshot.screenshot_path && (
        <div className="card">
          <h3>Screenshot</h3>
          <p>Path: {screenshot.screenshot_path}</p>
          <img src={`file:///${screenshot.screenshot_path}`} alt="Screenshot" className="screenshot-preview" />
        </div>
      )}

      {ocrResult && (
        <div className="card">
          <h3>OCR Result</h3>
          <p>Lines: {ocrResult.lines?.length || 0}</p>
          {ocrResult.lines?.map((line, i) => <p key={i}>{line}</p>)}
        </div>
      )}

      {summary && (
        <div className="card">
          <h3>Screen Summary</h3>
          <p>{summary.summary}</p>
          <p>App: {summary.app}</p>
          <p>Window: {summary.window}</p>
        </div>
      )}

      {actions.length > 0 && (
        <div className="card">
          <h3>Recent Actions</h3>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>App</th>
                <th>Risk</th>
                <th>Status</th>
                <th>Browser Run</th>
                <th>Stopped By</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {actions.slice(0, 10).map(a => (
                <tr key={a.id}>
                  <td>{a.id}</td>
                  <td>{a.action_type}</td>
                  <td>{a.app_name}</td>
                  <td>{a.risk_level}</td>
                  <td>{a.status}</td>
                  <td>{a.browser_action_run_id || ''}</td>
                  <td>{a.stopped_by || ''}</td>
                  <td>
                    {a.approval_status === 'approved' && a.status !== 'completed' && a.status !== 'cancelled' && (
                      <button className="btn btn--small" onClick={() => doExecuteAll(a.id)} disabled={disabled}>Execute All</button>
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
