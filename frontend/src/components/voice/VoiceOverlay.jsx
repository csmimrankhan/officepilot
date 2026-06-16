import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../../api.js'

const STATUS_LABELS = {
  idle: 'Ready',
  recording: 'Recording...',
  transcribing: 'Transcribing...',
  ready_to_paste: 'Ready to paste',
  pasted: 'Pasted!',
  cancelled: 'Cancelled',
  failed: 'Failed',
}

export default function VoiceOverlay({ mode = 'dictation', onClose, onTranscript, onOpenAgent }) {
  const [status, setStatus] = useState('idle')
  const [transcript, setTranscript] = useState('')
  const [aiOutput, setAiOutput] = useState('')
  const [timer, setTimer] = useState(0)
  const [error, setError] = useState('')
  const [mediaRecorder, setMediaRecorder] = useState(null)
  const timerRef = useRef(null)
  const chunksRef = useRef([])

  const formatTime = (s) => {
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
  }

  const startRecording = useCallback(async () => {
    setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
      chunksRef.current = []
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        setStatus('transcribing')
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        await transcribeAudio(blob)
      }
      recorder.onerror = () => setError('Recording error')
      recorder.start()
      setMediaRecorder(recorder)
      setStatus('recording')
      setTimer(0)
      timerRef.current = setInterval(() => setTimer(t => t + 1), 1000)
    } catch (err) {
      setError(`Microphone access denied: ${err.message}`)
      setStatus('failed')
    }
  }, [mode])

  const stopRecording = useCallback(() => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    }
    if (timerRef.current) clearInterval(timerRef.current)
  }, [mediaRecorder])

  const transcribeAudio = async (blob) => {
    try {
      const formData = new FormData()
      formData.append('file', blob, 'recording.webm')
      formData.append('mode', mode)
      formData.append('language', 'auto')

      const res = await fetch(`${api.base}/api/voice-layer/transcribe`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}` },
        body: formData,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || 'Transcription failed')
      }
      const data = await res.json()
      setTranscript(data.transcript || '')
      setAiOutput(data.ai_output || '')

      if (data.ai_output) {
        setStatus('ready_to_paste')
      } else {
        setStatus('ready_to_paste')
      }

      if (onTranscript) onTranscript(data.transcript, data.ai_output)
    } catch (err) {
      setError(err.message)
      setStatus('failed')
    }
  }

  const handlePaste = async () => {
    const text = aiOutput || transcript
    if (!text) return
    try {
      const res = await fetch(`${api.base}/api/voice-layer/paste`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}`,
        },
        body: new URLSearchParams({ text, confirm: 'false' }),
      })
      const data = await res.json()
      if (data.ok) {
        setStatus('pasted')
        setTimeout(() => { if (onClose) onClose() }, 1500)
      } else {
        setError(data.error || 'Paste failed')
      }
    } catch (err) {
      setError(err.message)
    }
  }

  const handleCancel = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    }
    if (timerRef.current) clearInterval(timerRef.current)
    setStatus('cancelled')
    setTimeout(() => { if (onClose) onClose() }, 500)
  }

  const handleSendToAgent = () => {
    if (onOpenAgent && transcript) {
      onOpenAgent(transcript)
      if (onClose) onClose()
    }
  }

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stream?.getTracks().forEach(t => t.stop())
        mediaRecorder.stop()
      }
    }
  }, [mediaRecorder])

  if (status === 'idle') {
    return (
      <div className="voice-overlay-trigger">
        <button className="voice-overlay-start" onClick={startRecording}
          title={mode === 'dictation' ? 'Start Dictation' : mode === 'ai_mode' ? 'Start AI Mode' : 'Start Agent Command'}>
          🎤
        </button>
      </div>
    )
  }

  const modeLabel = mode === 'dictation' ? 'Dictation' : mode === 'ai_mode' ? 'AI Mode' : 'Agent Command'

  return (
    <div className="voice-overlay">
      <div className="voice-overlay-card">
        <div className="voice-overlay-header">
          <div className="voice-overlay-mode">{modeLabel}</div>
          <button className="voice-overlay-close" onClick={handleCancel}>✕</button>
        </div>

        <div className="voice-overlay-status">
          {status === 'recording' && (
            <div className="voice-overlay-recording">
              <span className="voice-overlay-dot" />
              <span className="voice-overlay-recording-text">Recording {formatTime(timer)}</span>
              <button className="voice-overlay-stop-btn" onClick={stopRecording}>Stop</button>
            </div>
          )}
          {status === 'transcribing' && (
            <div className="voice-overlay-transcribing">
              <span className="voice-overlay-spinner" />
              Transcribing...
            </div>
          )}
          {status === 'ready_to_paste' && (
            <div className="voice-overlay-ready">
              <div className="voice-overlay-transcript">
                <label>Transcript</label>
                <p>{transcript}</p>
              </div>
              {aiOutput && (
                <div className="voice-overlay-ai-output">
                  <label>Polished</label>
                  <p>{aiOutput}</p>
                </div>
              )}
              <div className="voice-overlay-actions">
                <button className="btn btn--primary" onClick={handlePaste}>Paste</button>
                {mode === 'agent_command' && (
                  <button className="btn btn--outline" onClick={handleSendToAgent}>Send to Agent</button>
                )}
                <button className="btn btn--ghost" onClick={handleCancel}>Cancel</button>
              </div>
            </div>
          )}
          {status === 'pasted' && <div className="voice-overlay-success">✓ Pasted at cursor</div>}
          {status === 'cancelled' && <div className="voice-overlay-cancelled">Cancelled</div>}
          {status === 'failed' && (
            <div className="voice-overlay-error">
              <p>{error || 'Transcription failed'}</p>
              <button className="btn btn--ghost" onClick={handleCancel}>Close</button>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .voice-overlay {
          position: fixed; top: 0; left: 0; right: 0; bottom: 0;
          z-index: 9999; display: flex; align-items: center; justify-content: center;
          background: rgba(0,0,0,0.4);
        }
        .voice-overlay-card {
          background: #fff; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
          width: 420px; max-width: 90vw; overflow: hidden;
        }
        .voice-overlay-header {
          display: flex; justify-content: space-between; align-items: center;
          padding: 16px 20px; border-bottom: 1px solid #e5e7eb;
        }
        .voice-overlay-mode {
          font-size: 14px; font-weight: 600; color: #374151;
        }
        .voice-overlay-close {
          background: none; border: none; font-size: 18px; color: #9ca3af;
          cursor: pointer; padding: 4px;
        }
        .voice-overlay-close:hover { color: #374151; }
        .voice-overlay-status { padding: 20px; min-height: 80px; }
        .voice-overlay-recording {
          display: flex; align-items: center; gap: 12px; padding: 12px 0;
        }
        .voice-overlay-dot {
          width: 12px; height: 12px; border-radius: 50%; background: #dc2626;
          animation: voice-pulse 1s infinite;
        }
        @keyframes voice-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
        .voice-overlay-recording-text { font-size: 16px; color: #dc2626; font-weight: 500; flex: 1; }
        .voice-overlay-stop-btn {
          padding: 6px 16px; border-radius: 6px; border: 1px solid #dc2626;
          background: #fff; color: #dc2626; font-size: 13px; font-weight: 500;
          cursor: pointer;
        }
        .voice-overlay-stop-btn:hover { background: #fef2f2; }
        .voice-overlay-transcribing {
          display: flex; align-items: center; gap: 8px; font-size: 15px; color: #6b7280;
        }
        .voice-overlay-spinner {
          width: 18px; height: 18px; border: 2px solid #e5e7eb; border-top-color: #6366f1;
          border-radius: 50%; animation: voice-spin 0.8s linear infinite;
        }
        @keyframes voice-spin { to { transform: rotate(360deg); } }
        .voice-overlay-transcript { margin-bottom: 12px; }
        .voice-overlay-transcript label, .voice-overlay-ai-output label {
          font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;
          color: #9ca3af; font-weight: 600;
        }
        .voice-overlay-transcript p, .voice-overlay-ai-output p {
          margin: 4px 0 0; font-size: 14px; color: #374151;
          padding: 8px 12px; background: #f9fafb; border-radius: 6px;
        }
        .voice-overlay-ai-output { margin-bottom: 12px; }
        .voice-overlay-ai-output p { background: #f0fdf4; color: #166534; }
        .voice-overlay-actions { display: flex; gap: 8px; margin-top: 16px; }
        .voice-overlay-success { text-align: center; padding: 24px; font-size: 18px; color: #16a34a; font-weight: 600; }
        .voice-overlay-cancelled { text-align: center; padding: 24px; color: #6b7280; }
        .voice-overlay-error { text-align: center; padding: 12px; color: #dc2626; }
        .voice-overlay-trigger { display: inline; }
        .voice-overlay-start {
          width: 40px; height: 40px; border-radius: 50%; border: none;
          background: #6366f1; color: #fff; font-size: 18px; cursor: pointer;
        }
        .voice-overlay-start:hover { background: #4f46e5; }
      `}</style>
    </div>
  )
}