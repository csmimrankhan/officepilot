import { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'

export default function VoiceCommandModal({ isOpen, onClose }) {
  const [mode, setMode] = useState('idle') // idle, recording, uploading, transcribing, detected, executing, completed, failed
  const [text, setText] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [debug, setDebug] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [sttStatus, setSttStatus] = useState(null)
  
  const mediaRecorderRef = useRef(null)
  const audioChunksRef = useRef([])
  const timerRef = useRef(null)

  useEffect(() => {
    if (isOpen) {
      api.getSTTStatus().then(setSttStatus).catch(err => console.error('Failed to fetch STT status', err))
    } else {
      cleanup()
    }
    return () => cleanup()
  }, [isOpen])

  const cleanup = () => {
    if (timerRef.current) clearInterval(timerRef.current)
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    setRecordingTime(0)
    audioChunksRef.current = []
  }

  const startRecording = async () => {
    setError('')
    setMode('recording')
    setRecordingTime(0)
    audioChunksRef.current = []

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        handleTranscribe(audioBlob)
        // stop all tracks
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => {
          if (prev >= 30) { // Max 30 seconds
            stopRecording()
            return 30
          }
          return prev + 1
        })
      }, 1000)

    } catch (err) {
      setError(err.message || 'Microphone access denied.')
      setMode('failed')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
    if (timerRef.current) clearInterval(timerRef.current)
    setMode('uploading')
  }

  const handleTranscribe = async (blob) => {
    setMode('transcribing')
    setError('')
    try {
      const res = await api.transcribeVoice(blob)
      if (res.status === 'failed') {
        throw new Error(res.error_message)
      }
      setText(res.transcript)
      handleParse(res.transcript)
    } catch (err) {
      setError(err.message || 'Transcription failed.')
      setMode('failed')
    }
  }

  const handleParse = async (input) => {
    setBusy(true)
    setError('')
    try {
      const res = await api.parseVoiceCommand(input)
      setResult(res)
      setMode('detected')
    } catch (err) {
      setError(err.message || 'Parsing failed.')
      setMode('failed')
    } finally {
      setBusy(false)
    }
  }

  const handleExecute = async () => {
    if (!result?.command_id) return
    setBusy(true)
    setError('')
    try {
      const res = await api.executeVoiceCommand(result.command_id)
      if (res.requires_approval) {
        setMode('detected')
      } else if (res.success) {
        setMode('completed')
      } else {
        setError(res.message)
        setMode('failed')
      }
    } catch (err) {
      setError(err.message || 'Execution failed.')
      setMode('failed')
    } finally {
      setBusy(false)
    }
  }

  const handleConfirm = async () => {
    if (!result?.command_id) return
    setBusy(true)
    setError('')
    try {
      const res = await api.confirmVoiceCommand(result.command_id)
      if (res.success) {
        setMode('completed')
      } else {
        setError(res.message)
        setMode('failed')
      }
    } catch (err) {
      setError(err.message || 'Confirmation failed.')
      setMode('failed')
    } finally {
      setBusy(false)
    }
  }

  const handleStop = async () => {
    try {
      await api.screenEmergencyStop()
      setMode('failed')
      setError('EMERGENCY STOP TRIGGERED')
    } catch (err) {
      setError('Stop failed: ' + err.message)
    }
  }

  const reset = () => {
    cleanup()
    setMode('idle')
    setText('')
    setResult(null)
    setError('')
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay">
      <div className="modal-content voice-modal">
        <div className="modal-header">
          <h3>
            Voice Assistant
            {sttStatus?.demo_mode && <span className="demo-badge">DEMO MODE</span>}
          </h3>
          <button className="close-button" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          {mode === 'idle' && (
            <div className="voice-idle">
              <button className="voice-mic-large" onClick={startRecording}>
                <span className="icon">🎤</span>
                Push to Talk
              </button>
              <div className="voice-fallback">
                <input
                  type="text"
                  placeholder="Or type a command..."
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleParse(text)}
                />
                <button className="secondary" onClick={() => handleParse(text)}>Send</button>
              </div>
            </div>
          )}

          {mode === 'recording' && (
            <div className="voice-status">
              <div className="pulse-mic recording">🎤</div>
              <p>Recording... {recordingTime}s / 30s</p>
              <button className="danger" onClick={stopRecording}>Stop & Process</button>
            </div>
          )}

          {(mode === 'uploading' || mode === 'transcribing') && (
            <div className="voice-status">
              <div className="spinner"></div>
              <p>{mode === 'uploading' ? 'Uploading audio...' : 'Transcribing...'}</p>
            </div>
          )}

          {mode === 'detected' && result && (
            <div className="voice-preview">
              <div className="transcript-box">
                <span className="label">I heard:</span>
                <p>"{result.raw_text || text}"</p>
              </div>

              {result.clarification_needed ? (
                <div className="clarification-box card warning">
                  <p><strong>{result.clarification_question}</strong></p>
                  <div className="suggestion-chips">
                    {result.suggestions.map(s => (
                      <button key={s} className="chip" onClick={() => { setText(s); handleParse(s); }}>
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div className={`action-preview-card ${result.risk_level === 'blocked' ? 'error' : result.needs_approval ? 'warning' : 'info'}`}>
                  <h4>{result.domain.toUpperCase()} Action</h4>
                  <p>{result.preview_message}</p>
                  {result.needs_approval && result.risk_level !== 'blocked' && (
                    <p className="approval-note">⚠️ This action requires your approval.</p>
                  )}
                </div>
              )}

              {debug && (
                <pre className="debug-json">
                  {JSON.stringify(result, null, 2)}
                </pre>
              )}

              <div className="modal-actions">
                <button className="secondary" onClick={reset}>Cancel</button>
                {result.clarification_needed ? null : result.risk_level === 'blocked' ? (
                  <button className="primary" onClick={reset}>Close</button>
                ) : result.needs_approval ? (
                  <button className="primary" onClick={handleConfirm} disabled={busy}>Approve & Execute</button>
                ) : (
                  <button className="primary" onClick={handleExecute} disabled={busy}>Execute</button>
                )}
                <button className="danger" onClick={handleStop}>Emergency Stop</button>
              </div>
            </div>
          )}

          {mode === 'completed' && (
            <div className="voice-success">
              <div className="icon-success">✅</div>
              <p>Action completed successfully.</p>
              <button className="primary" onClick={reset}>Start Over</button>
            </div>
          )}

          {mode === 'failed' && (
            <div className="voice-error">
              <div className="icon-error">❌</div>
              <p>{error || 'Something went wrong.'}</p>
              <button className="secondary" onClick={reset}>Try Again</button>
            </div>
          )}

          {error && mode !== 'failed' && <div className="alert error">{error}</div>}
        </div>

        <div className="modal-footer">
          <div className="stt-status-info">
            <span className={`status-dot ${sttStatus?.configured ? 'online' : 'offline'}`}></span>
            {sttStatus?.message || 'Checking status...'}
          </div>
          <div className="footer-right">
            <label className="checkbox-label">
              <input type="checkbox" checked={debug} onChange={e => setDebug(e.target.checked)} />
              Debug Mode
            </label>
            <a href="/voice" onClick={(e) => { e.preventDefault(); onClose(); window.location.href='/voice'; }} className="subtle-link">What can I say?</a>
          </div>
        </div>
      </div>
    </div>
  )
}
