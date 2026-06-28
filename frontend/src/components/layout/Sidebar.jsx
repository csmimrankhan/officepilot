import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  MessageSquare, Sparkles, History, Clock, Mic, Scale,
  Settings, Plug, ShieldCheck, Eye,
  LayoutDashboard, Users, ClipboardList, ListChecks, Activity, Brain,
  Plus, ChevronRight, ChevronDown,
} from 'lucide-react'
import NavIcon from './NavIcon.jsx'

const MAIN_ITEMS = [
  { to: '/app/agent', label: 'Agent', icon: MessageSquare },
  { to: '/app/skills', label: 'Skills', icon: Sparkles },
  { to: '/app/workflow-memory', label: 'Workflow Memory', icon: History },
  { to: '/app/version-history', label: 'Version History', icon: Clock },
]

const WORKSPACE_ITEMS = [
  { to: '/app/voice-recorder', label: 'Voice Recorder', icon: Mic },
  { to: '/app/reconciliation', label: 'Reconciliation', icon: Scale },
  { to: '/app/settings', label: 'Settings', icon: Settings },
  { to: '/app/api-setup', label: 'API Setup', icon: Plug },
  { to: '/app/safety', label: 'Safety', icon: ShieldCheck },
  { to: '/watchers', label: 'Watchers', icon: Eye },
]

const ADMIN_ITEMS = [
  { to: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/audit-logs', label: 'Audit Logs', icon: ClipboardList },
  { to: '/admin/waitlist', label: 'Waitlist', icon: ListChecks },
  { to: '/admin/system-health', label: 'System Health', icon: Activity },
  { to: '/admin/ai-status', label: 'AI Status', icon: Brain },
]

const ADVANCED_ITEMS = [
  { to: '/app/browser', label: 'Browser', icon: Settings },
  { to: '/app/screen-control', label: 'Screen Control', icon: Settings },
  { to: '/app/local-agent', label: 'Local Agent', icon: Settings },
  { to: '/app/storage', label: 'Storage', icon: History },
  { to: '/app/system', label: 'Resource Monitor', icon: Activity },
]

export default function Sidebar({ user, isOwnerOrAdmin, mobileOpen, onMobileClose }) {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const navigate = useNavigate()
  const version = 'v1.0.0'

  function handleNav() {
    if (mobileOpen && onMobileClose) onMobileClose()
  }

  function handleNewTask(e) {
    e.preventDefault()
    e.stopPropagation()
    navigate('/app/agent')
    window.dispatchEvent(new CustomEvent('officepilot:new-task'))
    if (mobileOpen && onMobileClose) onMobileClose()
  }

  function renderNavItem(item) {
    return (
      <NavLink key={item.to} to={item.to} end onClick={handleNav} className="nav-item">
        <NavIcon icon={item.icon} />
        <span className="nav-label">{item.label}</span>
      </NavLink>
    )
  }

  function renderSection(title, items) {
    return (
      <div className="nav-section">
        <div className="nav-section-title">{title}</div>
        {items.map(renderNavItem)}
      </div>
    )
  }

  return (
    <>
      <aside className={`sidebar ${mobileOpen ? 'sidebar--mobile-open' : ''}`} aria-label="Main navigation">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <div className="sidebar-logo">
              <svg width="28" height="28" viewBox="0 0 40 40" fill="none" aria-hidden="true">
                <rect width="40" height="40" rx="8" fill="#2563eb" />
                <path d="M10 14h20v3H10v-3zm0 6h16v3H10v-3zm0 6h12v3H10v-3z" fill="#fff" />
              </svg>
            </div>
            <div className="sidebar-brand-text">
              <div className="sidebar-brand-name">OfficePilot AI</div>
              <div className="sidebar-brand-sub">Local-first accounting automation</div>
            </div>
          </div>
        </div>

        <div className="sidebar-new-task-wrap">
          <a href="/app/agent" className="new-task-button" onClick={handleNewTask} aria-label="Start new task">
            <Plus size={18} strokeWidth={2} />
            <span>New Task</span>
          </a>
        </div>

        <nav className="sidebar-nav">
          {renderSection('MAIN', MAIN_ITEMS)}
          {renderSection('WORKSPACE', WORKSPACE_ITEMS)}
          {isOwnerOrAdmin && renderSection('ADMIN', ADMIN_ITEMS)}

          <div className="nav-section">
            <button
              className="nav-section-title nav-section-title--clickable"
              onClick={() => setShowAdvanced(!showAdvanced)}
              aria-expanded={showAdvanced}
              aria-label={showAdvanced ? 'Collapse advanced section' : 'Expand advanced section'}
            >
              {showAdvanced ? <ChevronDown size={12} strokeWidth={2} /> : <ChevronRight size={12} strokeWidth={2} />}
              ADVANCED
            </button>
            {showAdvanced && ADVANCED_ITEMS.map(renderNavItem)}
          </div>
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-footer-status">
            <span className="sidebar-footer-dot" aria-hidden="true" />
            Agent Ready
          </div>
          <div className="sidebar-footer-version">{version}</div>
        </div>
      </aside>
      {mobileOpen && (
        <div className="sidebar-overlay" onClick={onMobileClose} aria-hidden="true" />
      )}
    </>
  )
}