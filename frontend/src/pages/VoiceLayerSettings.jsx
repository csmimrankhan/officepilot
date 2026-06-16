import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function VoiceLayerSettings() {
  const [status, setStatus] = useState(null)
  const [dbSettings, setDbSettings] = useState({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')
  const [testResult, setTestResult] = useState(null)
  const [testBusy, setTestBusy] = useState(false)
  const [downloadBusy, setDownloadBusy] = useState(false)
  const [downloadResult, setDownloadResult] = useState(null)

  const load = async () => {
    setError('')
    try {
      const [s, d] = await Promise.all([
        api.voiceLayerStatus().catch(() => null),
        api.getVoiceLayerSettings().catch(() => ({ settings: {} })),
      ])
      setStatus(s)
      setDbSettings(d.settings || {})
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [])

  const save = async () => {
    setBusy(true)
    setError('')
    setSaved('')
    try {
      const result = await api.updateVoiceLayerSettings(dbSettings)
      setDbSettings(result.settings || dbSettings)
      setSaved('Settings saved.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const update = (key, value) => setDbSettings(prev => ({ ...prev, [key]: value }))

  const handleTestTranscribe = async () => {
    setTestBusy(true)
    setTestResult(null)
    setError('')
    try {
      const result = await api.testTranscribe()
      setTestResult(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setTestBusy(false)
    }
  }

  const handleDetect = async () => {
    setError('')
    try {
      const result = await api.whisperDetect()
      if (result.whisper_cli_path) update('whisper_cli_path', result.whisper_cli_path)
      if (result.whisper_model_path) update('whisper_model_path', result.whisper_model_path)
      setSaved('Auto-detection complete.')
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDownloadModel = async () => {
    setDownloadBusy(true)
    setDownloadResult(null)
    setError('')
    try {
      const result = await api.whisperDownloadModel(status.default_model_name || 'ggml-base.en.bin')
      setDownloadResult(result)
      if (result.ok) {
        setSaved('Model downloaded. Saving path...')
        update('whisper_model_path', result.path)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setDownloadBusy(false)
    }
  }

  if (!status) return <div className="card">Loading voice layer settings…</div>

  const whisperReady = status.whisper_configured
  const whisperMsg = status.whisper_message || ''

  return (
    <div>
      <div className="page-header">
        <h2>Voice Layer</h2>
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Local dictation, AI mode, and agent command mode using whisper.cpp.
        </p>
      </div>
      {error && <div className="alert error">{error}</div>}
      {saved && <div className="alert success">{saved}</div>}

      <div className="card">
        <h3>Voice Layer</h3>
        <label className="toggle-row">
          <input type="checkbox" checked={status.enabled !== false} onChange={() => {}} disabled />
          Voice Layer: {status.enabled ? 'Enabled' : 'Disabled'}
        </label>
        <div className="form-row">
          <label>Default Mode</label>
          <select value={status.mode_default || 'dictation'} disabled>
            <option value="dictation">Dictation</option>
            <option value="ai_mode">AI Mode</option>
            <option value="agent_command">Agent Command</option>
          </select>
        </div>
        <div className="form-row">
          <label>Language</label>
          <input type="text" value={status.language || 'auto'} disabled />
        </div>
      </div>

      <div className="card">
        <h3>whisper.cpp</h3>
        <div className="form-row">
          <label>CLI Path</label>
          <input type="text" placeholder="C:\whisper.cpp\build\bin\Release\whisper-cli.exe"
            value={dbSettings.whisper_cli_path || status.whisper_cli_path || ''}
            onChange={e => update('whisper_cli_path', e.target.value)} />
        </div>
        <div className="form-row">
          <label>Model Path</label>
          <input type="text" placeholder="C:\whisper.cpp\models\ggml-base.bin"
            value={dbSettings.whisper_model_path || status.whisper_model_path || ''}
            onChange={e => update('whisper_model_path', e.target.value)} />
        </div>
        <div style={{
          marginTop: '8px',
          padding: '8px 12px',
          borderRadius: '6px',
          fontSize: '13px',
          fontWeight: 500,
          background: whisperReady ? '#f0fdf4' : '#fef2f2',
          color: whisperReady ? '#16a34a' : '#dc2626',
        }}>
          {whisperReady ? 'Local Whisper Ready' : whisperMsg || 'Whisper not configured'}
        </div>
        {status.whisper_cli_found && !status.whisper_model_found && (
          <div style={{ marginTop: '8px' }}>
            <button className="btn btn--outline btn--sm" onClick={handleDownloadModel} disabled={downloadBusy}>
              {downloadBusy ? 'Downloading...' : `Download ${status.default_model_name || 'ggml-base.en.bin'}`}
            </button>
            {downloadResult && (
              <div style={{ marginTop: '4px', fontSize: '12px', color: downloadResult.ok ? '#16a34a' : '#dc2626' }}>
                {downloadResult.ok ? `Downloaded (${Math.round(downloadResult.size_bytes / 1024 / 1024)} MB)` : downloadResult.error}
              </div>
            )}
          </div>
        )}
        <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
          <button className="btn btn--outline btn--sm" onClick={handleDetect}>
            Auto-Detect Paths
          </button>
          <button className="btn btn--outline btn--sm" onClick={handleTestTranscribe} disabled={testBusy || !whisperReady}>
            {testBusy ? 'Testing...' : 'Test Transcription'}
          </button>
        </div>
        {testResult && (
          <div style={{
            marginTop: '8px',
            padding: '8px 12px',
            borderRadius: '6px',
            fontSize: '13px',
            background: testResult.ok ? '#f0fdf4' : '#fef2f2',
            color: testResult.ok ? '#16a34a' : '#dc2626',
          }}>
            {testResult.ok ? (
              <>
                <div>Transcription: "{testResult.transcript}"</div>
                <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
                  Duration: {testResult.duration_ms}ms | Engine: {testResult.engine}
                </div>
              </>
            ) : (
              <div>Test failed: {testResult.error}</div>
            )}
          </div>
        )}
      </div>

      <div className="card">
        <h3>Shortcuts</h3>
        <div className="form-row">
          <label>Dictation</label>
          <input type="text" value={status.shortcuts?.dictation || 'Ctrl+Alt+Space'} disabled />
        </div>
        <div className="form-row">
          <label>AI Mode</label>
          <input type="text" value={status.shortcuts?.ai_mode || 'Ctrl+Alt+A'} disabled />
        </div>
        <div className="form-row">
          <label>Agent Command</label>
          <input type="text" value={status.shortcuts?.agent || 'Ctrl+Alt+O'} disabled />
        </div>
        <p style={{ fontSize: '12px', color: '#9ca3af', marginTop: '4px' }}>
          Global shortcuts are registered by the Tauri shell. Open the app and press
          Ctrl+Alt+Space (Dictation), Ctrl+Alt+A (AI Mode), or Ctrl+Alt+O (Agent Command).
        </p>
      </div>

      <div className="card">
        <h3>Paste Behavior</h3>
        <label className="toggle-row">
          <input type="checkbox" checked={dbSettings.confirm_before_paste ?? status.confirm_before_paste !== false}
            onChange={e => update('confirm_before_paste', e.target.checked)} />
          Confirm before paste
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={dbSettings.save_history ?? status.save_history !== false}
            onChange={e => update('save_history', e.target.checked)} />
          Save dictation history
        </label>
        <label className="toggle-row">
          <input type="checkbox" checked={dbSettings.beep_enabled ?? status.beep_enabled !== false}
            onChange={e => update('beep_enabled', e.target.checked)} />
          Play beep on start/stop
        </label>
      </div>

      <div className="card">
        <h3>AI Mode (Cloud LLM)</h3>
        <div className="form-row">
          <label>Provider</label>
          <input type="text" value={status.ai_mode?.provider || 'openai_compatible'} disabled />
        </div>
        <div style={{ marginTop: '8px', fontSize: '13px' }}>
          <span style={{ color: status.ai_mode?.allow_cloud ? '#16a34a' : '#9ca3af' }}>
            {status.ai_mode?.allow_cloud ? 'Cloud access enabled' : 'Cloud access disabled'}
          </span>
          <span style={{ marginLeft: '16px', color: status.ai_mode?.configured ? '#16a34a' : '#9ca3af' }}>
            {status.ai_mode?.configured ? 'API key set' : 'API key not set'}
          </span>
        </div>
        {!status.ai_mode?.allow_cloud && (
          <div style={{ marginTop: '8px', padding: '6px 10px', background: '#fef2f2', borderRadius: '6px', fontSize: '12px', color: '#dc2626' }}>
            AI Mode cloud access is disabled. Set AI_MODE_ALLOW_CLOUD=true in your .env file to enable.
          </div>
        )}
      </div>

      <div className="card">
        <h3>Recording Status</h3>
        <div style={{ fontSize: '13px' }}>
          Active: {status.recording?.active ? (
            <span style={{ color: '#dc2626', fontWeight: 600 }}>Recording ({status.recording?.mode})</span>
          ) : (
            <span style={{ color: '#6b7280' }}>Idle</span>
          )}
        </div>
      </div>

      <button className="btn btn--primary" onClick={save} disabled={busy} style={{ marginTop: '12px' }}>
        {busy ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  )
}