import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

const ONBOARDING_STEPS = ['Welcome', 'Whisper Model', 'Local LLM', 'Voice Test', 'Finish']

export default function OnboardingWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [setup, setSetup] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [whisperDownloading, setWhisperDownloading] = useState(false)
  const [whisperProgress, setWhisperProgress] = useState(0)
  const [useLocalLLM, setUseLocalLLM] = useState(false)
  const [localEndpoint, setLocalEndpoint] = useState('http://localhost:11434/v1')
  const [llmTesting, setLlmTesting] = useState(false)
  const [llmStatus, setLlmStatus] = useState('')
  const [voiceRecording, setVoiceRecording] = useState(false)
  const [voiceTranscript, setVoiceTranscript] = useState('')
  const [voicePlan, setVoicePlan] = useState(null)
  const [voiceTesting, setVoiceTesting] = useState(false)
  const [demoSeeded, setDemoSeeded] = useState(false)
  const [seedingDemo, setSeedingDemo] = useState(false)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  useEffect(() => {
    api.checkSetup().then(data => {
      setSetup(data)
      setUseLocalLLM(data.agent_provider === 'local')
      if (data.local_llm_reachable) setLlmStatus('connected')
      setDemoSeeded(data.demo_data_seeded)
    }).catch(() => {
      setError('Could not check system status.')
    }).finally(() => setLoading(false))
  }, [])

  const handleDownloadWhisper = useCallback(async () => {
    setWhisperDownloading(true)
    setWhisperProgress(0)
    setError('')
    try {
      const interval = setInterval(() => {
        setWhisperProgress(p => Math.min(p + 10, 90))
      }, 1000)
      await api.whisperDownloadModel()
      clearInterval(interval)
      setWhisperProgress(100)
      const updated = await api.checkSetup()
      setSetup(updated)
    } catch (err) {
      setError('Download failed. Ensure whisper is configured.')
    } finally {
      setWhisperDownloading(false)
    }
  }, [])

  const handleTestLLM = useCallback(async () => {
    setLlmTesting(true)
    setLlmStatus('testing')
    try {
      const status = await api.agentStatus()
      if (status.status === 'connected' || status.status === 'mock') {
        setLlmStatus('connected')
      } else {
        setLlmStatus('unreachable')
      }
    } catch {
      setLlmStatus('unreachable')
    } finally {
      setLlmTesting(false)
    }
  }, [])

  const handleStartVoiceTest = useCallback(async () => {
    try {
      setVoiceRecording(true)
      setVoiceTranscript('')
      setVoicePlan(null)
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      chunksRef.current = []
      recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
      recorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        setVoiceTesting(true)
        try {
          const formData = new FormData()
          formData.append('audio', blob, 'test.wav')
          const token = localStorage.getItem('access_token')
          const res = await fetch('/api/voice-layer/transcribe', {
            method: 'POST',
            headers: token ? { Authorization: `Bearer ${token}` } : {},
            body: formData,
          })
          const transcribeData = await res.json()
          setVoiceTranscript(transcribeData.transcript || transcribeData.text || '')
          if (transcribeData.transcript || transcribeData.text) {
            const planRes = await api.planAgentTask(transcribeData.transcript || transcribeData.text)
            setVoicePlan(planRes.plan || planRes)
          }
        } catch {
          setError('Voice test failed.')
        } finally {
          setVoiceTesting(false)
        }
      }
      recorder.start()
      setTimeout(() => { if (recorder.state === 'recording') recorder.stop() }, 4000)
    } catch {
      setError('Microphone access denied.')
      setVoiceRecording(false)
    }
  }, [])

  const handleSeedDemo = useCallback(async () => {
    setSeedingDemo(true)
    try {
      await api.seedDemoData()
      setDemoSeeded(true)
    } catch {
      setError('Could not seed demo data.')
    } finally {
      setSeedingDemo(false)
    }
  }, [])

  const handleFinish = useCallback(async () => {
    try {
      await api.completeOnboarding(demoSeeded)
    } catch {
      // Ignore — navigation still proceeds
    }
    navigate('/app/agent', { replace: true })
  }, [navigate, demoSeeded])

  if (loading) {
    return (
      <div className="onboarding-page">
        <div className="onboarding-card">
          <div className="onboarding-loading">Checking system setup...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="onboarding-page">
      <div className="onboarding-card">
        <div className="onboarding-progress">
          {ONBOARDING_STEPS.map((s, i) => (
            <div key={s} className={`onboarding-step-dot${i === step ? ' active' : ''}${i < step ? ' completed' : ''}`}>
              <span className="onboarding-step-number">{i < step ? '✓' : i + 1}</span>
              <span className="onboarding-step-label">{s}</span>
            </div>
          ))}
        </div>

        <div className="onboarding-content">
          {error && <div className="onboarding-error">{error}</div>}

          {step === 0 && (
            <div className="onboarding-step">
              <h1>Welcome to OfficePilot AI</h1>
              <p className="onboarding-subtitle">Your Universal Voice Accountant Agent</p>
              <div className="onboarding-features">
                <div className="onboarding-feature">Voice commands in any language</div>
                <div className="onboarding-feature">Excel automation & summaries</div>
                <div className="onboarding-feature">Local privacy-first processing</div>
                <div className="onboarding-feature">Record & replay workflows</div>
              </div>
              <p className="onboarding-hint">We will help you set up voice recognition and test everything in a few steps.</p>
            </div>
          )}

          {step === 1 && (
            <div className="onboarding-step">
              <h2>Voice Model Setup</h2>
              {setup && !setup.whisper_model_ready ? (
                <div>
                  <p>We need to download a multilingual voice recognition model (~500 MB).</p>
                  {whisperDownloading ? (
                    <div className="onboarding-progress-bar-wrapper">
                      <div className="onboarding-progress-bar" style={{ width: whisperProgress + '%' }} />
                      <span>{whisperProgress}%</span>
                    </div>
                  ) : (
                    <button className="onboarding-btn" onClick={handleDownloadWhisper} disabled={whisperDownloading}>
                      Download Voice Model
                    </button>
                  )}
                </div>
              ) : (
                <div>
                  <div className="onboarding-status-ok">Voice model is ready</div>
                  {setup && setup.whisper_cli_found && <div className="onboarding-status-ok">Whisper CLI detected</div>}
                </div>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="onboarding-step">
              <h2>Local LLM (Optional)</h2>
              <label className="onboarding-toggle">
                <input type="checkbox" checked={useLocalLLM} onChange={e => setUseLocalLLM(e.target.checked)} />
                <span>I want to use an offline LLM</span>
              </label>
              {useLocalLLM && (
                <div className="onboarding-llm-config">
                  <label>Endpoint URL:</label>
                  <input
                    type="text"
                    value={localEndpoint}
                    onChange={e => setLocalEndpoint(e.target.value)}
                    placeholder="http://localhost:11434/v1"
                    className="onboarding-input"
                    data-testid="llm-endpoint-input"
                  />
                  <button className="onboarding-btn" onClick={handleTestLLM} disabled={llmTesting}>
                    {llmTesting ? 'Testing...' : 'Test Connection'}
                  </button>
                  {llmStatus === 'connected' && <div className="onboarding-status-ok">Connected</div>}
                  {llmStatus === 'unreachable' && <div className="onboarding-status-err">Could not reach endpoint</div>}
                </div>
              )}
              <p className="onboarding-hint">Skip this if you use the integrated mock provider or a cloud LLM.</p>
            </div>
          )}

          {step === 3 && (
            <div className="onboarding-step">
              <h2>Voice Test</h2>
              <p>Say something like "download invoices and save to Excel" in any language.</p>
              <button
                className={`onboarding-btn onboarding-btn-mic${voiceRecording ? ' recording' : ''}`}
                onClick={handleStartVoiceTest}
                disabled={voiceRecording || voiceTesting}
              >
                {voiceRecording ? 'Recording...' : voiceTesting ? 'Testing...' : 'Start Voice Test'}
              </button>
              {voiceTranscript && (
                <div className="onboarding-voice-result">
                  <div className="onboarding-voice-label">Transcript:</div>
                  <div className="onboarding-voice-transcript">{voiceTranscript}</div>
                </div>
              )}
              {voicePlan && (
                <div className="onboarding-voice-result">
                  <div className="onboarding-voice-label">Generated Plan:</div>
                  <div className="onboarding-voice-plan">{voicePlan.task_title || JSON.stringify(voicePlan)}</div>
                </div>
              )}
            </div>
          )}

          {step === 4 && (
            <div className="onboarding-step">
              <h2>You are ready!</h2>
              <div className="onboarding-summary">
                <div className="onboarding-summary-item">
                  <span>Voice Model</span>
                  <span>{setup?.whisper_model_ready ? 'Ready' : 'Not downloaded'}</span>
                </div>
                <div className="onboarding-summary-item">
                  <span>LLM Provider</span>
                  <span>{setup?.agent_provider || 'mock'}</span>
                </div>
                <div className="onboarding-summary-item">
                  <span>Demo Data</span>
                  <span>{demoSeeded ? 'Loaded' : 'Not loaded'}</span>
                </div>
              </div>
              {!demoSeeded && (
                <button className="onboarding-btn" onClick={handleSeedDemo} disabled={seedingDemo}>
                  {seedingDemo ? 'Loading...' : 'Load Sample Data'}
                </button>
              )}
            </div>
          )}
        </div>

        <div className="onboarding-footer">
          {step > 0 && (
            <button className="onboarding-btn onboarding-btn-secondary" onClick={() => setStep(s => s - 1)}>Back</button>
          )}
          <div className="onboarding-footer-right">
            {step < ONBOARDING_STEPS.length - 1 ? (
              <button className="onboarding-btn" onClick={() => setStep(s => s + 1)}>
                {step === 0 ? 'Get Started' : 'Next'}
              </button>
            ) : (
              <button className="onboarding-btn onboarding-btn-primary" onClick={handleFinish}>
                Go to Dashboard
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
