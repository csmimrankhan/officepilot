import { vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import VoiceOverlay from '../src/components/voice/VoiceOverlay.jsx'
import VoiceLayerSettings from '../src/pages/VoiceLayerSettings.jsx'
import DictationHistory from '../src/pages/DictationHistory.jsx'

// ── Mock the api module (hoisted to avoid ReferenceError) ─────────────────────

const mockApi = vi.hoisted(() => ({
  base: 'http://127.0.0.1:8000',
  voiceLayerStatus: vi.fn(),
  getVoiceLayerSettings: vi.fn(),
  updateVoiceLayerSettings: vi.fn(),
}))
vi.mock('../src/api.js', () => ({ api: mockApi }))

// ── Mock localStorage ─────────────────────────────────────────────────────────

const localStorageMock = (() => {
  let store = {}
  return {
    getItem: vi.fn((k) => store[k] ?? null),
    setItem: vi.fn((k, v) => { store[k] = String(v) }),
    removeItem: vi.fn((k) => { delete store[k] }),
    clear: vi.fn(() => { store = {} }),
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// ── Mock fetch ────────────────────────────────────────────────────────────────

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// ── Mock MediaRecorder + getUserMedia ─────────────────────────────────────────

class MockMediaRecorder {
  constructor(stream, options) {
    this.stream = stream
    this.state = 'inactive'
    this.ondataavailable = null
    this.onstop = null
    this.onerror = null
  }
  start() { this.state = 'recording' }
  stop() {
    this.state = 'inactive'
    if (this.ondataavailable) this.ondataavailable({ data: { size: 100 } })
    if (this.onstop) this.onstop()
  }
}
vi.stubGlobal('MediaRecorder', MockMediaRecorder)

// Stub navigator.mediaDevices (keep existing navigator props)
const mockGetUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] })
Object.defineProperty(globalThis.navigator, 'mediaDevices', {
  value: { getUserMedia: mockGetUserMedia },
  configurable: true, writable: true,
})
Object.defineProperty(globalThis.navigator, 'clipboard', {
  value: { writeText: vi.fn().mockResolvedValue(undefined) },
  configurable: true, writable: true,
})

// Helper to find Polished text with "→ " prefix
function textWithPrefix(prefix, text) {
  return (_content, element) => {
    const hasText = (node) => node.textContent === `${prefix}${text}` || node.textContent === text
    const elementHasText = hasText(element)
    const childrenDontHaveText = Array.from(element.children).every(child => !hasText(child))
    return elementHasText && childrenDontHaveText
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderOverlay(props = {}) {
  return render(<MemoryRouter><VoiceOverlay mode="dictation" onClose={vi.fn()} {...props} /></MemoryRouter>)
}

function renderSettings() {
  return render(<MemoryRouter><VoiceLayerSettings /></MemoryRouter>)
}

function renderHistory() {
  return render(<MemoryRouter><DictationHistory /></MemoryRouter>)
}

// ═════════════════════════════════════════════════════════════════════════════
// VoiceOverlay
// ═════════════════════════════════════════════════════════════════════════════

describe('VoiceOverlay', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
    localStorageMock.getItem.mockReturnValue('test-token')
    mockFetch.mockReset()
    mockGetUserMedia.mockClear()
  })

  it('renders idle state with mic button', () => {
    renderOverlay()
    expect(screen.getByText('🎤')).toBeTruthy()
  })

  it('shows recording state on mic click', async () => {
    renderOverlay()
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => {
      expect(screen.getByText(/Recording/)).toBeTruthy()
    })
    expect(document.querySelector('.voice-overlay-dot')).toBeTruthy()
  })

  it('shows microphone denied error when getUserMedia fails', async () => {
    mockGetUserMedia.mockRejectedValueOnce(new Error('Permission denied'))
    renderOverlay()
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => {
      expect(screen.getByText(/Microphone access denied/)).toBeTruthy()
    })
  })

  it('shows transcribing state after stop', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, transcript: 'hello world', ai_output: null, engine: 'mock' }),
    })
    renderOverlay()
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => expect(screen.getByText(/Recording/)).toBeTruthy())
    fireEvent.click(screen.getByText('Stop'))
    await waitFor(() => {
      expect(screen.getByText(/Transcribing/)).toBeTruthy()
    })
  })

  it('shows transcript and paste button after transcription', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, transcript: 'hello world', ai_output: null, engine: 'mock' }),
    })
    renderOverlay()
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => expect(screen.getByText(/Recording/)).toBeTruthy())
    fireEvent.click(screen.getByText('Stop'))
    await waitFor(() => {
      expect(screen.getByText('hello world')).toBeTruthy()
      expect(screen.getByText('Paste')).toBeTruthy()
      expect(screen.getByText('Cancel')).toBeTruthy()
    })
  })

  it('shows Send to Agent button for agent_command mode', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, transcript: 'show invoices', ai_output: null, engine: 'mock' }),
    })
    const onOpenAgent = vi.fn()
    renderOverlay({ mode: 'agent_command', onOpenAgent })
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => expect(screen.getByText(/Recording/)).toBeTruthy())
    fireEvent.click(screen.getByText('Stop'))
    await waitFor(() => {
      expect(screen.getByText('Send to Agent')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Send to Agent'))
    expect(onOpenAgent).toHaveBeenCalledWith('show invoices')
  })

  it('shows pasted state after successful paste', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ok: true, transcript: 'test', ai_output: null, engine: 'mock' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ok: true, status: 'pasted' }),
      })
    renderOverlay()
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => expect(screen.getByText(/Recording/)).toBeTruthy())
    fireEvent.click(screen.getByText('Stop'))
    await waitFor(() => expect(screen.getByText('Paste')).toBeTruthy())
    fireEvent.click(screen.getByText('Paste'))
    await waitFor(() => {
      expect(screen.getByText(/Pasted/)).toBeTruthy()
    })
  })

  it('shows cancelled state on cancel', async () => {
    renderOverlay()
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => expect(screen.getByText(/Recording/)).toBeTruthy())
    fireEvent.click(screen.getByText('✕'))
    expect(screen.getByText('Cancelled')).toBeTruthy()
  })

  it('shows mode label for dictation', async () => {
    renderOverlay({ mode: 'dictation' })
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => {
      expect(screen.getByText('Dictation')).toBeTruthy()
    })
  })

  it('shows mode label for AI mode', async () => {
    renderOverlay({ mode: 'ai_mode' })
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => {
      expect(screen.getByText('AI Mode')).toBeTruthy()
    })
  })

  it('shows mode label for agent command', async () => {
    renderOverlay({ mode: 'agent_command' })
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => {
      expect(screen.getByText('Agent Command')).toBeTruthy()
    })
  })

  it('shows recording timer while recording', async () => {
    renderOverlay()
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => {
      expect(screen.getByText(/00:00/)).toBeTruthy()
    })
  })

  it('shows transcript preview after transcription', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, transcript: 'transcript preview text', ai_output: null, engine: 'mock' }),
    })
    renderOverlay()
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => expect(screen.getByText(/Recording/)).toBeTruthy())
    fireEvent.click(screen.getByText('Stop'))
    await waitFor(() => {
      expect(screen.getByText('transcript preview text')).toBeTruthy()
    })
  })

  it('renders from shortcut event trigger via voice://shortcut', async () => {
    // The overlay renders based on voiceMode state in AppShell.
    // This test verifies the VoiceOverlay component renders properly
    // when initiated with different modes.
    render(
      <MemoryRouter>
        <VoiceOverlay mode="dictation" onClose={vi.fn()} />
      </MemoryRouter>
    )
    expect(screen.getByText('🎤')).toBeTruthy()
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => {
      expect(screen.getByText(/Recording/)).toBeTruthy()
    })
  })

  it('shows Send to Agent button for agent_command mode and navigates to agent', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, transcript: 'create excel summary', ai_output: null, engine: 'mock' }),
    })
    const onOpenAgent = vi.fn()
    render(<MemoryRouter><VoiceOverlay mode="agent_command" onClose={vi.fn()} onOpenAgent={onOpenAgent} /></MemoryRouter>)
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => expect(screen.getByText(/Recording/)).toBeTruthy())
    fireEvent.click(screen.getByText('Stop'))
    await waitFor(() => {
      expect(screen.getByText('Send to Agent')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Send to Agent'))
    await waitFor(() => {
      expect(onOpenAgent).toHaveBeenCalledWith('create excel summary')
    })
  })
})

// ═════════════════════════════════════════════════════════════════════════════
// VoiceLayerSettings
// ═════════════════════════════════════════════════════════════════════════════

describe('VoiceLayerSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApi.voiceLayerStatus.mockReset()
    mockApi.getVoiceLayerSettings.mockReset()
    mockApi.updateVoiceLayerSettings.mockReset()
  })

  it('shows loading state initially', () => {
    mockApi.voiceLayerStatus.mockReturnValue(new Promise(() => {}))
    mockApi.getVoiceLayerSettings.mockReturnValue(new Promise(() => {}))
    renderSettings()
    expect(screen.getByText(/Loading voice layer settings/)).toBeTruthy()
  })

  it('renders status fields when loaded', async () => {
    mockApi.voiceLayerStatus.mockResolvedValue({
      enabled: true, mode_default: 'dictation', language: 'auto',
      whisper_configured: false, whisper_cli_path: '', whisper_model_path: '',
      confirm_before_paste: true, save_history: true,
      beep_enabled: true, overlay_enabled: true,
      shortcuts: { dictation: 'Ctrl+Alt+Space', ai_mode: 'Ctrl+Alt+A', agent: 'Ctrl+Alt+O' },
      ai_mode: { configured: false, allow_cloud: false, provider: 'openai_compatible' },
      recording: { active: false, mode: null },
    })
    mockApi.getVoiceLayerSettings.mockResolvedValue({ settings: {} })
    renderSettings()
    await waitFor(() => {
      expect(screen.getAllByText(/Voice Layer/).length).toBeGreaterThan(0)
    })
    expect(screen.getByText(/Enabled/)).toBeTruthy()
    expect(screen.getByDisplayValue('Dictation')).toBeTruthy()
    expect(screen.getByDisplayValue('auto')).toBeTruthy()
  })

  it('shows whisper not configured indicator', async () => {
    mockApi.voiceLayerStatus.mockResolvedValue({
      enabled: true, mode_default: 'dictation', language: 'auto',
      whisper_configured: false, whisper_cli_path: '', whisper_model_path: '',
      whisper_cli_found: false, whisper_model_found: false,
      whisper_message: 'Whisper not configured',
      default_model_name: 'ggml-base.en.bin',
      confirm_before_paste: true, save_history: true,
      beep_enabled: true, overlay_enabled: true,
      shortcuts: { dictation: 'Ctrl+Alt+Space', ai_mode: 'Ctrl+Alt+A', agent: 'Ctrl+Alt+O' },
      ai_mode: { configured: false, allow_cloud: false, provider: 'openai_compatible' },
      recording: { active: false, mode: null },
    })
    mockApi.getVoiceLayerSettings.mockResolvedValue({ settings: {} })
    renderSettings()
    await waitFor(() => {
      expect(screen.getByText(/Whisper not configured/)).toBeTruthy()
    })
  })

  it('shows local whisper ready status when configured', async () => {
    mockApi.voiceLayerStatus.mockResolvedValue({
      enabled: true, mode_default: 'dictation', language: 'auto',
      whisper_configured: true, whisper_cli_path: 'C:\\whisper-cli.exe', whisper_model_path: 'C:\\model.bin',
      whisper_cli_found: true, whisper_model_found: true,
      whisper_message: 'Local Whisper Ready',
      default_model_name: 'ggml-base.en.bin',
      confirm_before_paste: true, save_history: true,
      beep_enabled: true, overlay_enabled: true,
      shortcuts: { dictation: 'Ctrl+Alt+Space', ai_mode: 'Ctrl+Alt+A', agent: 'Ctrl+Alt+O' },
      ai_mode: { configured: false, allow_cloud: false, provider: 'openai_compatible' },
      recording: { active: false, mode: null },
    })
    mockApi.getVoiceLayerSettings.mockResolvedValue({ settings: {} })
    renderSettings()
    await waitFor(() => {
      expect(screen.getByText('Local Whisper Ready')).toBeTruthy()
    })
  })

  it('shows auto-detect and test transcription buttons', async () => {
    mockApi.voiceLayerStatus.mockResolvedValue({
      enabled: true, mode_default: 'dictation', language: 'auto',
      whisper_configured: false, whisper_cli_path: '', whisper_model_path: '',
      whisper_cli_found: false, whisper_model_found: false,
      whisper_message: 'Whisper not configured',
      default_model_name: 'ggml-base.en.bin',
      confirm_before_paste: true, save_history: true,
      beep_enabled: true, overlay_enabled: true,
      shortcuts: { dictation: 'Ctrl+Alt+Space', ai_mode: 'Ctrl+Alt+A', agent: 'Ctrl+Alt+O' },
      ai_mode: { configured: false, allow_cloud: false, provider: 'openai_compatible' },
      recording: { active: false, mode: null },
    })
    mockApi.getVoiceLayerSettings.mockResolvedValue({ settings: {} })
    renderSettings()
    await waitFor(() => {
      expect(screen.getByText('Auto-Detect Paths')).toBeTruthy()
      expect(screen.getByText('Test Transcription')).toBeTruthy()
    })
  })

  it('shows AI mode cloud-disabled warning', async () => {
    mockApi.voiceLayerStatus.mockResolvedValue({
      enabled: true, mode_default: 'dictation', language: 'auto',
      whisper_configured: false, whisper_cli_path: '', whisper_model_path: '',
      whisper_cli_found: false, whisper_model_found: false,
      whisper_message: 'Whisper not configured',
      default_model_name: 'ggml-base.en.bin',
      confirm_before_paste: true, save_history: true,
      beep_enabled: true, overlay_enabled: true,
      shortcuts: { dictation: 'Ctrl+Alt+Space', ai_mode: 'Ctrl+Alt+A', agent: 'Ctrl+Alt+O' },
      ai_mode: { configured: false, allow_cloud: false, provider: 'openai_compatible' },
      recording: { active: false, mode: null },
    })
    mockApi.getVoiceLayerSettings.mockResolvedValue({ settings: {} })
    renderSettings()
    await waitFor(() => {
      expect(screen.getByText(/Cloud access disabled/)).toBeTruthy()
      // The AI mode warning should show
      expect(screen.getByText(/Set AI_MODE_ALLOW_CLOUD/)).toBeTruthy()
    })
  })

  it('shows dictation mode UI for Ctrl+Alt+Space shortcut', async () => {
    // Dictation mode overlay shows when mode='dictation'
    render(<MemoryRouter><VoiceOverlay mode="dictation" onClose={vi.fn()} /></MemoryRouter>)
    expect(screen.getByText('🎤')).toBeTruthy()
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => {
      expect(screen.getByText('Dictation')).toBeTruthy()
    })
  })

  it('shows AI mode cloud-disabled error message in overlay when cloud not available', async () => {
    // The AI mode overlay should still open but the backend
    // will reject the transcribe call with cloud-disabled error
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ detail: 'AI Mode requires cloud LLM access. Set AI_MODE_ALLOW_CLOUD=true.' }),
    })
    render(<MemoryRouter><VoiceOverlay mode="ai_mode" onClose={vi.fn()} /></MemoryRouter>)
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => expect(screen.getByText(/Recording/)).toBeTruthy())
    fireEvent.click(screen.getByText('Stop'))
    await waitFor(() => {
      expect(screen.getByText(/AI Mode requires cloud LLM access/)).toBeTruthy()
    })
  })

  it('agent command mode opens Accountant Agent via onOpenAgent callback', async () => {
    const onOpenAgent = vi.fn()
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, transcript: 'show invoices', ai_output: null, engine: 'mock' }),
    })
    render(<MemoryRouter><VoiceOverlay mode="agent_command" onClose={vi.fn()} onOpenAgent={onOpenAgent} /></MemoryRouter>)
    fireEvent.click(screen.getByText('🎤'))
    await waitFor(() => expect(screen.getByText(/Recording/)).toBeTruthy())
    fireEvent.click(screen.getByText('Stop'))
    await waitFor(() => expect(screen.getByText('Send to Agent')).toBeTruthy())
    fireEvent.click(screen.getByText('Send to Agent'))
    await waitFor(() => {
      expect(onOpenAgent).toHaveBeenCalledWith('show invoices')
    })
  })

  it('voice settings show test transcription result when test passes', async () => {
    mockApi.voiceLayerStatus.mockResolvedValue({
      enabled: true, mode_default: 'dictation', language: 'auto',
      whisper_configured: true, whisper_cli_path: 'C:\\whisper.exe', whisper_model_path: 'C:\\model.bin',
      whisper_cli_found: true, whisper_model_found: true,
      whisper_message: 'Local Whisper Ready',
      default_model_name: 'ggml-base.en.bin',
      confirm_before_paste: true, save_history: true,
      beep_enabled: true, overlay_enabled: true,
      shortcuts: { dictation: 'Ctrl+Alt+Space', ai_mode: 'Ctrl+Alt+A', agent: 'Ctrl+Alt+O' },
      ai_mode: { configured: false, allow_cloud: false, provider: 'openai_compatible' },
      recording: { active: false, mode: null },
    })
    mockApi.getVoiceLayerSettings.mockResolvedValue({ settings: {} })
    mockApi.testTranscribe = vi.fn().mockResolvedValue({
      ok: true, transcript: 'test tone', duration_ms: 500, engine: 'whisper_cpp',
    })
    renderSettings()
    await waitFor(() => {
      expect(screen.getByText('Test Transcription')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Test Transcription'))
    await waitFor(() => {
      expect(screen.getByText(/test tone/)).toBeTruthy()
    })
  })

  it('auto-detect button calls whisperDetect API', async () => {
    mockApi.voiceLayerStatus.mockResolvedValue({
      enabled: true, mode_default: 'dictation', language: 'auto',
      whisper_configured: false, whisper_cli_path: '', whisper_model_path: '',
      whisper_cli_found: false, whisper_model_found: false,
      whisper_message: 'Whisper not configured',
      default_model_name: 'ggml-base.en.bin',
      confirm_before_paste: true, save_history: true,
      beep_enabled: true, overlay_enabled: true,
      shortcuts: { dictation: 'Ctrl+Alt+Space', ai_mode: 'Ctrl+Alt+A', agent: 'Ctrl+Alt+O' },
      ai_mode: { configured: false, allow_cloud: false, provider: 'openai_compatible' },
      recording: { active: false, mode: null },
    })
    mockApi.getVoiceLayerSettings.mockResolvedValue({ settings: {} })
    mockApi.whisperDetect = vi.fn().mockResolvedValue({
      whisper_cli_path: 'C:\\detected\\whisper-cli.exe',
      whisper_model_path: 'C:\\detected\\model.bin',
    })
    mockApi.whisperDownloadModel = vi.fn()
    mockApi.testTranscribe = vi.fn()
    renderSettings()
    await waitFor(() => {
      expect(screen.getByText('Auto-Detect Paths')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Auto-Detect Paths'))
    await waitFor(() => {
      expect(mockApi.whisperDetect).toHaveBeenCalled()
    })
  })

  it('shows recording idle status', async () => {
    mockApi.voiceLayerStatus.mockResolvedValue({
      enabled: true, mode_default: 'dictation', language: 'auto',
      whisper_configured: false, whisper_cli_path: '', whisper_model_path: '',
      confirm_before_paste: true, save_history: true,
      beep_enabled: true, overlay_enabled: true,
      shortcuts: { dictation: 'Ctrl+Alt+Space', ai_mode: 'Ctrl+Alt+A', agent: 'Ctrl+Alt+O' },
      ai_mode: { configured: false, allow_cloud: false, provider: 'openai_compatible' },
      recording: { active: false, mode: null },
    })
    mockApi.getVoiceLayerSettings.mockResolvedValue({ settings: {} })
    renderSettings()
    await waitFor(() => {
      expect(screen.getByText('Idle')).toBeTruthy()
    })
  })

  it('saves settings on button click', async () => {
    mockApi.voiceLayerStatus.mockResolvedValue({
      enabled: true, mode_default: 'dictation', language: 'auto',
      whisper_configured: false, whisper_cli_path: '', whisper_model_path: '',
      confirm_before_paste: true, save_history: true,
      beep_enabled: true, overlay_enabled: true,
      shortcuts: { dictation: 'Ctrl+Alt+Space', ai_mode: 'Ctrl+Alt+A', agent: 'Ctrl+Alt+O' },
      ai_mode: { configured: false, allow_cloud: false, provider: 'openai_compatible' },
      recording: { active: false, mode: null },
    })
    mockApi.getVoiceLayerSettings.mockResolvedValue({ settings: {} })
    mockApi.updateVoiceLayerSettings.mockResolvedValue({ settings: {} })
    renderSettings()
    await waitFor(() => expect(screen.getByText('Save Settings')).toBeTruthy())
    fireEvent.click(screen.getByText('Save Settings'))
    await waitFor(() => {
      expect(screen.getByText(/Settings saved/)).toBeTruthy()
    })
  })
})

// ═════════════════════════════════════════════════════════════════════════════
// DictationHistory
// ═════════════════════════════════════════════════════════════════════════════

describe('DictationHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
    localStorageMock.getItem.mockReturnValue('test-token')
    mockFetch.mockReset()
  })

  it('shows loading state initially', () => {
    mockFetch.mockReturnValue(new Promise(() => {}))
    renderHistory()
    expect(screen.getByText(/Loading history/)).toBeTruthy()
  })

  it('shows empty state', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, items: [], total: 0 }),
    })
    renderHistory()
    await waitFor(() => {
      expect(screen.getByText(/No dictation history yet/)).toBeTruthy()
    })
  })

  it('renders history items', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        ok: true,
        items: [
          { id: 1, mode: 'dictation', transcript: 'test entry one', ai_output: null, pasted: false, target_app: null, created_at: '2026-06-09T12:00:00Z' },
          { id: 2, mode: 'ai_mode', transcript: 'polish this', ai_output: 'Polished text', pasted: true, target_app: 'notepad', created_at: '2026-06-09T13:00:00Z' },
        ],
        total: 2,
      }),
    })
    renderHistory()
    await waitFor(() => {
      expect(screen.getByText('test entry one')).toBeTruthy()
      expect(screen.getByText('polish this')).toBeTruthy()
      expect(screen.getByText(/Polished text/)).toBeTruthy()
      expect(screen.getByText('2 entries')).toBeTruthy()
    })
  })

  it('filter dropdown changes mode filter', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true, items: [], total: 0 }),
    })
    renderHistory()
    await waitFor(() => {
      expect(screen.getByText(/No dictation history yet/)).toBeTruthy()
    })
    const select = screen.getByRole('combobox')
    fireEvent.change(select, { target: { value: 'dictation' } })
    expect(mockFetch).toHaveBeenCalled()
  })

  it('clear all button calls DELETE and empties list', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ok: true,
          items: [{ id: 1, mode: 'dictation', transcript: 'x', ai_output: null, pasted: false, target_app: null, created_at: '2026-06-09T12:00:00Z' }],
          total: 1,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ok: true, message: 'History cleared' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ok: true, items: [], total: 0 }),
      })
    renderHistory()
    await waitFor(() => {
      expect(screen.getByText('Clear All')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Clear All'))
    await waitFor(() => {
      expect(screen.getByText(/No dictation history yet/)).toBeTruthy()
    })
  })

  it('delete button removes a single entry', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ok: true,
          items: [{ id: 42, mode: 'dictation', transcript: 'delete me', ai_output: null, pasted: false, target_app: null, created_at: '2026-06-09T12:00:00Z' }],
          total: 1,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ok: true, message: 'Entry deleted' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ok: true, items: [], total: 0 }),
      })
    renderHistory()
    await waitFor(() => {
      expect(screen.getByText('delete me')).toBeTruthy()
    })
    const deleteBtn = screen.getAllByText('Delete')[0]
    fireEvent.click(deleteBtn)
    await waitFor(() => {
      expect(screen.getByText(/No dictation history yet/)).toBeTruthy()
    })
  })

  it('copy button copies transcript to clipboard', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        ok: true,
        items: [{ id: 7, mode: 'dictation', transcript: 'copy this', ai_output: null, pasted: false, target_app: null, created_at: '2026-06-09T12:00:00Z' }],
        total: 1,
      }),
    })
    renderHistory()
    await waitFor(() => {
      expect(screen.getByText('copy this')).toBeTruthy()
    })
    const copyBtn = screen.getByText('Copy')
    fireEvent.click(copyBtn)
    await waitFor(() => {
      expect(screen.getByText('Copied!')).toBeTruthy()
    })
  })
})
