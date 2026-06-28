import { useState, useEffect, useCallback } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth.jsx'
import Sidebar from './Sidebar.jsx'
import TopBar from './TopBar.jsx'
import FeedbackModal from '../FeedbackModal.jsx'
import BugReportModal from '../BugReportModal.jsx'
import TrayFloatingAgent from '../agent/TrayFloatingAgent.jsx'
import VoiceOverlay from '../voice/VoiceOverlay.jsx'
import ReleaseNotesModal from '../ReleaseNotesModal.jsx'


export default function AppShell({ children }) {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const [showFeedback, setShowFeedback] = useState(false)
  const [showBugReport, setShowBugReport] = useState(false)
  const [voiceMode, setVoiceMode] = useState(null)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  useEffect(() => {
    const handler = (event) => {
      const { mode } = event.detail
      if (mode === 'dictation' || mode === 'ai_mode' || mode === 'agent_command') {
        setVoiceMode(mode)
      }
    }

    const unlisten = window.__TAURI__?.event?.listen?.('voice://shortcut', (event) => {
      const { mode } = event.payload
      if (mode === 'dictation' || mode === 'ai_mode' || mode === 'agent_command') {
        setVoiceMode(mode)
      }
    })

    const unlistenTraySkills = window.__TAURI__?.event?.listen?.('tray://skills', () => {
      navigate('/app/workflow-memory/skills')
    })

    window.addEventListener('voice://shortcut', handler)

    function handleKeyDown(e) {
      if (e.key === 'Escape' && mobileSidebarOpen) {
        setMobileSidebarOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('voice://shortcut', handler)
      window.removeEventListener('keydown', handleKeyDown)
      if (unlisten) unlisten.then(fn => fn())
      if (unlistenTraySkills) unlistenTraySkills.then(fn => fn())
    }
  }, [navigate, mobileSidebarOpen])

  const handleTranscript = useCallback((transcript, aiOutput) => {
    if (voiceMode === 'agent_command' && transcript) {
      navigate('/app/agent', { state: { command: transcript } })
    }
  }, [voiceMode, navigate])

  const handleCloseOverlay = useCallback(() => {
    setVoiceMode(null)
  }, [])

  const handleOpenAgent = useCallback((transcript) => {
    if (transcript) {
      navigate('/app/agent', { state: { command: transcript } })
    }
    setVoiceMode(null)
  }, [navigate])

  if (loading) return <div className="shell-loading"><div className="spinner" /><p>Loading...</p></div>
  if (!user) return <Navigate to="/login" replace />

  const doLogout = () => { logout(); navigate('/login') }
  const isOwnerOrAdmin = user.role === 'owner' || user.role === 'admin' || user.role === 'staff'

  return (
    <div className={`app-shell ${mobileSidebarOpen ? 'app-shell--mobile-menu' : ''}`}>
      <Sidebar user={user} isOwnerOrAdmin={isOwnerOrAdmin} mobileOpen={mobileSidebarOpen} onMobileClose={() => setMobileSidebarOpen(false)} />
      <div className="shell-main">
        <TopBar user={user} onLogout={doLogout} onFeedback={() => setShowFeedback(true)} onBugReport={() => setShowBugReport(true)} onMenuToggle={() => setMobileSidebarOpen(o => !o)} />
        <main className="shell-content">
          <div className="shell-content-inner">
            {children}
          </div>
        </main>
      </div>
      {showFeedback && <FeedbackModal onClose={() => setShowFeedback(false)} />}
      {showBugReport && <BugReportModal onClose={() => setShowBugReport(false)} />}
      <ReleaseNotesModal />
      <TrayFloatingAgent />
      {voiceMode && (
        <VoiceOverlay
          mode={voiceMode}
          onClose={handleCloseOverlay}
          onTranscript={handleTranscript}
          onOpenAgent={handleOpenAgent}
        />
      )}
    </div>
  )
}