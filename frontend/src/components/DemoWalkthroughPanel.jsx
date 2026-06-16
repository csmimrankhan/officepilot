import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function DemoWalkthroughPanel() {
  const [state, setState] = useState(null)
  const [loading, setLoading] = useState(true)

  function load() {
    api.demoWalkthroughStatus().then(s => setState(s)).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return null
  if (!state || state.dismissed) return null

  const { steps, status, current_step, completed_steps, progress_pct } = state

  function handleStart() {
    api.startDemoWalkthrough().then(s => setState(s)).catch(() => {})
  }

  function handleComplete(step) {
    api.completeDemoWalkthroughStep(step).then(s => setState(s)).catch(() => {})
  }

  function handleSkip(step) {
    api.skipDemoWalkthroughStep(step).then(s => setState(s)).catch(() => {})
  }

  function handleReset() {
    if (!confirm('Reset the demo walkthrough?')) return
    api.resetDemoWalkthrough().then(s => setState(s)).catch(() => {})
  }

  function handleDismiss() {
    api.dismissDemoWalkthrough().then(() => setState(s => ({ ...s, dismissed: true }))).catch(() => {})
  }

  const isActive = status === 'in_progress'
  const isCompleted = status === 'completed'
  const currentStepLabel = isActive && steps[current_step] ? steps[current_step].label : ''

  return (
    <div className="card" style={{ marginBottom: '16px', border: '2px solid #ff9800' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>Demo Walkthrough</h3>
        {isActive && <button className="btn btn--small btn--secondary" onClick={handleDismiss}>Dismiss</button>}
      </div>
      {!isActive && !isCompleted && (
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <p>Follow a guided tour of OfficePilot's features.</p>
          <button className="btn" onClick={handleStart}>Start Demo</button>
        </div>
      )}
      {isActive && (
        <>
          <p>Progress: {progress_pct}%</p>
          <div style={{ height: '8px', background: '#e0e0e0', borderRadius: '4px', marginBottom: '12px' }}>
            <div style={{ height: '100%', width: `${progress_pct}%`, background: '#ff9800', borderRadius: '4px', transition: 'width 0.3s' }} />
          </div>
          <p style={{ fontSize: '0.85rem', color: '#666' }}>Current: <strong>{currentStepLabel}</strong></p>
          <div style={{ maxHeight: '250px', overflowY: 'auto' }}>
            {steps.map((item, i) => {
              const done = completed_steps.includes(item.step)
              const isCurrent = i === current_step && !done
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', opacity: done ? 0.6 : 1, background: isCurrent ? '#fff3e0' : 'transparent' }}>
                  <span style={{ color: done ? '#4caf50' : '#9e9e9e', fontSize: '1.2rem' }}>{done ? '\u2713' : isCurrent ? '\u25B6' : '\u25CB'}</span>
                  <span style={{ flex: 1, fontSize: '0.85rem' }}>{item.label}</span>
                  {isCurrent && <button className="btn btn--small" onClick={() => handleComplete(item.step)}>Done</button>}
                  {isCurrent && <button className="btn btn--small btn--secondary" onClick={() => handleSkip(item.step)}>Skip</button>}
                  {done && <span style={{ fontSize: '0.75rem', color: '#4caf50' }}>Done</span>}
                </div>
              )
            })}
          </div>
        </>
      )}
      {isCompleted && (
        <div style={{ textAlign: 'center', padding: '16px 0' }}>
          <p style={{ color: '#4caf50' }}>Demo complete! All 15 steps finished.</p>
          <button className="btn btn--secondary" onClick={handleReset}>Restart Demo</button>
        </div>
      )}
    </div>
  )
}
