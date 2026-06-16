import { useState } from 'react'
import VoiceCommandModal from './VoiceCommandModal.jsx'

export default function FloatingVoiceAssistant() {
  const [isOpen, setIsOpen] = useState(false)

  // Hide on public landing/auth pages
  const isPublicPage = ['/login', '/register', '/', '/landing'].includes(window.location.pathname)
  if (isPublicPage) return null

  return (
    <>
      <div className="floating-voice-button" onClick={() => setIsOpen(true)} title="Voice Command (Alt+V)">
        <span className="icon">🎤</span>
      </div>
      
      <VoiceCommandModal 
        isOpen={isOpen} 
        onClose={() => setIsOpen(false)} 
      />
    </>
  )
}
