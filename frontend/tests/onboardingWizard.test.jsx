import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import OnboardingWizard from '../src/pages/OnboardingWizard'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

const mockCheckSetup = vi.fn()
const mockAgentStatus = vi.fn()
const mockWhisperDownload = vi.fn()
const mockSeedDemo = vi.fn()
const mockCompleteOnboarding = vi.fn()
const mockPlanAgentTask = vi.fn()

vi.mock('../src/api', () => ({
  api: {
    checkSetup: (...args) => mockCheckSetup(...args),
    agentStatus: (...args) => mockAgentStatus(...args),
    whisperDownloadModel: (...args) => mockWhisperDownload(...args),
    seedDemoData: (...args) => mockSeedDemo(...args),
    completeOnboarding: (...args) => mockCompleteOnboarding(...args),
    planAgentTask: (...args) => mockPlanAgentTask(...args),
    setAuthToken: vi.fn(),
  },
}))

function renderWizard() {
  return render(
    <MemoryRouter>
      <OnboardingWizard />
    </MemoryRouter>
  )
}

describe('OnboardingWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCheckSetup.mockResolvedValue({
      whisper_model_ready: false,
      whisper_cli_found: false,
      local_llm_reachable: false,
      agent_provider: 'mock',
      demo_data_seeded: false,
      onboarding_completed: false,
    })
  })

  it('shows loading state initially', () => {
    renderWizard()
    expect(screen.getByText('Checking system setup...')).toBeDefined()
  })

  it('renders welcome step after loading', async () => {
    renderWizard()
    await waitFor(() => {
      expect(screen.getByText('Welcome to OfficePilot AI')).toBeDefined()
    })
  })

  it('renders subtitle on welcome step', async () => {
    renderWizard()
    await waitFor(() => {
      expect(screen.getByText('Your Universal Voice Accountant Agent')).toBeDefined()
    })
  })

  it('shows feature list on welcome step', async () => {
    renderWizard()
    await waitFor(() => {
      expect(screen.getByText('Voice commands in any language')).toBeDefined()
      expect(screen.getByText('Excel automation & summaries')).toBeDefined()
      expect(screen.getByText('Local privacy-first processing')).toBeDefined()
      expect(screen.getByText('Record & replay workflows')).toBeDefined()
    })
  })

  it('shows Get Started button on step 0', async () => {
    renderWizard()
    await waitFor(() => {
      expect(screen.getByText('Get Started')).toBeDefined()
    })
  })

  it('advances to step 1 (whisper model) when Get Started clicked', async () => {
    renderWizard()
    await waitFor(() => { expect(screen.getByText('Get Started')).toBeDefined() })
    fireEvent.click(screen.getByText('Get Started'))
    await waitFor(() => {
      expect(screen.getByText('Voice Model Setup')).toBeDefined()
    })
  })

  it('shows download button when whisper model not ready', async () => {
    renderWizard()
    await waitFor(() => { expect(screen.getByText('Get Started')).toBeDefined() })
    fireEvent.click(screen.getByText('Get Started'))
    await waitFor(() => {
      expect(screen.getByText('Download Voice Model')).toBeDefined()
    })
  })

  it('shows voice model ready when model is present', async () => {
    mockCheckSetup.mockResolvedValue({
      whisper_model_ready: true,
      whisper_cli_found: true,
      local_llm_reachable: false,
      agent_provider: 'mock',
      demo_data_seeded: false,
      onboarding_completed: false,
    })
    renderWizard()
    await waitFor(() => { expect(screen.getByText('Get Started')).toBeDefined() })
    fireEvent.click(screen.getByText('Get Started'))
    await waitFor(() => {
      expect(screen.getByText('Voice model is ready')).toBeDefined()
      expect(screen.getByText('Whisper CLI detected')).toBeDefined()
    })
  })

  it('shows Local LLM step after voice model step', async () => {
    renderWizard()
    await waitFor(() => { expect(screen.getByText('Get Started')).toBeDefined() })
    fireEvent.click(screen.getByText('Get Started'))
    await waitFor(() => { expect(screen.getByText('Next')).toBeDefined() })
    fireEvent.click(screen.getByText('Next'))
    await waitFor(() => {
      expect(screen.getByText('Local LLM (Optional)')).toBeDefined()
    })
  })

  it('shows LLM endpoint config when toggle is on', async () => {
    renderWizard()
    await waitFor(() => { expect(screen.getByText('Get Started')).toBeDefined() })
    fireEvent.click(screen.getByText('Get Started'))
    await waitFor(() => { expect(screen.getByText('Next')).toBeDefined() })
    fireEvent.click(screen.getByText('Next'))
    await waitFor(() => { expect(screen.getByText('I want to use an offline LLM')).toBeDefined() })
    fireEvent.click(screen.getByText('I want to use an offline LLM'))
    await waitFor(() => {
      expect(screen.getByTestId('llm-endpoint-input')).toBeDefined()
    })
  })

  it('tests LLM connection when Test Connection clicked', async () => {
    mockAgentStatus.mockResolvedValue({ status: 'mock' })
    renderWizard()
    await waitFor(() => { expect(screen.getByText('Get Started')).toBeDefined() })
    fireEvent.click(screen.getByText('Get Started'))
    await waitFor(() => { expect(screen.getByText('Next')).toBeDefined() })
    fireEvent.click(screen.getByText('Next'))
    fireEvent.click(screen.getByText('I want to use an offline LLM'))
    await waitFor(() => { expect(screen.getByText('Test Connection')).toBeDefined() })
    fireEvent.click(screen.getByText('Test Connection'))
    await waitFor(() => {
      expect(mockAgentStatus).toHaveBeenCalled()
    })
  })

  async function goToStep(target) {
    // Start from step 0 (Welcome → "Get Started")
    await waitFor(() => { expect(screen.getByText('Get Started')).toBeDefined() })
    for (let s = 0; s < target; s++) {
      const label = s === 0 ? 'Get Started' : 'Next'
      fireEvent.click(screen.getByText(label))
      await waitFor(() => {})
    }
  }

  it('shows voice test step', async () => {
    renderWizard()
    await goToStep(3)
    await waitFor(() => {
      const headings = screen.getAllByText('Voice Test')
      expect(headings.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows summary on finish step', async () => {
    renderWizard()
    await goToStep(4)
    await waitFor(() => {
      expect(screen.getByText('You are ready!')).toBeDefined()
      expect(screen.getByText('Go to Dashboard')).toBeDefined()
    })
  })

  it('calls completeOnboarding and navigates on finish', async () => {
    mockCompleteOnboarding.mockResolvedValue({ ok: true })
    renderWizard()
    await goToStep(4)
    await waitFor(() => { expect(screen.getByText('Go to Dashboard')).toBeDefined() })
    fireEvent.click(screen.getByText('Go to Dashboard'))
    await waitFor(() => {
      expect(mockCompleteOnboarding).toHaveBeenCalled()
      expect(mockNavigate).toHaveBeenCalledWith('/app/agent', { replace: true })
    })
  })

  it('shows Back button on steps > 0', async () => {
    renderWizard()
    await waitFor(() => { expect(screen.getByText('Get Started')).toBeDefined() })
    fireEvent.click(screen.getByText('Get Started'))
    await waitFor(() => {
      expect(screen.getByText('Back')).toBeDefined()
    })
  })

  it('goes back when Back button clicked', async () => {
    renderWizard()
    await waitFor(() => { expect(screen.getByText('Get Started')).toBeDefined() })
    fireEvent.click(screen.getByText('Get Started'))
    await waitFor(() => { expect(screen.getByText('Next')).toBeDefined() })
    fireEvent.click(screen.getByText('Back'))
    await waitFor(() => {
      // Step 1 has "Voice Model Setup" — but after going back to step 0 we see Welcome
      expect(screen.getByText('Welcome to OfficePilot AI')).toBeDefined()
    })
  })
})
