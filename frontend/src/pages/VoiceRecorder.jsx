import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api.js'

const RECORDING_STATUS = { IDLE: 'idle', RECORDING: 'recording', STOPPED: 'stopped', CONVERTING: 'converting' }

export default function VoiceRecorder() {
  const [status, setStatus] = useState(RECORDING_STATUS.IDLE)
  const [session, setSession] = useState(null)
  const [transcripts, setTranscripts] = useState([])
  const [events, setEvents] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [draft, setDraft] = useState(null)
  const [savedSkill, setSavedSkill] = useState(null)
  const [saveName, setSaveName] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [intervalId, setIntervalId] = useState(null)

  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])
  const streamRef = useRef(null)
  const transcriptContainerRef = useRef(null)

  const tick = useCallback(() => {
    setElapsed(prev => prev + 1)
  }, [])

  useEffect(() => {
    return () => {
      if (intervalId) clearInterval(intervalId)
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop())
      }
    }
  }, [intervalId])

  const formatTime = (s) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`
  }

  const startRecording = async () => {
    setError('')
    setBusy(true)
    try {
      const sess = await api.recorderStart({ title: `Voice Recording ${new Date().toLocaleString()}`, source: 'voice' })
      setSession(sess)
      setStatus(RECORDING_STATUS.RECORDING)
      setTranscripts([])
      setEvents([])
      setDraft(null)
      setSavedSkill(null)
      setElapsed(0)

      const id = setInterval(tick, 1000)
      setIntervalId(id)

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      mediaRecorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = async (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
          if (status === 'recording') {
            try {
              const blob = new Blob([e.data], { type: 'audio/webm;codecs=opus' })
              const file = new File([blob], 'chunk.webm', { type: 'audio/webm;codecs=opus' })
              const formData = new FormData()
              formData.append('file', file)
              formData.append('language', 'auto')
              formData.append('mode', 'dictation')
              const res = await fetch('/api/voice-layer/transcribe', {
                method: 'POST',
                headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
                body: formData,
              })
              if (res.ok) {
                const data = await res.json()
                if (data.transcript?.trim()) {
                  setTranscripts(prev => [...prev, { text: data.transcript, time: new Date().toLocaleTimeString() }])
                }
              }
            } catch {
              // silent — transcription is best-effort during recording
            }
          }
        }
      }

      recorder.onstop = () => {
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(t => t.stop())
          streamRef.current = null
        }
      }

      recorder.start(3000)
    } catch (err) {
      setError(err.message || 'Could not start recording. Check microphone permissions.')
      setStatus(RECORDING_STATUS.IDLE)
    } finally {
      setBusy(false)
    }
  }

  const stopRecording = async () => {
    setBusy(true)
    setError('')
    try {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
      if (intervalId) { clearInterval(intervalId); setIntervalId(null) }

      const result = await api.recorderStop(session.session_id)
      const evts = await api.recorderListEvents(session.session_id)
      setSession(prev => prev ? { ...prev, status: result.status, event_count: result.event_count } : null)
      setEvents(evts || [])
      setStatus(RECORDING_STATUS.STOPPED)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const convertToSkill = async () => {
    setStatus(RECORDING_STATUS.CONVERTING)
    setError('')
    setBusy(true)
    try {
      const result = await api.recorderConvertToSkill(session.session_id, { name: saveName, description: `${transcripts.length} voice transcripts, ${events.length} events` })
      setDraft(result)
      setSaveName(result.name || '')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const approveAndSave = async () => {
    setBusy(true)
    setError('')
    try {
      const approved = await api.recorderApproveDraft(draft.draft_id)
      if (approved.status === 'approved') {
        const skill = await api.recorderSaveAsSkill(draft.draft_id)
        setSavedSkill(skill)
        setDraft(null)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const rejectDraft = async () => {
    setBusy(true)
    try {
      await api.recorderRejectDraft(draft.draft_id)
      setDraft(null)
    } catch { /* noop */ } finally { setBusy(false) }
  }

  const reset = () => {
    setStatus(RECORDING_STATUS.IDLE)
    setSession(null)
    setTranscripts([])
    setEvents([])
    setDraft(null)
    setSavedSkill(null)
    setError('')
    setElapsed(0)
    setSaveName('')
  }

  const isRecording = status === RECORDING_STATUS.RECORDING

  return (
    <div className="voice-recorder-page">
      <div className="page-header">
        <h2>Voice Recorder</h2>
        <p className="muted">Record workflows with voice and convert to reusable skills</p>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="vr-mic-section">
        <button
          className={`vr-mic-btn ${isRecording ? 'vr-mic-btn--recording' : ''}`}
          onClick={isRecording ? stopRecording : startRecording}
          disabled={busy}
          aria-label={isRecording ? 'Stop recording' : 'Start recording'}
        >
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            {isRecording ? (
              <rect x="6" y="6" width="12" height="12" rx="2" />
            ) : (
              <>
                <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="22" />
              </>
            )}
          </svg>
        </button>
        <div className="vr-status-label">
          {isRecording ? (
            <span className="vr-recording-badge">
              <span className="vr-recording-dot" /> RECORDING — {formatTime(elapsed)}
            </span>
          ) : status === RECORDING_STATUS.STOPPED ? (
            <span className="badge ok">Recording complete — {session?.event_count || 0} events</span>
          ) : (
            <span className="muted">Tap the microphone to start</span>
          )}
        </div>
      </div>

      {isRecording && transcripts.length > 0 && (
        <div className="vr-transcript-section" ref={transcriptContainerRef}>
          <h3>Live Transcription</h3>
          <div className="vr-transcript-list">
            {transcripts.map((t, i) => (
              <div key={i} className="vr-transcript-item">
                <span className="vr-transcript-time">{t.time}</span>
                <span className="vr-transcript-text">{t.text}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {isRecording && events.length === 0 && (
        <div className="card vr-hint-card">
          <p className="muted" style={{ textAlign: 'center', margin: 0 }}>
            Events captured by the system will appear here in real-time.
          </p>
        </div>
      )}

      {status === RECORDING_STATUS.STOPPED && !draft && !savedSkill && (
        <div className="card vr-actions-card">
          <h3>Recording Complete</h3>
          {transcripts.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4>Voice Transcripts ({transcripts.length})</h4>
              <div className="vr-transcript-list">
                {transcripts.map((t, i) => (
                  <div key={i} className="vr-transcript-item">
                    <span className="vr-transcript-time">{t.time}</span>
                    <span className="vr-transcript-text">{t.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {events.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4>Captured Events ({events.length})</h4>
              <div className="vr-event-list">
                {events.map((ev, i) => (
                  <div key={ev.event_order || i} className="vr-event-item">
                    <span className="badge">{ev.event_type}</span>
                    <span>{ev.target_description || ev.event_type}</span>
                    {ev.redacted && <span className="badge warning">REDACTED</span>}
                  </div>
                ))}
              </div>
            </div>
          )}
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Skill name (LLM will auto-generate if empty)..."
              value={saveName}
              onChange={(e) => setSaveName(e.target.value)}
              style={{ flex: 1, minWidth: 200 }}
            />
            <button className="primary" onClick={convertToSkill} disabled={busy}>
              {busy ? 'Converting...' : 'Convert to Skill'}
            </button>
            <button className="secondary" onClick={reset}>Discard</button>
          </div>
        </div>
      )}

      {draft && !savedSkill && (
        <div className="card vr-draft-card">
          <h3>Skill Draft: {draft.name || 'Unnamed'}</h3>
          {draft.trigger_phrases?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4>Trigger Phrases</h4>
              <div className="vr-phrase-list">
                {draft.trigger_phrases.map((p, i) => (
                  <span key={i} className="badge info">{p}</span>
                ))}
              </div>
            </div>
          )}
          {draft.steps?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4>Steps ({draft.steps.length})</h4>
              {draft.steps.map((s, i) => (
                <div key={i} className="vr-draft-step">
                  <strong>{i + 1}.</strong> {s.tool_name || s.type}: {s.description || s.target || ''}
                </div>
              ))}
            </div>
          )}
          {draft.description && <p className="muted">{draft.description}</p>}
          <div className="toolbar" style={{ marginTop: 16 }}>
            <button className="primary" onClick={approveAndSave} disabled={busy}>
              {busy ? 'Saving...' : 'Approve & Save Skill'}
            </button>
            <button className="secondary" onClick={rejectDraft} disabled={busy}>Reject</button>
          </div>
        </div>
      )}

      {savedSkill && (
        <div className="card vr-saved-card">
          <div className="alert success">
            Skill saved: <strong>{savedSkill.name}</strong> (ID: {savedSkill.skill_id || savedSkill.id})
          </div>
          <button className="primary" onClick={reset} style={{ marginTop: 12 }}>
            Record Another
          </button>
        </div>
      )}
    </div>
  )
}
