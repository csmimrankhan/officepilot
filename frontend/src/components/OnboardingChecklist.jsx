import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function OnboardingChecklist() {
  const [state, setState] = useState(null)
  const [loading, setLoading] = useState(true)

  function load() {
    api.onboardingStatus().then(s => setState(s)).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return null
  if (!state || state.dismissed) return null

  const { checklist, completed_steps, progress_pct } = state

  function handleComplete(step) {
    api.completeOnboardingStep(step).then(s => setState(s)).catch(() => {})
  }

  function handleDismiss() {
    api.dismissOnboarding().then(() => setState(s => ({ ...s, dismissed: true }))).catch(() => {})
  }

  return (
    <div className="card" style={{ marginBottom: '16px', border: '2px solid #1976d2' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>Setup Checklist</h3>
        <button className="btn btn--small btn--secondary" onClick={handleDismiss}>Dismiss</button>
      </div>
      <p>Progress: {progress_pct}%</p>
      <div style={{ height: '8px', background: '#e0e0e0', borderRadius: '4px', marginBottom: '12px' }}>
        <div style={{ height: '100%', width: `${progress_pct}%`, background: '#1976d2', borderRadius: '4px', transition: 'width 0.3s' }} />
      </div>
      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
        {checklist.map((item, i) => {
          const done = completed_steps.includes(item.step)
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', opacity: done ? 0.6 : 1 }}>
              <span style={{ color: done ? '#4caf50' : '#9e9e9e', fontSize: '1.2rem' }}>{done ? '\u2713' : '\u25CB'}</span>
              <span style={{ flex: 1 }}>{item.label}</span>
              {!done && <button className="btn btn--small" onClick={() => handleComplete(item.step)}>Complete</button>}
              {done && <span style={{ fontSize: '0.8rem', color: '#4caf50' }}>Done</span>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
