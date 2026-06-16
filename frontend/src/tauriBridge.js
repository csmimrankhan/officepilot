/**
 * Tiny Tauri 2.0 bridge for the OfficePilot AI frontend.
 *
 * The Tauri shell injects a ``window.__TAURI__`` global inside the
 * WebView. We use it to talk to the Rust supervisor:
 *
 *   - ``getAgentStatus()``        -> AgentStatus
 *   - ``restartAgent()``          -> AgentStatus   (kills + respawns)
 *   - ``retryAgent()``            -> AgentStatus   (resets the failed cap)
 *   - ``getAgentLogs()``          -> { path, size, last_lines }
 *   - ``revealSidecarLogs()``     -> bool          (pops file explorer)
 *   - ``onAgentStatus(cb)``       -> unsubscribe fn  (listens to agent://status)
 *
 * Phase 11 — boot-timing fields (``spawn_started_at``,
 * ``first_port_open_at``, ``first_health_ok_at``,
 * ``boot_duration_ms``, ``boot_grace_active``, ``log_path``)
 * are populated by the supervisor and rendered by the Local
 * Agent page so the user sees "started in 4.2s" once the sidecar
 * comes online.
 *
 * When the page is opened in a plain browser (npm run dev, or
 * tests under jsdom) the bridge returns safe fallbacks so the UI
 * still renders. Tests stub the global via
 * ``tests/setup.js`` + the per-test vi.mock calls.
 */

const tauriGlobal = (typeof window !== 'undefined' && window.__TAURI__) || null

function isTauriContext() {
  return Boolean(tauriGlobal && tauriGlobal.core && typeof tauriGlobal.core.invoke === 'function')
}

function invokeFallback() {
  // Plain-browser / test fallback. The Local Agent page already
  // shows "Offline" when the API is unreachable, so this is a
  // coherent degraded mode.
  return Promise.resolve({
    state: 'offline',
    running: false,
    mode: 'system-python',
    pid: null,
    uptime_seconds: 0,
    restart_count: 0,
    last_error: 'not running inside the OfficePilot desktop shell',
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
}

function logsFallback() {
  return Promise.resolve({
    sidecar_log_path: '',
    tauri_log_path: null,
    size_bytes: 0,
    exists: false,
    last_lines: []
  })
}

export function getAgentStatus() {
  if (!isTauriContext()) return invokeFallback()
  return tauriGlobal.core.invoke('get_agent_status')
}

export function restartAgent() {
  if (!isTauriContext()) return invokeFallback()
  return tauriGlobal.core.invoke('request_agent_restart')
}

export function retryAgent() {
  if (!isTauriContext()) return invokeFallback()
  return tauriGlobal.core.invoke('request_agent_retry')
}

export function getAgentLogs() {
  if (!isTauriContext()) return logsFallback()
  return tauriGlobal.core.invoke('get_agent_logs')
}

export function revealSidecarLogs() {
  if (!isTauriContext()) return Promise.resolve(false)
  return tauriGlobal.core.invoke('reveal_sidecar_logs')
}

/**
 * Subscribe to the supervisor's status updates.
 *
 * Returns an unsubscribe function. In a non-Tauri context this
 * is a no-op.
 */
export function onAgentStatus(callback) {
  if (!isTauriContext()) return () => {}
  if (!tauriGlobal.event || typeof tauriGlobal.event.listen !== 'function') {
    return () => {}
  }
  let cancelled = false
  let unlistenPromise = null
  tauriGlobal.event
    .listen('agent://status', (evt) => {
      if (!cancelled) callback(evt.payload)
    })
    .then((un) => {
      if (cancelled && typeof un === 'function') un()
      else unlistenPromise = Promise.resolve(un)
    })
  return () => {
    cancelled = true
    if (unlistenPromise && typeof unlistenPromise.then === 'function') {
      unlistenPromise.then((un) => { if (typeof un === 'function') un() })
    }
  }
}

export const AGENT_STATE_LABELS = {
  starting: 'Agent Starting',
  online: 'Agent Online',
  offline: 'Agent Offline',
  failed: 'Agent Failed'
}

// Phase 11 — the Local Agent page uses these to render a
// one-line status summary that matches the supervisor's
// boot-grace semantics.
export function bootStatusMessage(agent) {
  if (!agent) return ''
  const state = agent.state
  if (state === 'online') {
    if (agent.boot_duration_ms != null) {
      return `Agent online. Cold-start took ${(agent.boot_duration_ms / 1000).toFixed(1)}s.`
    }
    return 'Agent online.'
  }
  if (state === 'starting') {
    if (agent.boot_grace_active) {
      return 'OfficePilot Agent is starting. First launch may take longer while Windows checks the app.'
    }
    return 'OfficePilot Agent is starting…'
  }
  if (state === 'offline') {
    return 'Agent is offline. Use Retry to bring it back.'
  }
  if (state === 'failed') {
    if (agent.last_error) return `Agent failed: ${agent.last_error}`
    return 'Agent failed after multiple restart attempts. Use Retry to try again.'
  }
  return ''
}

export function isTauri() {
  return isTauriContext()
}
