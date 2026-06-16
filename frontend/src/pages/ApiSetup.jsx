import { useEffect, useState } from 'react'
import { api } from '../api.js'

function StatusBadge({ ok, label, detail }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0' }}>
      <span style={{
        width: 10, height: 10, borderRadius: '50%',
        background: ok ? '#16a34a' : '#9ca3af',
        display: 'inline-block', flexShrink: 0,
      }} />
      <span style={{ fontSize: '13px', color: ok ? '#16a34a' : '#6b7280' }}>
        {label}
      </span>
      {detail && <span style={{ fontSize: '12px', color: '#9ca3af' }}>({detail})</span>}
    </div>
  )
}

function SectionCard({ title, children }) {
  return (
    <div className="card" style={{ marginBottom: '12px' }}>
      <h3 style={{ margin: '0 0 12px', fontSize: '15px', color: 'var(--text)' }}>{title}</h3>
      {children}
    </div>
  )
}

export default function ApiSetup() {
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [testResult, setTestResult] = useState('')

  const load = async () => {
    try {
      const [agentStatus, local] = await Promise.all([
        api.agentStatus(),
        api.localSettings().catch(() => ({})),
      ])
      setStatus({ ...agentStatus, local })
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [])

  const testConnection = async () => {
    setBusy(true)
    setTestResult('')
    try {
      const result = await api.planAgentTask({ command: 'test connection', context: {} })
      setTestResult(result?.task_title ? `Connected — received response: "${result.task_title}"` : 'Connected — no errors')
    } catch (err) {
      setTestResult(`Connection failed: ${err.message}`)
    } finally {
      setBusy(false)
    }
  }

  if (!status) return <div className="card">Loading API setup…</div>

  const env = status.local?.env || {}
  const provider = status.provider || '-'
  const apiKeyPresent = !!(status.api_key || env.AGENT_API_KEY)
  const cloudAllowed = status.allow_cloud === true || env.AGENT_ALLOW_CLOUD === 'true'
  const model = status.model || env.AGENT_MODEL || '-'
  const baseUrl = status.base_url || env.AGENT_API_BASE_URL || '-'

  return (
    <div>
      <div className="page-header">
        <h2>API Setup</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Configure LLM, voice, and integration providers. Required env vars shown below.
        </p>
      </div>
      {error && <div className="alert error">{error}</div>}

      <SectionCard title="LLM Provider">
        <StatusBadge
          ok={provider === 'mock' || provider === 'connected'}
          label={provider === 'mock' ? 'Mock (local)' : provider === 'connected' ? 'Connected' : 'Disconnected'}
          detail={`Provider: ${provider}`}
        />
        <StatusBadge ok={!!apiKeyPresent} label={apiKeyPresent ? 'API Key: present' : 'API Key: not set'} />
        <StatusBadge ok={cloudAllowed} label={cloudAllowed ? 'Cloud calls: allowed' : 'Cloud calls: disabled (default)'} />
        <StatusBadge ok={!!model && model !== '-'} label={`Model: ${model}`} />
        <StatusBadge ok={!!baseUrl && baseUrl !== '-'} label={`Base URL: ${baseUrl}`} />
        <div style={{ marginTop: '8px' }}>
          <button className="btn btn--primary" onClick={testConnection} disabled={busy}>
            {busy ? 'Testing…' : 'Test Connection'}
          </button>
          {testResult && (
            <div style={{ marginTop: '8px', padding: '8px 12px', borderRadius: '6px', fontSize: '13px', background: testResult.includes('failed') ? '#fef2f2' : '#f0fdf4', color: testResult.includes('failed') ? '#dc2626' : '#16a34a' }}>
              {testResult}
            </div>
          )}
        </div>
        <details style={{ marginTop: '12px', fontSize: '12px', color: '#6b7280' }}>
          <summary style={{ cursor: 'pointer' }}>Required env vars</summary>
          <pre style={{ marginTop: '4px', padding: '8px', background: '#f3f4f6', borderRadius: '4px', overflowX: 'auto' }}>
AGENT_PROVIDER=mock|openai_compatible|deepseek
AGENT_API_BASE_URL=https://api.deepseek.com
AGENT_API_KEY=sk-...
AGENT_MODEL=deepseek-chat
AGENT_ALLOW_CLOUD=true|false
AGENT_TIMEOUT_SECONDS=60
AGENT_MAX_STEPS=20
AGENT_DRY_RUN_DEFAULT=true
          </pre>
        </details>
      </SectionCard>

      <SectionCard title="STT (Speech-to-Text) Provider">
        <StatusBadge
          ok={true}
          label={env.VOICE_PROVIDER === 'openai' ? 'OpenAI Whisper' : env.VOICE_PROVIDER === 'local' ? 'Local Whisper' : 'Browser-based (default)'}
          detail={`Provider: ${env.VOICE_PROVIDER || 'browser'}`}
        />
        <StatusBadge
          ok={!!env.OPENAI_API_KEY}
          label={env.OPENAI_API_KEY ? 'OpenAI API Key: present' : 'OpenAI API Key: not set'}
        />
        <StatusBadge
          ok={env.VOICE_ALLOW_CLOUD_STT === 'true'}
          label={env.VOICE_ALLOW_CLOUD_STT === 'true' ? 'Cloud STT: allowed' : 'Cloud STT: disabled'}
        />
        <StatusBadge
          ok={!!env.LOCAL_WHISPER_PATH || env.VOICE_PROVIDER !== 'local'}
          label={env.LOCAL_WHISPER_PATH ? `Local Whisper path: ${env.LOCAL_WHISPER_PATH}` : 'Local Whisper: not configured'}
        />
      </SectionCard>

      <SectionCard title="TTS (Text-to-Speech) Provider">
        <StatusBadge
          ok={env.TTS_ENABLED === 'true'}
          label={env.TTS_ENABLED === 'true' ? 'TTS: enabled' : 'TTS: disabled'}
          detail={`Provider: ${env.TTS_PROVIDER || 'none'}`}
        />
      </SectionCard>

      <SectionCard title="Gmail / Email Integration (Optional)">
        <StatusBadge
          ok={!!env.OFFICEPILOT_GMAIL_ALLOW_REAL}
          label={env.OFFICEPILOT_GMAIL_ALLOW_REAL === 'true' ? 'Real Gmail API: allowed' : 'Real Gmail: disabled (dry-run only)'}
        />
        <StatusBadge
          ok={!!env.GOOGLE_CLIENT_ID || !!env.OFFICEPILOT_GMAIL_CLIENT_ID}
          label={env.GOOGLE_CLIENT_ID || env.OFFICEPILOT_GMAIL_CLIENT_ID ? 'Client ID: configured' : 'Client ID: not set'}
        />
        <StatusBadge
          ok={!!env.GOOGLE_CLIENT_SECRET || !!env.OFFICEPILOT_GMAIL_CLIENT_SECRET}
          label={env.GOOGLE_CLIENT_SECRET || env.OFFICEPILOT_GMAIL_CLIENT_SECRET ? 'Client Secret: configured' : 'Client Secret: not set'}
        />
      </SectionCard>

      <SectionCard title="Browser Automation (Optional)">
        <StatusBadge
          ok={env.BROWSER_AUTOMATION_ENABLED === 'true'}
          label={env.BROWSER_AUTOMATION_ENABLED === 'true' ? 'Browser automation: enabled' : 'Browser automation: disabled (default)'}
        />
        <StatusBadge
          ok={!!env.BROWSER_ALLOWED_DOMAINS || !env.BROWSER_ALLOWED_DOMAINS}
          label={env.BROWSER_ALLOWED_DOMAINS ? `Allowed domains: ${env.BROWSER_ALLOWED_DOMAINS}` : 'Allowed domains: default'}
        />
      </SectionCard>

      <SectionCard title="Provider Status">
        <StatusBadge
          ok={status.status === 'mock' || status.status === 'connected'}
          label={`Agent provider: ${status.status || 'unknown'}`}
        />
        <StatusBadge
          ok={status.dry_run_default !== false}
          label={`Dry-run default: ${status.dry_run_default !== false ? 'enabled' : 'disabled'}`}
        />
        <StatusBadge ok={true} label={`Timeout: ${status.timeout || '60'}s`} />
        <StatusBadge ok={true} label={`Max steps: ${status.max_steps || '20'}`} />
      </SectionCard>
    </div>
  )
}