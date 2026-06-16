import { useState, useEffect } from 'react'
import { api } from '../api.js'

function ConfigRow({ label, value, highlight }) {
  const valueColor = highlight
    ? (value === 'No' || value === 'Not configured' ? '#16a34a' : '#2563eb')
    : 'var(--text-secondary)'
  return (
    <div className="admin-ai-config-row">
      <span className="admin-ai-config-label">{label}</span>
      <span style={{ fontWeight: highlight ? 600 : 400, color: valueColor, wordBreak: 'break-all' }}>{value}</span>
    </div>
  )
}

export default function AdminAIStatus() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    api.getAdminAIStatus()
      .then(r => { if (!cancelled) setData(r) })
      .catch(e => { if (!cancelled) setError(e?.message || 'Failed to load AI status') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div className="page-header-info">
            <h2>AI Status</h2>
            <p className="page-header-subtitle">OfficePilot runs fully without LLM. Cloud AI is optional and disabled by default.</p>
          </div>
        </div>
        <div className="loading-state"><div className="spinner" /><p>Loading AI status...</p></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div className="page-header-info">
            <h2>AI Status</h2>
            <p className="page-header-subtitle">OfficePilot runs fully without LLM. Cloud AI is optional and disabled by default.</p>
          </div>
        </div>
        <div className="error-state">
          <h3>Failed to load</h3>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="page-container">
        <div className="page-header">
          <div className="page-header-info">
            <h2>AI Status</h2>
            <p className="page-header-subtitle">OfficePilot runs fully without LLM. Cloud AI is optional and disabled by default.</p>
          </div>
        </div>
        <div className="empty-state"><p className="subtle">No AI status data available.</p></div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="page-header-info">
          <h2>AI Status</h2>
          <p className="page-header-subtitle">OfficePilot runs fully without LLM. Cloud AI is optional and disabled by default.</p>
        </div>
      </div>

      {data.zero_cloud_by_default && (
        <div className="card" style={{ padding: 12, marginBottom: 16, borderLeft: '4px solid #22c55e', background: '#dcfce7' }}>
          <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: '#166534' }}>
            This build makes zero cloud AI calls. All agents use local mock planning.
          </p>
        </div>
      )}

      {data.message && (
        <div className="card" style={{ padding: 12, marginBottom: 12, borderLeft: '4px solid #f59e0b', background: '#fef3c7' }}>
          <p style={{ margin: 0, fontSize: 13, fontWeight: 500 }}>{data.message}</p>
        </div>
      )}

      <div className="admin-ai-grid">
        <div className="card admin-ai-section">
          <h3 className="admin-ai-section-title">Agent Planner</h3>
          <div className="admin-ai-config-rows">
            <ConfigRow label="Provider" value={data.agent_provider || 'mock'} highlight />
            <ConfigRow label="Model" value={data.agent_model || '(default)'} />
            <ConfigRow label="API Base URL" value={data.agent_api_base_url || '(none)'} />
            <ConfigRow label="API Key" value={data.agent_api_key_configured ? 'Configured' : 'Not configured'} highlight />
            <ConfigRow label="Cloud AI Allowed" value={data.agent_allow_cloud ? 'Yes' : 'No'} highlight />
          </div>
        </div>

        <div className="card admin-ai-section">
          <h3 className="admin-ai-section-title">AI Mode Dictation Polish</h3>
          <div className="admin-ai-config-rows">
            <ConfigRow label="Provider" value={data.ai_mode_provider || '(none)'} />
            <ConfigRow label="Model" value={data.ai_mode_model || '(default)'} />
            <ConfigRow label="API Key" value={data.ai_mode_api_key_configured ? 'Configured' : 'Not configured'} highlight />
            <ConfigRow label="Cloud AI Allowed" value={data.ai_mode_allow_cloud ? 'Yes' : 'No'} highlight />
          </div>
        </div>

        <div className="card admin-ai-section">
          <h3 className="admin-ai-section-title">Voice Speech-to-Text</h3>
          <div className="admin-ai-config-rows">
            <ConfigRow label="Provider" value={data.voice_provider || 'mock'} highlight />
            <ConfigRow label="Cloud STT Allowed" value={data.voice_allow_cloud_stt ? 'Yes' : 'No'} highlight />
            <ConfigRow label="OpenAI API Key" value={data.openai_api_key_configured ? 'Configured' : 'Not configured'} highlight />
          </div>
        </div>
      </div>
    </div>
  )
}
