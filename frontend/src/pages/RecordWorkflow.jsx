import { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'

export default function RecordWorkflow() {
  const [session, setSession] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [eventLog, setEventLog] = useState([])
  const [saveName, setSaveName] = useState('')
  const [saveDesc, setSaveDesc] = useState('')
  const [savedWorkflow, setSavedWorkflow] = useState(null)
  const wsRef = useRef(null)

  useEffect(() => {
    return () => { if (wsRef.current) wsRef.current.close() }
  }, [])

  const start = async () => {
    setBusy(true); setError('')
    try {
      const data = await api.startRecording()
      setSession(data)
      setEventLog([])
      setSavedWorkflow(null)
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  const stop = async () => {
    if (!session) return
    setBusy(true); setError('')
    try {
      const data = await api.stopRecording(session.session_id)
      setSession((s) => ({ ...s, status: 'stopped', event_count: data.event_count }))
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  const save = async () => {
    if (!session || !saveName.trim()) return
    setBusy(true); setError('')
    try {
      const data = await api.saveRecordingSession(session.session_id, saveName.trim(), saveDesc.trim())
      setSavedWorkflow(data)
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  const simulateEvent = async (type) => {
    if (!session) return
    const templates = {
      click: { event_type: 'click', app_name: 'InvoicePilot', target_description: 'Clicked Approve button' },
      type_text: { event_type: 'type_text', app_name: 'InvoicePilot', input_value: 'test value', target_description: 'Typed in vendor field' },
      open_url: { event_type: 'open_url', app_name: 'Browser', target_description: 'Opened test form' },
      open_file: { event_type: 'open_file', app_name: 'Explorer', target_description: 'Opened invoice PDF' },
      copy: { event_type: 'copy', app_name: 'InvoicePilot', target_description: 'Copied vendor name' },
      paste: { event_type: 'paste', app_name: 'Test Form', input_value: 'ACME Corp', target_description: 'Pasted vendor name into form' },
      browser_fill: { event_type: 'browser_fill_field', app_name: 'Browser', target_description: 'Filled invoice amount field', input_value: '460.64' },
    }
    const event = templates[type] || { event_type: type, app_name: 'Unknown' }
    try {
      const res = await api.captureEvent(session.session_id, event)
      setEventLog((prev) => [...prev, { index: res.event_index, type, redacted: res.redacted }])
    } catch (err) {
      setError(err.message)
    }
  }

  const recording = session && session.status === 'recording'

  return (
    <div>
      <div className="page-header"><h2>Record Workflow</h2></div>
      {error && <div className="alert error">{error}</div>}
      {session && (
        <div className={`alert ${recording ? 'warning' : 'info'}`} style={{ fontWeight: 'bold' }}>
          {recording ? '🔴 RECORDING ACTIVE' : 'Recording stopped'} — Session #{session.session_id} ({session.event_count || 0} events)
        </div>
      )}
      <div className="card">
        {!session ? (
          <button className="primary" onClick={start} disabled={busy}>Start Recording</button>
        ) : recording ? (
          <div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
              <button className="danger" onClick={stop} disabled={busy}>Stop Recording</button>
              <button className="secondary" onClick={() => simulateEvent('click')}>Simulate Click</button>
              <button className="secondary" onClick={() => simulateEvent('type_text')}>Simulate Type</button>
              <button className="secondary" onClick={() => simulateEvent('open_url')}>Simulate Open URL</button>
              <button className="secondary" onClick={() => simulateEvent('open_file')}>Simulate Open File</button>
              <button className="secondary" onClick={() => simulateEvent('copy')}>Simulate Copy</button>
              <button className="secondary" onClick={() => simulateEvent('paste')}>Simulate Paste</button>
              <button className="secondary" onClick={() => simulateEvent('browser_fill')}>Simulate Browser Fill</button>
            </div>
            {eventLog.length > 0 && (
              <div>
                <h4>Captured Events ({eventLog.length})</h4>
                <table>
                  <thead><tr><th>#</th><th>Type</th><th>Redacted</th></tr></thead>
                  <tbody>
                    {eventLog.map((ev, i) => (
                      <tr key={i}><td>{ev.index}</td><td>{ev.type}</td><td>{ev.redacted ? 'Yes' : 'No'}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ) : (
          <div>
            <p>Recording complete — {session.event_count || 0} events captured.</p>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <input type="text" placeholder="Workflow name…" value={saveName} onChange={(e) => setSaveName(e.target.value)} style={{ maxWidth: 280 }} />
              <input type="text" placeholder="Description (optional)…" value={saveDesc} onChange={(e) => setSaveDesc(e.target.value)} style={{ maxWidth: 280 }} />
              <button className="primary" onClick={save} disabled={busy || !saveName.trim()}>Save as Workflow</button>
            </div>
            {savedWorkflow && (
              <div className="alert success" style={{ marginTop: 8 }}>
                Workflow saved: <strong>{savedWorkflow.name}</strong> (ID: {savedWorkflow.workflow_id})
              </div>
            )}
            <button className="secondary" onClick={start} disabled={busy} style={{ marginTop: 8 }}>Record Another</button>
          </div>
        )}
      </div>
    </div>
  )
}
