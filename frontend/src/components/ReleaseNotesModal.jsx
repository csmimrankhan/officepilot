import { useState, useEffect } from 'react'
import { BrainCircuit, Scale, MousePointerClick, Eye, Cpu, Sparkles } from 'lucide-react'

const VERSION = '1.0.0'
const HIGHLIGHTS = [
  { icon: BrainCircuit, text: 'Multi-Agent Swarm Architecture', desc: 'Specialist agents for Auditor, Tax, and Data Entry tasks' },
  { icon: Scale, text: 'Semantic Bank Reconciliation', desc: 'AI-powered matching of bank feeds against invoices' },
  { icon: MousePointerClick, text: 'Live Voice-Driven Excel Editing', desc: 'Real-time COM automation on your active workbook' },
  { icon: Eye, text: 'Autonomous Background Watchers', desc: 'Always-on monitoring of Gmail, Drive, and local folders' },
  { icon: Cpu, text: 'Ollama Local LLM Brain', desc: 'Private on-device AI with no cloud dependency' },
]

export default function ReleaseNotesModal({ onClose }) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const seen = localStorage.getItem('last_seen_version')
    if (!seen || seen < VERSION) {
      setVisible(true)
    }
  }, [])

  function handleDismiss() {
    localStorage.setItem('last_seen_version', VERSION)
    setVisible(false)
    onClose?.()
  }

  if (!visible) return null

  return (
    <div className="modal-overlay" role="dialog" aria-modal="true" aria-label="Release notes">
      <div className="release-notes-modal">
        <div className="release-notes-header">
          <Sparkles size={28} strokeWidth={1.5} className="release-notes-sparkle" />
          <h2>Welcome to OfficePilot v1.0.0</h2>
          <p className="release-notes-subtitle">The Grand Release — Phase 45 is here</p>
        </div>

        <div className="release-notes-body">
          {HIGHLIGHTS.map(({ icon: Icon, text, desc }) => (
            <div key={text} className="release-notes-item">
              <div className="release-notes-icon">
                <Icon size={22} strokeWidth={1.5} />
              </div>
              <div>
                <strong>{text}</strong>
                <p>{desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="release-notes-footer">
          <button className="release-notes-btn" onClick={handleDismiss}>
            Got it!
          </button>
        </div>
      </div>
    </div>
  )
}
