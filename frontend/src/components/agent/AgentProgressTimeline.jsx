export default function AgentProgressTimeline({ run, onDryRun, onStartLive, onEmergencyStop, loading }) {
  if (!run) return null

  const steps = run.steps || []
  const isDryRun = run.mode === 'dry_run'
  const isRunning = run.status === 'running' || run.status === 'approved' || run.status === 'pending'
  const isCompleted = run.status === 'completed'
  const isStopped = run.status === 'stopped' || run.status === 'cancelled'

  const stepStatusIcon = (status) => {
    switch (status) {
      case 'completed': return '✓'
      case 'running': return '⟳'
      case 'failed': return '✗'
      case 'blocked': return '⛔'
      case 'cancelled': return '—'
      default: return '○'
    }
  }

  const stepStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#a6e3a1'
      case 'running': return '#89b4fa'
      case 'failed': return '#f38ba8'
      case 'blocked': return '#f38ba8'
      case 'cancelled': return '#6c7086'
      default: return '#45475a'
    }
  }

  return (
    <div className="card" style={{ padding: '12px', background: '#181825', borderRadius: '12px' }}>
      <style>{`
        .agent-timeline-title { font-size: 13px; font-weight: 600; margin: 0 0 8px; display: flex; align-items: center; gap: 8px; }
        .agent-timeline-title.running { color: #89b4fa; }
        .agent-timeline-title.dry-run { color: #f9e2af; }
        .agent-timeline-title.completed { color: #a6e3a1; }
        .agent-timeline-title.stopped { color: #f38ba8; }
        .agent-timeline-step { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 12px; color: #bac2de; }
        .agent-timeline-icon { width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; flex-shrink: 0; }
        .agent-timeline-actions { display: flex; gap: 6px; margin-top: 8px; flex-wrap: wrap; }
        .agent-timeline-actions button { padding: 5px 10px; border: none; border-radius: 5px; font-size: 11px; font-weight: 600; cursor: pointer; }
        .agent-timeline-actions button:disabled { opacity: 0.5; cursor: default; }
      `}</style>

      <div className={`agent-timeline-title ${isStopped ? 'stopped' : isCompleted ? 'completed' : isDryRun ? 'dry-run' : 'running'}`}>
        <span>{isDryRun ? '🔄' : isCompleted ? '✅' : isStopped ? '⛔' : '⚡'}</span>
        Run: {run.mode?.toUpperCase() || 'DRY_RUN'} · {run.status?.toUpperCase() || 'PENDING'}
      </div>

      <div style={{ fontSize: '11px', color: '#6c7086', marginBottom: '8px' }}>
        {steps.length} step{steps.length !== 1 ? 's' : ''}
        {run.summary && (
          <span style={{ display: 'block', marginTop: '4px', color: '#a6adc8' }}>
            {run.summary.summary_english || ''}
            {run.summary.summary_roman_urdu && (
              <span style={{ color: '#89b4fa', marginLeft: '4px' }}>({run.summary.summary_roman_urdu})</span>
            )}
          </span>
        )}
      </div>

      {steps.length > 0 && (
        <div style={{ marginBottom: '8px' }}>
          {steps.map((step) => (
            <div key={step.step_log_id || step.id || step.step_order} className="agent-timeline-step">
              <span className="agent-timeline-icon" style={{ background: stepStatusColor(step.status) + '33', color: stepStatusColor(step.status) }}>
                {stepStatusIcon(step.status)}
              </span>
              <span style={{ flex: 1 }}>{step.step_type} {step.step_order ? `#${step.step_order}` : ''}</span>
              <span style={{ fontSize: '10px', color: stepStatusColor(step.status) }}>{step.status}</span>
            </div>
          ))}
        </div>
      )}

      <div className="agent-timeline-actions">
        {isRunning && isDryRun && (
          <button style={{ background: '#45475a', color: '#89b4fa' }} onClick={() => onDryRun(run.run_id)} disabled={loading}>
            {loading ? '...' : 'Run All Steps (Dry-Run)'}
          </button>
        )}
        {isRunning && !isDryRun && (
          <button style={{ background: '#a6e3a1', color: '#1e1e2e' }} onClick={() => onStartLive(run.run_id)} disabled={loading}>
            {loading ? '...' : 'Continue Live'}
          </button>
        )}
        {isCompleted && isDryRun && (
          <button style={{ background: '#a6e3a1', color: '#1e1e2e' }} onClick={() => onStartLive(run.run_id)} disabled={loading}>
            {loading ? '...' : 'Execute for Real'}
          </button>
        )}
        <button style={{ background: '#dc2626', color: '#fff' }} onClick={onEmergencyStop} disabled={loading}>
          Emergency Stop
        </button>
      </div>
    </div>
  )
}
