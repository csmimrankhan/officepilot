import { useState, useEffect } from 'react'
import { api } from '../../api.js'

export default function TopBar({ user, onLogout, onFeedback, onBugReport, onMenuToggle }) {
  const [agentOnline, setAgentOnline] = useState(null)
  const [killSwitch, setKillSwitch] = useState(null)
  const [showProfile, setShowProfile] = useState(false)

  useEffect(() => {
    const check = async () => {
      try {
        const status = await api.getLocalStatus()
        setAgentOnline(status.state === 'online')
      } catch { setAgentOnline(false) }
      try {
        const pol = await api.getSafetyPolicies()
        setKillSwitch(pol.kill_switch_active)
      } catch {}
    }
    check()
    const interval = setInterval(check, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button className="topbar-menu-btn" onClick={onMenuToggle} aria-label="Open navigation" type="button">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path d="M3 5h14v2H3V5zm0 4h14v2H3V9zm0 4h14v2H3v-2z" />
          </svg>
        </button>
        <span className="topbar-title">OfficePilot AI</span>
      </div>
      <div className="topbar-center">
        <span className={`agent-dot ${agentOnline === true ? 'online' : agentOnline === false ? 'offline' : 'checking'}`} aria-hidden="true" />
        <span className="agent-label">
          {agentOnline === true ? 'Ready' : agentOnline === false ? 'Offline' : '...'}
        </span>
        {killSwitch && (
          <span className="kill-switch-badge">Kill Switch Active</span>
        )}
      </div>
      <div className="topbar-right">
        <button className="btn btn--danger btn--sm topbar-emergency" onClick={async () => {
          try { await api.setKillSwitch?.({ active: true }) } catch {}
        }} type="button">Emergency Stop</button>
        <div className="topbar-user" onClick={() => setShowProfile(!showProfile)} role="button" tabIndex={0} onKeyDown={e => { if (e.key === 'Enter') setShowProfile(!showProfile) }} aria-label="User menu" aria-expanded={showProfile}>
          <div className="topbar-avatar" aria-hidden="true">
            {user?.email?.[0]?.toUpperCase() || 'U'}
          </div>
          <span className="topbar-email">{user?.email}</span>
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" className="topbar-chevron" aria-hidden="true">
            <path d="M2 3.5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" fill="none" />
          </svg>
        </div>
        {showProfile && (
          <div className="topbar-dropdown" role="menu">
            <div className="topbar-dropdown-header">
              <div className="topbar-dropdown-email">{user?.email}</div>
              <div className="topbar-dropdown-role">{user?.role}</div>
            </div>
            <div className="topbar-dropdown-body">
              <button className="topbar-dropdown-item" onClick={() => { setShowProfile(false); window.location.href = '/app/settings' }} role="menuitem">Settings</button>
              <button className="topbar-dropdown-item" onClick={() => { setShowProfile(false); onFeedback() }} role="menuitem">Feedback</button>
              <button className="topbar-dropdown-item" onClick={() => { setShowProfile(false); onBugReport() }} role="menuitem">Report Bug</button>
              <button className="topbar-dropdown-item topbar-dropdown-item--danger" onClick={onLogout} role="menuitem">Logout</button>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}