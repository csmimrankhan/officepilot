import { useState, useRef, useEffect } from 'react'

export default function WorkflowRecordingOverlay({ sessionId, title, startedAt, eventCount, onStop, onCancel }) {
  const [elapsed, setElapsed] = useState('0:00')
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!startedAt) return
    const start = new Date(startedAt).getTime()
    intervalRef.current = setInterval(() => {
      const diff = Math.floor((Date.now() - start) / 1000)
      const m = Math.floor(diff / 60)
      const s = diff % 60
      setElapsed(`${m}:${String(s).padStart(2, '0')}`)
    }, 1000)
    return () => clearInterval(intervalRef.current)
  }, [startedAt])

  if (!sessionId) return null

  return (
    <div style={{
      position: 'fixed', top: 16, right: 16, zIndex: 9999,
      background: '#fff', border: '2px solid #ef4444', borderRadius: 12,
      padding: '16px 20px', minWidth: 280, boxShadow: '0 4px 24px rgba(0,0,0,0.15)',
      fontFamily: 'system-ui, sans-serif',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <span style={{
          width: 14, height: 14, borderRadius: '50%', background: '#ef4444',
          animation: 'pulse 1.5s infinite',
        }} />
        <strong style={{ fontSize: 15 }}>Recording Workflow</strong>
        <span style={{ marginLeft: 'auto', fontVariantNumeric: 'tabular-nums', color: '#666' }}>
          {elapsed}
        </span>
      </div>
      {title && <div style={{ fontSize: 13, color: '#555', marginBottom: 8 }}>{title}</div>}
      <div style={{ fontSize: 13, color: '#888', marginBottom: 12 }}>
        Events captured: <strong>{eventCount || 0}</strong>
      </div>
      <div style={{ fontSize: 12, color: '#999', marginBottom: 12, fontStyle: 'italic' }}>
        Recording is always visible. No passwords, OTPs, or secrets are recorded.
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={onStop}
          style={{
            flex: 1, padding: '8px 16px', background: '#ef4444', color: '#fff',
            border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600, fontSize: 13,
          }}
        >
          Stop Recording
        </button>
        <button
          onClick={onCancel}
          style={{
            padding: '8px 16px', background: '#f3f4f6', color: '#666',
            border: '1px solid #d1d5db', borderRadius: 6, cursor: 'pointer', fontSize: 13,
          }}
        >
          Cancel
        </button>
      </div>
      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
      `}</style>
    </div>
  )
}
