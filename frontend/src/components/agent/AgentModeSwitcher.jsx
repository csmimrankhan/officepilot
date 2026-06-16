const MODES = [
  { id: 'plan', label: 'Plan', icon: '📋', description: 'Read-only planning' },
  { id: 'work', label: 'Work', icon: '⚡', description: 'Execute approved steps' },
  { id: 'record', label: 'Record', icon: '⏺', description: 'Record a workflow' },
  { id: 'replay', label: 'Replay', icon: '🔄', description: 'Repeat a saved workflow' },
]

export default function AgentModeSwitcher({ currentMode, onModeChange }) {
  return (
    <div style={{ display: 'flex', gap: '0', padding: '0 4px', marginBottom: '4px' }}>
      <style>{`
        .agent-mode-btn {
          flex: 1; padding: 6px 2px; border: none; background: transparent;
          font-size: 11px; font-weight: 500; cursor: pointer; color: #6c7086;
          border-bottom: 2px solid transparent; transition: all 0.15s;
          text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .agent-mode-btn:hover { color: #cdd6f4; }
        .agent-mode-btn.active { color: #cdd6f4; }
        .agent-mode-btn.active.plan { border-bottom-color: #89b4fa; color: #89b4fa; }
        .agent-mode-btn.active.work { border-bottom-color: #a6e3a1; color: #a6e3a1; }
        .agent-mode-btn.active.record { border-bottom-color: #f38ba8; color: #f38ba8; }
        .agent-mode-btn.active.replay { border-bottom-color: #f9e2af; color: #f9e2af; }
      `}</style>
      {MODES.map((m) => (
        <button
          key={m.id}
          className={`agent-mode-btn ${currentMode === m.id ? `active ${m.id}` : ''}`}
          onClick={() => onModeChange(m.id)}
          title={m.description}
        >
          <span style={{ fontSize: '14px', display: 'block' }}>{m.icon}</span>
          {m.label}
        </button>
      ))}
    </div>
  )
}
