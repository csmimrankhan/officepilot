import { useState, useEffect, useRef } from 'react'
import { api } from '../../api.js'
import { AlertTriangle, Loader, CheckCircle, XCircle, Clock } from 'lucide-react'

const ACTIVE_STATUSES = new Set(['queued', 'running'])
const NEEDS_ATTENTION_STATUSES = new Set(['paused_for_input'])

function sendNotification(title, body) {
  if (window.__TAURI__) {
    import('@tauri-apps/plugin-notification').then(({ sendNotification, isPermissionGranted, requestPermission }) => {
      isPermissionGranted().then((granted) => {
        if (!granted) {
          requestPermission().then(() => {
            sendNotification({ title, body })
          })
        } else {
          sendNotification({ title, body })
        }
      })
    }).catch(() => {
      // fallback - plugin not available
    })
  } else {
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, { body })
    } else if ('Notification' in window && Notification.permission !== 'denied') {
      Notification.requestPermission().then(perm => {
        if (perm === 'granted') new Notification(title, { body })
      })
    }
  }
}

function formatMoney(val) {
  if (val == null) return ''
  const n = Number(val)
  if (Number.isNaN(n)) return String(val)
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }).format(n)
  } catch { return `$${n.toFixed(2)}` }
}

export default function BackgroundTaskWidget() {
  const [tasks, setTasks] = useState([])
  const [lastSeenStatuses, setLastSeenStatuses] = useState({})
  const prevTasksRef = useRef({})
  const [open, setOpen] = useState(false)
  const intervalRef = useRef(null)
  const dropdownRef = useRef(null)

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await api.getBackgroundTasks()
        const current = Array.isArray(data) ? data : data?.tasks || []
        setTasks(current)

        const statusMap = {}
        for (const t of current) {
          statusMap[t.id] = t.status
        }

        for (const t of current) {
          const prev = prevTasksRef.current[t.id]
          if (prev && prev !== t.status) {
            if ((prev === 'running' || prev === 'queued') && (t.status === 'completed' || t.status === 'failed')) {
              const resultJson = t.result_summary_json
              const summary = typeof resultJson === 'string' ? JSON.parse(resultJson) : resultJson
              const count = summary?.invoice_count || summary?.completed_steps || summary?.total_steps || ''
              const largest = summary?.largest_amount ? formatMoney(summary.largest_amount) : ''
              const isDone = t.status === 'completed'
              const title = isDone ? 'OfficePilot Task Complete' : 'OfficePilot Task Failed'
              let body = t.command?.length > 60 ? t.command.slice(0, 60) + '...' : (t.command || 'Task complete')
              if (count && isDone) {
                body = `Processed ${count} invoice${count > 1 ? 's' : ''}.${largest ? ` Biggest: ${largest}.` : ''} Click to view.`
              }
              if (!isDone && t.error_message) {
                body = t.error_message.length > 80 ? t.error_message.slice(0, 80) + '...' : t.error_message
              }
              sendNotification(title, body)
            }
          }
        }

        prevTasksRef.current = statusMap
        setLastSeenStatuses(statusMap)
      } catch { /* ignore */ }
    }
    poll()
    intervalRef.current = setInterval(poll, 3000)
    return () => clearInterval(intervalRef.current)
  }, [])

  const [answerInputs, setAnswerInputs] = useState({})
  const [answeringIds, setAnsweringIds] = useState(new Set())

  const active = tasks.filter(t => ACTIVE_STATUSES.has(t.status))
  const needsAttention = tasks.filter(t => NEEDS_ATTENTION_STATUSES.has(t.status))
  if (active.length === 0 && tasks.length === 0 && needsAttention.length === 0) return null

  const handleAnswer = async (taskId) => {
    const answer = answerInputs[taskId]
    if (!answer || !answer.trim()) return
    setAnsweringIds(prev => new Set([...prev, taskId]))
    try {
      await api.answerBackgroundTask(taskId, answer.trim())
      setAnswerInputs(prev => ({ ...prev, [taskId]: '' }))
    } catch { /* ignore */ }
    setAnsweringIds(prev => {
      const next = new Set(prev)
      next.delete(taskId)
      return next
    })
  }

  const needsAttentionCount = needsAttention.length

  return (
    <div className="bg-task-widget" ref={dropdownRef} style={{ position: 'relative' }}>
      <button
        className="bg-task-trigger"
        onClick={() => setOpen(!open)}
        title={`${needsAttentionCount > 0 ? `${needsAttentionCount} task(s) need attention` : active.length > 0 ? `${active.length} background task${active.length !== 1 ? 's' : ''} running` : 'Background tasks'}`}
        aria-label="Background tasks"
        type="button"
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 10px', borderRadius: 8,
          border: '1px solid var(--border, #e2e8f0)',
          background: needsAttentionCount > 0 ? '#fff7ed' : active.length > 0 ? '#fef3c7' : 'transparent',
          cursor: 'pointer', fontSize: 13, position: 'relative',
        }}
      >
        {needsAttentionCount > 0 ? (
          <>
            <AlertTriangle size={16} color="#ea580c" />
            <span style={{ fontWeight: 600, color: '#9a3412' }}>{needsAttentionCount}</span>
          </>
        ) : active.length > 0 ? (
          <>
            <Loader size={16} color="#d97706" className="bg-task-pulse" />
            <span style={{ fontWeight: 600, color: '#92400e' }}>{active.length}</span>
          </>
        ) : (
          <Clock size={16} color="#94a3b8" />
        )}
      </button>

      {open && (
        <div
          className="bg-task-dropdown"
          style={{
            position: 'absolute', top: '100%', right: 0, marginTop: 4,
            width: 360, maxHeight: 400, overflowY: 'auto',
            background: '#fff', border: '1px solid var(--border, #e2e8f0)',
            borderRadius: 10, boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            zIndex: 100, padding: 8,
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', padding: '4px 8px 8px', letterSpacing: '0.06em' }}>
            Background Tasks ({tasks.length})
          </div>
          {tasks.length === 0 && (
            <div style={{ fontSize: 13, color: '#94a3b8', padding: '8px' }}>No background tasks</div>
          )}
          {tasks.map(task => {
            const isPaused = task.status === 'paused_for_input'
            return (
            <div key={task.id} className="bg-task-item" style={{
              padding: '8px', borderRadius: 6, marginBottom: 4,
              background: isPaused ? '#fff7ed' : task.status === 'running' ? '#fffbeb' : task.status === 'completed' ? '#f0fdf4' : task.status === 'failed' ? '#fef2f2' : '#f8fafc',
              border: '1px solid',
              borderColor: isPaused ? '#fdba74' : task.status === 'running' ? '#fde68a' : task.status === 'completed' ? '#bbf7d0' : task.status === 'failed' ? '#fecaca' : 'var(--border, #e2e8f0)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#1e293b' }}>
                  {task.command?.length > 40 ? task.command.slice(0, 40) + '...' : task.command || `Task #${task.id}`}
                </span>
                <span className={`badge badge--${
                  task.status === 'completed' ? 'success' : task.status === 'failed' ? 'danger' : task.status === 'cancelled' ? 'secondary' : task.status === 'paused_for_input' ? 'warning' : 'info'
                }`} style={{ fontSize: 10, textTransform: 'capitalize' }}>
                  {task.status === 'paused_for_input' ? 'Needs Attention' : task.status}
                </span>
              </div>
              {task.current_step_description && (
                <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>
                  {task.current_step_description}
                </div>
              )}
              {isPaused && task.clarification_question && (
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 12, color: '#9a3412', background: '#fff7ed', padding: '6px 8px', borderRadius: 6, marginBottom: 6, border: '1px solid #fdba74' }}>
                    <AlertTriangle size={14} style={{ display: 'inline', marginRight: 4, verticalAlign: 'middle' }} color="#ea580c" />
                    {task.clarification_question}
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <input
                      type="text"
                      value={answerInputs[task.id] || ''}
                      onChange={e => setAnswerInputs(prev => ({ ...prev, [task.id]: e.target.value }))}
                      placeholder="Type your answer..."
                      style={{
                        flex: 1, padding: '4px 8px', borderRadius: 6, border: '1px solid #d1d5db',
                        fontSize: 12, outline: 'none',
                      }}
                      onKeyDown={e => { if (e.key === 'Enter') handleAnswer(task.id) }}
                    />
                    <button
                      className="btn btn--sm btn--primary"
                      style={{ fontSize: 11, padding: '4px 10px', whiteSpace: 'nowrap' }}
                      onClick={() => handleAnswer(task.id)}
                      disabled={answeringIds.has(task.id) || !answerInputs[task.id]?.trim()}
                      type="button"
                    >
                      {answeringIds.has(task.id) ? 'Sending...' : 'Send'}
                    </button>
                  </div>
                </div>
              )}
              {ACTIVE_STATUSES.has(task.status) && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div className="bg-task-progress-bar" style={{
                    flex: 1, height: 4, borderRadius: 2, background: '#e2e8f0', overflow: 'hidden',
                  }}>
                    <div style={{
                      width: `${task.progress_percent || 0}%`, height: '100%',
                      background: '#3b82f6', borderRadius: 2,
                      transition: 'width 0.5s ease',
                    }} />
                  </div>
                  <span style={{ fontSize: 10, color: '#94a3b8', minWidth: 28, textAlign: 'right' }}>
                    {task.progress_percent || 0}%
                  </span>
                </div>
              )}
              {task.status === 'failed' && task.error_message && (
                <div style={{ fontSize: 11, color: '#dc2626', marginTop: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <XCircle size={12} />
                  {task.error_message.length > 80 ? task.error_message.slice(0, 80) + '...' : task.error_message}
                </div>
              )}
              {task.status === 'completed' && (
                <div style={{ fontSize: 11, color: '#16a34a', marginTop: 4, display: 'flex', alignItems: 'center', gap: 4 }}>
                  <CheckCircle size={12} />
                  Completed
                </div>
              )}
              {(ACTIVE_STATUSES.has(task.status) || isPaused) && (
                <button
                  className="btn btn--sm btn--danger"
                  style={{ marginTop: 6, fontSize: 11, padding: '2px 8px' }}
                  onClick={async (e) => { e.stopPropagation(); try { await api.cancelBackgroundTask(task.id) } catch {} }}
                  type="button"
                >
                  Cancel
                </button>
              )}
            </div>
            )
          })}
        </div>
      )}

      <style>{`
        @keyframes bg-task-spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .bg-task-pulse {
          animation: bg-task-spin 1.5s linear infinite;
        }
      `}</style>
    </div>
  )
}
