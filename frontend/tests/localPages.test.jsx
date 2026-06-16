import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

vi.mock('../src/api.js', async () => {
  const actual = await vi.importActual('../src/api.js')
  return {
    ...actual,
    api: {
      localStatus: vi.fn(),
      localSettings: vi.fn(),
      localStorage: vi.fn(),
      patchLocalSettings: vi.fn(),
      exportAudit: vi.fn(),
      clearLocalCache: vi.fn(),
      health: vi.fn()
    }
  }
})

// Phase 8 — mock the Tauri bridge. Tests run in jsdom with no
// window.__TAURI__, so the real bridge returns a no-op; we
// override it here to simulate the four supervisor states.
vi.mock('../src/tauriBridge.js', async () => {
  const actual = await vi.importActual('../src/tauriBridge.js')
  return {
    ...actual,
    getAgentStatus: vi.fn(),
    restartAgent: vi.fn(),
    retryAgent: vi.fn(),
    onAgentStatus: vi.fn(() => () => {}),
    isTauri: vi.fn(() => false)
  }
})

import { api } from '../src/api.js'
import { getAgentStatus, restartAgent, retryAgent } from '../src/tauriBridge.js'
import LocalAgent from '../src/pages/LocalAgent.jsx'
import StorageSettings from '../src/pages/StorageSettings.jsx'
import PrivacyDashboard from '../src/pages/PrivacyDashboard.jsx'

const status = {
  app: 'officepilot-ai',
  version: '0.8.0',
  phase: 8,
  started_at: '2026-06-05T10:00:00Z',
  uptime_seconds: 3600,
  uptime_human: '1h 0m 0s',
  host: '127.0.0.1',
  port: 8000,
  url: 'http://127.0.0.1:8000',
  pid: 12345,
  python: 'C:/python.exe',
  platform: 'Windows-10',
  env: 'development',
  parser_engine: 'existing',
  ocr_enabled: true,
  gmail_configured: false,
  gmail_allow_real: true,
  data_dir: 'C:/data',
  storage_root: 'C:/storage',
  sidecar: { bundled: false, frozen: false, mode: 'system-python' },
  database: { status: 'ok' }
}

const settings = {
  settings: { ocr_enabled: true, max_upload_mb: 20, data_dir: 'C:/data' },
  mutable: ['ocr_enabled', 'max_upload_mb']
}

const storage = {
  data_dir: 'C:/data',
  storage_root: 'C:/storage',
  protected_total_bytes: 1024,
  protected_total_human: '1.0 KB',
  cache_total_bytes: 0,
  cache_total_human: '0 B',
  dirs: [
    { name: 'data', path: 'C:/data', exists: true, file_count: 0, total_bytes: 0, protected: true },
    { name: 'invoices', path: 'C:/storage/invoices', exists: true, file_count: 2, total_bytes: 1024, protected: true },
    { name: 'cache', path: 'C:/data/cache', exists: true, file_count: 0, total_bytes: 0, protected: false }
  ]
}

beforeEach(() => {
  vi.clearAllMocks()
  // Stub confirm so tests don't hang.
  vi.spyOn(window, 'confirm').mockReturnValue(true)
  // Default supervisor state for LocalAgent tests. Individual
  // tests override this to exercise the "failed" / "online" /
  // "offline" / "starting" states. ``uptime_seconds`` is set
  // large enough that ``formatUptime`` produces the same
  // "1h 0m 0s" the original test asserted.
  getAgentStatus.mockResolvedValue({
    state: 'online',
    running: true,
    mode: 'bundled',
    pid: 7777,
    uptime_seconds: 3600,
    restart_count: 0,
    last_error: null,
    last_health_at: '2026-06-05T10:01:00Z',
    health_url: 'http://127.0.0.1:8000/api/health',
    port: 8000
  })
  restartAgent.mockResolvedValue({ state: 'starting', running: false, mode: 'bundled', pid: null, uptime_seconds: 0, restart_count: 0, last_error: null, last_health_at: null, health_url: 'http://127.0.0.1:8000/api/health', port: 8000 })
  retryAgent.mockResolvedValue({ state: 'starting', running: false, mode: 'bundled', pid: null, uptime_seconds: 0, restart_count: 0, last_error: null, last_health_at: null, health_url: 'http://127.0.0.1:8000/api/health', port: 8000 })
})

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/local" element={<LocalAgent />} />
        <Route path="/local/storage" element={<StorageSettings />} />
        <Route path="/local/privacy" element={<PrivacyDashboard />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('LocalAgent page', () => {
  it('shows runtime info', async () => {
    api.localStatus.mockResolvedValue(status)
    api.localSettings.mockResolvedValue(settings)
    api.health.mockResolvedValue({ ok: true })
    renderAt('/local')
    await waitFor(() => {
      expect(screen.getByText('Local Agent')).toBeTruthy()
    })
    expect(screen.getByText(/Phase 8/)).toBeTruthy()
    // Uptime is derived from the supervisor's uptime_seconds.
    // The default mock returns 3600 which formatUptime() formats
    // as "1h 0m 0s" — wait for the mock promise to resolve and
    // the value to appear in the DOM.
    await waitFor(() => {
      expect(screen.getByText('1h 0m 0s')).toBeTruthy()
    })
    // URL is rendered in a <code> tag; use a function matcher.
    expect(screen.getAllByText((_, el) =>
      Boolean(el && el.textContent && el.textContent.includes('127.0.0.1:8000'))
    ).length).toBeGreaterThan(0)
  })

  it('renders the health probe', async () => {
    api.localStatus.mockResolvedValue(status)
    api.localSettings.mockResolvedValue(settings)
    api.health.mockResolvedValue({ ok: true, version: '0.8.0' })
    renderAt('/local')
    await waitFor(() => {
      // The "Health probe" label appears both in the
      // supervisor status summary and in the standalone
      // /api/health probe section; we just need at least one.
      expect(screen.getAllByText(/Health probe/).length).toBeGreaterThan(0)
    })
  })

  it('shows the supervisor state pill and retry button when failed', async () => {
    api.localStatus.mockResolvedValue(status)
    api.localSettings.mockResolvedValue(settings)
    api.health.mockResolvedValue({ ok: false })
    getAgentStatus.mockResolvedValue({
      state: 'failed',
      running: false,
      mode: 'bundled',
      pid: null,
      uptime_seconds: 0,
      restart_count: 5,
      last_error: 'spawn failed: missing python',
      last_health_at: null,
      health_url: 'http://127.0.0.1:8000/api/health',
      port: 8000
    })
    renderAt('/local')
    await waitFor(() => {
      expect(screen.getByText('Agent Failed')).toBeTruthy()
    })
    const retryBtn = screen.getByText(/Retry starting agent/i)
    expect(retryBtn).toBeTruthy()
    fireEvent.click(retryBtn)
    await waitFor(() => {
      expect(retryAgent).toHaveBeenCalled()
    })
  })

  it('hides the retry button when the agent is online', async () => {
    api.localStatus.mockResolvedValue(status)
    api.localSettings.mockResolvedValue(settings)
    api.health.mockResolvedValue({ ok: true })
    getAgentStatus.mockResolvedValue({
      state: 'online',
      running: true,
      mode: 'bundled',
      pid: 4242,
      uptime_seconds: 5,
      restart_count: 0,
      last_error: null,
      last_health_at: '2026-06-05T10:00:30Z',
      health_url: 'http://127.0.0.1:8000/api/health',
      port: 8000
    })
    renderAt('/local')
    await waitFor(() => {
      expect(screen.getByText('Agent Online')).toBeTruthy()
    })
    expect(screen.queryByText('Retry')).toBeNull()
  })
})

describe('StorageSettings page', () => {
  it('shows read-only and mutable settings', async () => {
    api.localSettings.mockResolvedValue(settings)
    api.localStatus.mockResolvedValue(status)
    renderAt('/local/storage')
    await waitFor(() => {
      expect(screen.getByText('Storage & Local Settings')).toBeTruthy()
    })
    // data_dir is not mutable
    expect(screen.getAllByText(/^no$/).length).toBeGreaterThan(0)
  })

  it('patches mutable settings on save', async () => {
    api.localSettings.mockResolvedValueOnce(settings).mockResolvedValueOnce({
      ...settings, settings: { ...settings.settings, max_upload_mb: 50 }
    })
    api.localStatus.mockResolvedValue(status)
    api.patchLocalSettings.mockResolvedValue({
      applied: { max_upload_mb: 50 },
      rejected: {}
    })
    renderAt('/local/storage')
    await waitFor(() => screen.getByText('Storage & Local Settings'))
    // Find the max_upload_mb input and change it.
    const input = screen.getByDisplayValue('20')
    fireEvent.change(input, { target: { value: '50' } })
    fireEvent.click(screen.getByText('Save changes'))
    await waitFor(() => {
      expect(api.patchLocalSettings).toHaveBeenCalled()
    })
    const callArgs = api.patchLocalSettings.mock.calls[0][0]
    expect(callArgs.max_upload_mb).toBe(50)
  })
})

describe('PrivacyDashboard page', () => {
  it('shows the privacy banner and storage summary', async () => {
    api.localStatus.mockResolvedValue(status)
    api.localStorage.mockResolvedValue(storage)
    renderAt('/local/privacy')
    await waitFor(() => {
      expect(screen.getByText('Privacy & Local Data')).toBeTruthy()
    })
    expect(screen.getByText(/Local-first/)).toBeTruthy()
    // "1.0 KB" appears both in the protected total summary and in
    // the per-dir table — use getAllByText.
    expect(screen.getAllByText('1.0 KB').length).toBeGreaterThan(0)
  })

  it('exports the audit log on click', async () => {
    api.localStatus.mockResolvedValue(status)
    api.localStorage.mockResolvedValue(storage)
    api.exportAudit.mockResolvedValue({
      rows_exported: 7, path: 'C:/data/audit/x.csv', limit: 1000
    })
    renderAt('/local/privacy')
    await waitFor(() => screen.getByText('Privacy & Local Data'))
    fireEvent.click(screen.getByText(/Export audit log/))
    await waitFor(() => {
      expect(api.exportAudit).toHaveBeenCalled()
    })
    await waitFor(() => {
      expect(screen.getByText(/Last export:/)).toBeTruthy()
    })
  })

  it('clears the cache on click', async () => {
    api.localStatus.mockResolvedValue(status)
    api.localStorage.mockResolvedValue(storage)
    api.clearLocalCache.mockResolvedValue({
      cleared: true, removed_files: 4, removed_bytes: 256,
      removed_bytes_human: '256 B', removed_dirs: [], skipped: []
    })
    renderAt('/local/privacy')
    await waitFor(() => screen.getByText('Privacy & Local Data'))
    fireEvent.click(screen.getByText('Clear cache'))
    await waitFor(() => {
      expect(api.clearLocalCache).toHaveBeenCalledWith(true)
    })
    await waitFor(() => {
      expect(screen.getByText(/Cleared 4 cache file/)).toBeTruthy()
    })
  })
})
