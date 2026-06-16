import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import LoadingState from '../components/ui/LoadingState.jsx'

const QUICK_ACTIONS = [
  { label: 'Open Accountant Agent', icon: '🎙️', action: 'agent' },
  { label: 'Record Workflow', icon: '⏺️', action: 'record' },
  { label: 'Repeat Workflow', icon: '🔄', action: 'repeat' },
  { label: 'Emergency Stop', icon: '⛔', action: 'emergency' },
  { label: 'Workflow Memory', icon: '🧠', action: 'memory' },
  { label: 'Settings', icon: '⚙️', action: 'settings' },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const [status, setStatus] = useState(null)
  const [mode, setMode] = useState('plan')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [s, m] = await Promise.all([
          api.agentStatus().catch(() => ({ provider: 'unknown', status: 'disconnected' })),
          api.getAgentMode().catch(() => ({ mode: 'plan' })),
        ])
        setStatus(s)
        setMode(m.mode || 'plan')
      } catch { /* silent */ }
      setLoading(false)
    }
    load()
  }, [])

  if (loading) return <LoadingState text="Loading dashboard..." />

  return (
    <div className="dashboard">
      <style>{`
        .dashboard-tray-banner {
          text-align: center; padding: 24px 20px; background: linear-gradient(135deg, #1e1e2e 0%, #181825 100%);
          border-radius: 16px; margin-bottom: 24px;
        }
        .dashboard-tray-banner h2 { margin: 0 0 8px; font-size: 20px; font-weight: 700; color: #cdd6f4; }
        .dashboard-tray-banner p { margin: 0 0 12px; color: #a6adc8; font-size: 14px; }
        .dashboard-tray-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; background: #313244; color: #a6adc8; }
        .dashboard-tray-badge .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
        .dashboard-tray-badge .dot.green { background: #a6e3a1; }
        .dashboard-tray-badge .dot.red { background: #f38ba8; }
        .dashboard-actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
        .dashboard-action-card { padding: 20px; background: #1e1e2e; border-radius: 12px; cursor: pointer; text-align: center; transition: all 0.15s; border: 1px solid #313244; }
        .dashboard-action-card:hover { background: #313244; border-color: #45475a; transform: translateY(-1px); }
        .dashboard-action-card .icon { font-size: 28px; margin-bottom: 8px; display: block; }
        .dashboard-action-card .label { font-size: 13px; font-weight: 600; color: #cdd6f4; }
        .dashboard-action-card.emergency { border-color: #dc2626; }
        .dashboard-action-card.emergency:hover { background: #dc262622; }
        .dashboard-mode-bar { display: flex; justify-content: center; gap: 8px; margin: 16px 0; }
        .dashboard-mode-badge { padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
        .dashboard-mode-badge.plan { background: #89b4fa22; color: #89b4fa; }
        .dashboard-mode-badge.work { background: #a6e3a122; color: #a6e3a1; }
        .dashboard-mode-badge.record { background: #f38ba822; color: #f38ba8; }
        .dashboard-mode-badge.replay { background: #f9e2af22; color: #f9e2af; }
      `}</style>

      <div className="dashboard-tray-banner">
        <h2>OfficePilot is running in your taskbar.</h2>
        <p>Click the tray icon or press <strong>Alt+A</strong> to open the Accountant Agent.</p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <span className="dashboard-tray-badge">
            <span className={`dot ${status?.status === 'mock' || status?.status === 'connected' ? 'green' : 'red'}`} />
            {status?.provider || 'Unknown'}
          </span>
          <span className={`dashboard-mode-badge ${mode}`}>Mode: {mode}</span>
        </div>
      </div>

      <div className="dashboard-actions">
        {QUICK_ACTIONS.map(a => (
          <div key={a.action}
            className={`dashboard-action-card ${a.action === 'emergency' ? 'emergency' : ''}`}
            onClick={() => {
              if (a.action === 'agent') navigate('/app/agent')
              else if (a.action === 'record') navigate('/app/agent', { state: { command: 'record this workflow' } })
              else if (a.action === 'repeat') navigate('/app/agent', { state: { command: 'repeat yesterday workflow' } })
              else if (a.action === 'emergency') api.emergencyStopAgent({ reason: 'Dashboard emergency stop' }).then(() => alert('Emergency stop executed.')).catch(() => alert('Error executing stop.'))
              else if (a.action === 'memory') navigate('/app/workflow-memory')
              else if (a.action === 'settings') navigate('/app/settings')
            }}
          >
            <span className="icon">{a.icon}</span>
            <span className="label">{a.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
