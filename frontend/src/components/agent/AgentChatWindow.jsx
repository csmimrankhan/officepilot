import { useEffect, useRef } from 'react'

const AGENT_STYLES = {
  auditor: { bg: '#dbeafe', color: '#1e40af', label: 'Auditor', icon: 'search' },
  tax: { bg: '#dcfce7', color: '#166534', label: 'Tax Agent', icon: 'calculator' },
  data_entry: { bg: '#fee2e2', color: '#991b1b', label: 'Data Entry', icon: 'database' },
  general: { bg: '#e0e7ff', color: '#3730a3', label: 'General', icon: 'bot' },
}

function AgentBadge({ assignedAgent }) {
  const key = assignedAgent?.toLowerCase?.() || 'general'
  const style = AGENT_STYLES[key] || AGENT_STYLES.general
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '4px',
      fontSize: '10px', fontWeight: 600, padding: '2px 8px',
      borderRadius: '10px', background: style.bg, color: style.color,
      marginBottom: '4px',
    }}>
      {style.label}
    </span>
  )
}

export default function AgentChatWindow({ messages = [] }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    try { bottomRef.current?.scrollIntoView?.({ behavior: 'smooth' }) } catch { /* jsdom compatible */ }
  }, [messages.length])

  if (!messages || messages.length === 0) {
    return (
      <div className="agent-chat-empty">
        <style>{`
          .agent-chat-empty { padding: 24px; text-align: center; color: #6c7086; font-size: 13px; }
          .agent-chat-message { padding: 8px 12px; border-radius: 10px; margin-bottom: 8px; font-size: 13px; line-height: 1.5; max-width: 85%; word-wrap: break-word; }
          .agent-chat-message.user { background: #45475a; color: #cdd6f4; align-self: flex-end; margin-left: auto; }
          .agent-chat-message.agent { background: #313244; color: #bac2de; align-self: flex-start; }
        `}</style>
        <p>Ask your Accountant Agent a task.</p>
        <p style={{ fontSize: '11px', marginTop: '4px' }}>Try: "Read this screen", "Record this workflow", "Emergency stop"</p>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column' }}>
      <style>{`
        .agent-chat-message { padding: 8px 12px; border-radius: 10px; margin-bottom: 8px; font-size: 13px; line-height: 1.5; max-width: 85%; word-wrap: break-word; }
        .agent-chat-message.user { background: #45475a; color: #cdd6f4; align-self: flex-end; margin-left: auto; }
        .agent-chat-message.agent { background: #313244; color: #bac2de; align-self: flex-start; }
      `}</style>
      {messages.map((msg) => (
        <div key={msg.id} className={`agent-chat-message ${msg.role}`}>
          {msg.role === 'agent' && msg.assignedAgent && (
            <AgentBadge assignedAgent={msg.assignedAgent} />
          )}
          <div>{msg.text}</div>
          <div style={{ fontSize: '10px', color: '#6c7086', marginTop: '4px' }}>
            {msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : ''} · {msg.role === 'user' ? 'You' : 'Agent'}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
