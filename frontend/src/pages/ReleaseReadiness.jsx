import { useState, useEffect } from 'react'
import * as api from '../api.js'

const STEPS = [
  { id: 'invoice_upload', label: 'Invoice upload and parsing works end-to-end' },
  { id: 'review_queue', label: 'Review queue displays pending invoices correctly' },
  { id: 'approve_reject', label: 'Invoice approval and rejection flow is functional' },
  { id: 'audit_log', label: 'Audit log captures all invoice actions' },
  { id: 'excel_export', label: 'Excel export produces valid spreadsheet' },
  { id: 'gmail_sync', label: 'Gmail integration syncs and imports invoices' },
  { id: 'folder_rules', label: 'Auto-organize folder rules apply correctly' },
  { id: 'workflow_orchestration', label: 'LangGraph workflows start and complete' },
  { id: 'browser_automation', label: 'Browser automation preview and execute work' },
  { id: 'accounting_sync', label: 'QuickBooks/Xero accounting sync is configured' },
  { id: 'screen_control', label: 'Screen control reads context and executes actions' },
  { id: 'version_history', label: 'Version history captures and restores data' },
  { id: 'backup_restore', label: 'Local backup and restore cycle is verified' },
  { id: 'auth_sessions', label: 'Authentication, login, and role permissions work' },
]

export default function ReleaseReadiness() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  function load() {
    setLoading(true)
    setError(false)
    api.getReleaseChecklist()
      .then(res => setData(res))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const completed = data ? STEPS.filter(s => (data.completed || []).includes(s.id)).length : 0
  const total = STEPS.length
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0

  async function handleComplete(stepId) {
    try {
      const res = await api.completeReleaseStep({ step_id: stepId })
      setData(res)
    } catch {
      setError(true)
    }
  }

  async function handleReset() {
    if (!confirm('Reset the entire release readiness checklist?')) return
    try {
      const res = await api.resetReleaseChecklist()
      setData(res)
    } catch {
      setError(true)
    }
  }

  if (loading) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <p>Loading release checklist...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <p style={{ color: '#c62828', marginBottom: '12px' }}>Could not load checklist</p>
          <button className="btn btn--secondary" onClick={load}>Retry</button>
        </div>
      </div>
    )
  }

  return (
    <>
      <style>{`
        .release-container { max-width: 800px; margin: 0 auto; }
        .release-header { display: flex; align-items: center; gap: 16px; margin-bottom: 4px; }
        .release-badge { background: #1565c0; color: #fff; padding: 4px 14px; border-radius: 12px; font-size: 0.85rem; font-weight: 600; white-space: nowrap; }
        .release-bar-track { height: 10px; background: #e0e0e0; border-radius: 5px; margin-bottom: 24px; overflow: hidden; }
        .release-bar-fill { height: 100%; border-radius: 5px; transition: width 0.4s ease; }
        .release-step { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 8px; background: #fff; }
        .release-step.completed { background: #f1f8e9; border-color: #aed581; }
        .release-checkbox { width: 18px; height: 18px; cursor: default; accent-color: #2e7d32; flex-shrink: 0; }
        .release-step-label { flex: 1; font-size: 0.95rem; color: #333; }
        .release-step-label.done { text-decoration: line-through; color: #558b2f; }
        .release-check-badge { background: #2e7d32; color: #fff; padding: 2px 10px; border-radius: 4px; font-size: 0.8rem; font-weight: 600; white-space: nowrap; }
        .release-btn-complete { background: #1565c0; color: #fff; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 0.85rem; font-weight: 500; white-space: nowrap; transition: background 0.2s; }
        .release-btn-complete:hover { background: #0d47a1; }
        .release-footer { display: flex; gap: 12px; margin-top: 24px; flex-wrap: wrap; }
      `}</style>

      <div className="card release-container">
        <div className="release-header">
          <h2 style={{ margin: 0 }}>Release Readiness Checklist</h2>
          <span className="release-badge">{completed}/{total}</span>
        </div>
        <p style={{ color: '#555', marginTop: 4, marginBottom: 12 }}>
          Overall progress: {pct}%
        </p>

        <div className="release-bar-track">
          <div
            className="release-bar-fill"
            style={{
              width: `${pct}%`,
              background: pct === 100 ? '#2e7d32' : pct >= 50 ? '#1565c0' : '#ff9800',
            }}
          />
        </div>

        {STEPS.map(s => {
          const isDone = (data.completed || []).includes(s.id)
          return (
            <div key={s.id} className={`release-step${isDone ? ' completed' : ''}`}>
              <input
                type="checkbox"
                className="release-checkbox"
                checked={isDone}
                readOnly
              />
              <span className={`release-step-label${isDone ? ' done' : ''}`}>
                {s.label}
              </span>
              {isDone ? (
                <span className="release-check-badge">{'\u2713'}</span>
              ) : (
                <button
                  className="release-btn-complete"
                  onClick={() => handleComplete(s.id)}
                >
                  Mark Complete
                </button>
              )}
            </div>
          )
        })}

        <div className="release-footer">
          <button className="btn btn--secondary" onClick={handleReset}>
            Reset All
          </button>
          <button className="btn btn--secondary" onClick={load}>
            Refresh
          </button>
        </div>
      </div>
    </>
  )
}
