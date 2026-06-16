import { useEffect, useState, useCallback } from 'react'
import { api, formatDateTime } from '../api.js'
import {
  getAgentStatus,
  getAgentLogs,
  revealSidecarLogs,
  restartAgent,
  retryAgent,
  onAgentStatus,
  AGENT_STATE_LABELS,
  bootStatusMessage,
  isTauri
} from '../tauriBridge.js'
import FeedbackModal from '../components/FeedbackModal.jsx'

function StatusPill({ ok, label, kind = 'ok' }) {
  return (
    <span className={`badge ${kind}`}>
      {ok ? '● ' : '○ '}{label}
    </span>
  )
}

function StatePill({ state }) {
  const kind = {
    online: 'ok',
    starting: 'starting',
    offline: 'bad',
    failed: 'failed'
  }[state] || 'subtle'
  return (
    <span className={`badge ${kind}`}>
      {AGENT_STATE_LABELS[state] || state || 'Unknown'}
    </span>
  )
}

function formatDuration(ms) {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(1)}s`
}

export default function LocalAgent() {
  const [status, setStatus] = useState(null)
  const [settings, setSettings] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [health, setHealth] = useState(null)
  const [pulse, setPulse] = useState(0)
  // Phase 8 — Tauri supervisor status (when running inside the
  // desktop shell). Falls back to a sensible default in the
  // browser so the UI still renders.
  const [agent, setAgent] = useState({
    state: 'offline',
    running: false,
    mode: 'system-python',
    pid: null,
    uptime_seconds: 0,
    restart_count: 0,
    last_error: null,
    last_health_at: null,
    health_url: 'http://127.0.0.1:8000/api/health',
    port: 8000,
    spawn_started_at: null,
    first_port_open_at: null,
    first_health_ok_at: null,
    boot_duration_ms: null,
    boot_grace_active: false,
    log_path: ''
  })
  const [agentAction, setAgentAction] = useState(null) // 'restart' | 'retry' | 'open-logs' | 'reveal' | null
  // Phase 11 — local 1.5s polling clock so the "Agent Starting
  // for N s" message updates even if no supervisor event fires
  // (e.g. when the page is open in the browser, where the
  // Tauri event channel is absent).
  const [now, setNow] = useState(Date.now())
  // Phase 11 — log preview snapshot from ``get_agent_logs``.
  const [logs, setLogs] = useState(null)
  const [showFeedback, setShowFeedback] = useState(false)
  const [exportingLogs, setExportingLogs] = useState(false)

  const load = useCallback(async () => {
    setError('')
    try {
      const [s, st] = await Promise.all([
        api.localStatus(),
        api.localSettings()
      ])
      setStatus(s)
      setSettings(st)
    } catch (err) {
      setError(err.message || 'Failed to load local agent status.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Periodic health check (every 10s) so the user sees the dot
  // change colour if the backend goes away.
  useEffect(() => {
    const tick = async () => {
      try {
        const h = await api.health()
        setHealth(h)
      } catch {
        setHealth({ ok: false })
      }
      setPulse((p) => p + 1)
    }
    tick()
    const id = setInterval(tick, 10000)
    return () => clearInterval(id)
  }, [])

  // Phase 11 — fast 1.5s "wall clock" tick so the "Agent
  // Starting for N s…" message updates smoothly while the
  // sidecar boots. The supervisor's own event stream is the
  // source of truth for the state; this loop only advances the
  // local ``now`` counter.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1500)
    return () => clearInterval(id)
  }, [])

  // Phase 8 — read the supervisor's authoritative state from
  // the Tauri shell and subscribe to its event stream. In a
  // plain browser the bridge returns a no-op so the UI still
  // renders.
  useEffect(() => {
    let cancelled = false
    getAgentStatus().then((s) => { if (!cancelled) setAgent(s) })
    const unsub = onAgentStatus((s) => { if (!cancelled) setAgent(s) })
    const id = setInterval(() => {
      getAgentStatus().then((s) => { if (!cancelled) setAgent(s) })
    }, 5000)
    return () => {
      cancelled = true
      clearInterval(id)
      if (typeof unsub === 'function') unsub()
    }
  }, [])

  const onRetry = useCallback(async () => {
    setAgentAction('retry')
    try {
      const next = await retryAgent()
      setAgent(next)
    } catch (e) {
      setError(e.message || 'Retry failed.')
    } finally {
      setAgentAction(null)
    }
  }, [])

  const onRestart = useCallback(async () => {
    setAgentAction('restart')
    try {
      const next = await restartAgent()
      setAgent(next)
    } catch (e) {
      setError(e.message || 'Restart failed.')
    } finally {
      setAgentAction(null)
    }
  }, [])

  const onOpenLogs = useCallback(async () => {
    setAgentAction('open-logs')
    try {
      const info = await getAgentLogs()
      setLogs(info)
    } catch (e) {
      setError(e.message || 'Failed to read sidecar logs.')
    } finally {
      setAgentAction(null)
    }
  }, [])

  const onRevealLogs = useCallback(async () => {
    setAgentAction('reveal')
    try {
      const ok = await revealSidecarLogs()
      if (!ok) setError('Could not open the file explorer. Check the path manually.')
    } catch (e) {
      setError(e.message || 'Reveal logs failed.')
    } finally {
      setAgentAction(null)
    }
  }, [])

  const onExportLogs = useCallback(async () => {
    setExportingLogs(true)
    setError('')
    try {
      const result = await api.exportLogs()
      const byteChars = atob(result.content_base64)
      const byteNums = new Array(byteChars.length)
      for (let i = 0; i < byteChars.length; i++) {
        byteNums[i] = byteChars.charCodeAt(i)
      }
      const byteArray = new Uint8Array(byteNums)
      const blob = new Blob([byteArray], { type: 'application/zip' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = result.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e.message || 'Failed to export logs.')
    } finally {
      setExportingLogs(false)
    }
  }, [])

  if (loading) return <div className="subtle">Loading local agent…</div>
  if (error && !status) return <div className="alert error">{error}</div>
  if (!status) return <div className="muted">No data.</div>

  const liveOk = !!(health && health.ok)
  const dbOk = status.database && status.database.status === 'ok'
  const ocrOn = !!status.ocr_enabled
  const gmailOn = !!status.gmail_configured
  // Combined verdict: the supervisor's state wins over the
  // 10-second poll, but the dot still shows the raw /api/health
  // answer so the user can spot a split-brain.
  const supervisorState = agent.state || 'offline'
  const showRetry = supervisorState === 'failed' || supervisorState === 'offline'

  // Phase 11 — compute "starting for N s" from spawn_started_at
  // when we don't have a fresh boot_duration_ms yet. This is
  // used both in the summary card and in the friendly
  // starting message.
  const startingSeconds = (() => {
    if (supervisorState !== 'starting' || !agent.spawn_started_at) return 0
    const t0 = new Date(agent.spawn_started_at).getTime()
    if (!Number.isFinite(t0)) return 0
    return Math.max(0, Math.floor((now - t0) / 1000))
  })()

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Local Agent</h2>
          <span className="subtle">
            Phase {status.phase} · v{status.version} · {status.env}
          </span>
        </div>
        <button type="button" className="secondary" onClick={load}>Refresh</button>
      </div>

      <h3>Agent status</h3>
      <p className="subtle">
        Authoritative state from the {isTauri() ? 'desktop supervisor' : 'local agent endpoint'}.
        A failed agent can be revived with the Retry button.
      </p>
      <div className="run-summary">
        <div>
          <div className="subtle">State</div>
          <div>
            <StatePill state={supervisorState} />
          </div>
        </div>
        <div>
          <div className="subtle">Health probe</div>
          <div>
            <StatusPill ok={liveOk} label={liveOk ? 'Online' : 'Offline'} kind={liveOk ? 'ok' : 'bad'} />
          </div>
        </div>
        <div>
          <div className="subtle">Mode</div>
          <div>
            <code className="mono">{agent.mode || (status.sidecar && status.sidecar.mode) || 'system-python'}</code>
          </div>
        </div>
        <div>
          <div className="subtle">PID</div>
          <code className="mono">{agent.pid || status.pid || '—'}</code>
        </div>
        <div>
          <div className="subtle">Uptime</div>
          <div>
            {agent.uptime_seconds
              ? formatUptime(agent.uptime_seconds)
              : (status.uptime_human || '—')}
          </div>
        </div>
        <div>
          <div className="subtle">Restarts</div>
          <div>{agent.restart_count ?? 0}</div>
        </div>
      </div>

      {/* Phase 11 — friendly boot / failure messaging. The
          pill colour is set by ``.alert`` variant; the message
          text comes from ``bootStatusMessage`` so the user
          always sees an explanation for the current state. */}
      <div className={`alert ${
        supervisorState === 'online' ? 'success' :
        supervisorState === 'starting' ? (agent.boot_grace_active ? 'info' : 'warning') :
        supervisorState === 'failed' ? 'error' : 'warning'
      }`}>
        {bootStatusMessage(agent) || '—'}
        {supervisorState === 'starting' && startingSeconds > 0 && (
          <span className="subtle"> · starting for {startingSeconds}s</span>
        )}
        {supervisorState === 'online' && agent.boot_duration_ms != null && (
          <span className="subtle"> · first port open in {formatDuration(
            (new Date(agent.first_port_open_at || agent.spawn_started_at).getTime()) -
            (new Date(agent.spawn_started_at || agent.first_port_open_at).getTime())
          )}</span>
        )}
        {supervisorState === 'starting' && agent.boot_grace_active && (
          <div className="muted small" style={{ marginTop: 6 }}>
            We give the sidecar up to 60 seconds on first launch
            before reporting failure, so Windows Defender can scan
            the bundled .exe and PyInstaller can unpack the
            runtime.
          </div>
        )}
        {showRetry && (
          <div style={{ marginTop: 8 }}>
            <button
              type="button"
              className="primary"
              onClick={onRetry}
              disabled={agentAction !== null}
            >
              {agentAction === 'retry' ? 'Retrying…' : 'Retry starting agent'}
            </button>{' '}
            <button
              type="button"
              className="secondary"
              onClick={onRestart}
              disabled={agentAction !== null}
            >
              {agentAction === 'restart' ? 'Restarting…' : 'Force restart'}
            </button>{' '}
            <button
              type="button"
              className="secondary"
              onClick={onOpenLogs}
              disabled={agentAction !== null}
            >
              {agentAction === 'open-logs' ? 'Loading…' : 'Open logs'}
            </button>
            {' '}
            <button
              type="button"
              className="secondary"
              onClick={onExportLogs}
              disabled={exportingLogs}
            >
              {exportingLogs ? 'Exporting…' : 'Export Logs'}
            </button>
            {' '}
            <button
              type="button"
              className="secondary"
              onClick={() => setShowFeedback(true)}
            >
              Send Feedback
            </button>
          </div>
        )}
        {!showRetry && (
          <div style={{ marginTop: 8 }}>
            <button
              type="button"
              className="secondary"
              onClick={onOpenLogs}
              disabled={agentAction !== null}
            >
              {agentAction === 'open-logs' ? 'Loading…' : 'Open logs'}
            </button>
            {' '}
            <button
              type="button"
              className="secondary"
              onClick={onExportLogs}
              disabled={exportingLogs}
            >
              {exportingLogs ? 'Exporting…' : 'Export Logs'}
            </button>
            {' '}
            <button
              type="button"
              className="secondary"
              onClick={() => setShowFeedback(true)}
            >
              Send Feedback
            </button>
          </div>
        )}
      </div>

      <h3>Runtime</h3>
      <table className="data-table">
        <tbody>
          <tr><th>Started at</th><td>{formatDateTime(status.started_at) || '—'}</td></tr>
          <tr><th>Python</th><td><code className="mono">{status.python}</code></td></tr>
          <tr><th>Platform</th><td>{status.platform}</td></tr>
          <tr><th>Database</th><td>
            <StatusPill ok={dbOk} label={dbOk ? 'connected' : 'error'} kind={dbOk ? 'ok' : 'bad'} />
            {status.database && status.database.error
              ? <span className="subtle"> · {status.database.error}</span>
              : null}
          </td></tr>
          <tr><th>OCR</th><td>
            <StatusPill ok={ocrOn} label={ocrOn ? 'enabled' : 'disabled'} kind={ocrOn ? 'ok' : 'bad'} />
          </td></tr>
          <tr><th>Gmail</th><td>
            <StatusPill ok={gmailOn} label={gmailOn ? 'configured' : 'not configured'} kind={gmailOn ? 'ok' : 'bad'} />
            <span className="subtle"> · allow_real = {String(status.gmail_allow_real)}</span>
          </td></tr>
          <tr><th>Parser engine</th><td><code className="mono">{status.parser_engine}</code></td></tr>
          <tr><th>Data dir</th><td><code className="mono">{status.data_dir}</code></td></tr>
          <tr><th>Storage root</th><td><code className="mono">{status.storage_root}</code></td></tr>
          {status.sidecar && (
            <tr>
              <th>Sidecar</th>
              <td>
                <code className="mono">{status.sidecar.mode}</code>
                <span className="subtle"> · bundled={String(status.sidecar.bundled)}</span>
              </td>
            </tr>
          )}
          {agent.health_url && (
            <tr>
              <th>Supervisor health URL</th>
              <td><code className="mono">{agent.health_url}</code></td>
            </tr>
          )}
          {agent.last_health_at && (
            <tr>
              <th>Supervisor last probe</th>
              <td>{formatDateTime(agent.last_health_at)}</td>
            </tr>
          )}
        </tbody>
      </table>

      <h3>Boot diagnostics</h3>
      <p className="subtle">
        Timestamps recorded by the supervisor around the most recent
        sidecar spawn. Useful when the user asks "why did it take so
        long to start?".
      </p>
      <table className="data-table">
        <tbody>
          <tr>
            <th>Spawn started at</th>
            <td>{formatDateTime(agent.spawn_started_at) || '—'}</td>
          </tr>
          <tr>
            <th>First port-open</th>
            <td>{formatDateTime(agent.first_port_open_at) || '—'}</td>
          </tr>
          <tr>
            <th>First healthy probe</th>
            <td>{formatDateTime(agent.first_health_ok_at) || '—'}</td>
          </tr>
          <tr>
            <th>Cold-boot duration</th>
            <td>{formatDuration(agent.boot_duration_ms)}</td>
          </tr>
          <tr>
            <th>Boot grace</th>
            <td>
              <StatusPill
                ok={agent.boot_grace_active}
                label={agent.boot_grace_active ? 'active (60s window)' : 'expired or offline'}
                kind={agent.boot_grace_active ? 'info' : 'subtle'}
              />
            </td>
          </tr>
          <tr>
            <th>Sidecar log</th>
            <td>
              <code className="mono">{agent.log_path || '—'}</code>
              {isTauri() && (
                <>
                  {' '}
                  <button
                    type="button"
                    className="link"
                    onClick={onRevealLogs}
                    disabled={agentAction !== null || !agent.log_path}
                  >
                    {agentAction === 'reveal' ? 'Opening…' : 'Reveal in Explorer'}
                  </button>
                </>
              )}
            </td>
          </tr>
        </tbody>
      </table>

      {/* Phase 11 — log preview panel. Hidden until the user
          clicks "Open logs"; rendered as a code block so users
          can copy lines out. */}
      {logs && (
        <div className="card">
          <div className="page-header" style={{ marginBottom: 8 }}>
            <h3 style={{ margin: 0 }}>Sidecar log</h3>
            <span className="subtle">
              {logs.exists
                ? `${(logs.size_bytes / 1024).toFixed(1)} KB · last ${logs.last_lines.length} non-empty lines`
                : 'log file not found yet'}
            </span>
          </div>
          {logs.exists ? (
            <pre className="json-block">
              {logs.last_lines.length
                ? logs.last_lines.join('\n')
                : '(log is empty so far)'}
            </pre>
          ) : (
            <div className="muted small">
              The log file is created the first time the sidecar
              writes to stdout / stderr. If the agent has never
              started, no file exists yet.
            </div>
          )}
        </div>
      )}

      {settings && (
        <>
          <h3>Mutable settings (this session)</h3>
          <p className="subtle">
            These settings live in <code className="mono">os.environ</code> for the
            lifetime of this process. Restarting the agent reverts to the
            values in <code className="mono">.env</code>.
          </p>
          <table className="data-table">
            <thead>
              <tr><th>Key</th><th>Current value</th><th>Mutable</th></tr>
            </thead>
            <tbody>
              {Object.entries(settings.settings).map(([k, v]) => (
                <tr key={k}>
                  <td><code className="mono">{k}</code></td>
                  <td><code className="mono">{String(v)}</code></td>
                  <td>{settings.mutable.includes(k)
                    ? <StatusPill ok={true} label="yes" kind="ok" />
                    : <span className="subtle">no</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      <h3>Health probe</h3>
      <p className="subtle">
        Polled every 10s. The most recent result is shown below.
        <span className="subtle"> · probe #{pulse}</span>
      </p>
      <pre className="json-block">
        {JSON.stringify(health || { probing: true }, null, 2)}
      </pre>

      {showFeedback && <FeedbackModal onClose={() => setShowFeedback(false)} />}
    </div>
  )
}

function formatUptime(seconds) {
  if (seconds == null || (typeof seconds !== 'number' && isNaN(seconds))) return '—'
  const s = Math.max(0, Math.floor(seconds))
  const days = Math.floor(s / 86400)
  const hours = Math.floor((s % 86400) / 3600)
  const minutes = Math.floor((s % 3600) / 60)
  const secs = s % 60
  // Always show the three non-day units so the output is
  // stable across renders (matches the Python agent's
  // ``uptime_human`` format: "1h 0m 0s" not "1h 0s").
  if (days) {
    return `${days}d ${hours}h ${minutes}m ${secs}s`
  }
  return `${hours}h ${minutes}m ${secs}s`
}
