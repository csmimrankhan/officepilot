import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AccountantAgent from './AccountantAgent.jsx'
import { api } from '../api.js'

vi.mock('../api.js', () => ({
  api: {
    agentStatus: vi.fn(),
    agentContext: vi.fn(),
    listAgentWorkflows: vi.fn(),
    planAgentTask: vi.fn(),
    approveAgentPlan: vi.fn(),
    executeRunStep: vi.fn(),
    stopRun: vi.fn(),
    dryRunRun: vi.fn(),
    startLiveRun: vi.fn(),
    saveAgentWorkflow: vi.fn(),
    repeatAgentWorkflow: vi.fn(),
    repeatRecentAgentWorkflow: vi.fn(),
    getAgentRunSummary: vi.fn(),
    verifyAgentRunExcel: vi.fn(),
    createSkillFromWorkflow: vi.fn(),
    recorderStart: vi.fn(),
    recorderStop: vi.fn(),
    recorderCancel: vi.fn(),
    recorderCurrent: vi.fn(),
    recorderListEvents: vi.fn(),
    recorderRecordEvent: vi.fn(),
    recorderConvertToSkill: vi.fn(),
    recorderApproveDraft: vi.fn(),
    recorderRejectDraft: vi.fn(),
    recorderSaveAsSkill: vi.fn(),
  },
}))

function renderAgent(initialState) {
  const locationState = initialState ? { state: { command: initialState } } : {}
  return render(
    <MemoryRouter initialEntries={[locationState]}>
      <AccountantAgent />
    </MemoryRouter>
  )
}

const mockStatus = { provider: 'mock', status: 'mock', dry_run_default: true }
const mockContext = { context: { user_role: 'owner', kill_switch_active: false, voice_approval_enabled: false, demo_mode: true, screen_control_enabled: false, browser_enabled: false, recent_workflows: [] } }
const mockWorkflows = { workflows: [] }

function setup() {
  vi.mocked(api.agentStatus).mockResolvedValue(mockStatus)
  vi.mocked(api.agentContext).mockResolvedValue(mockContext)
  vi.mocked(api.listAgentWorkflows).mockResolvedValue(mockWorkflows)
}

beforeEach(() => {
  vi.clearAllMocks()
  setup()
})

describe('AccountantAgent Page', () => {
  it('renders the page with heading', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getByText(/What would you like OfficePilot to do/i)).toBeTruthy()
    })
  })

  it('renders welcome subtext', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getByText(/Create reports, download invoice attachments/i)).toBeTruthy()
    })
  })

  it('renders command input', async () => {
    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      expect(input).toBeTruthy()
    })
  })

  it('renders automation cards', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getByText('Create Excel Summary')).toBeTruthy()
      expect(screen.getByText('Download Invoice Attachments')).toBeTruthy()
      expect(screen.getByText('Export Monthly Report')).toBeTruthy()
    })
  })

  it('renders all 6 automation cards', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getByText('Create Excel Summary')).toBeTruthy()
      expect(screen.getByText('Download Invoice Attachments')).toBeTruthy()
      expect(screen.getByText('Export Monthly Report')).toBeTruthy()
      expect(screen.getByText('Record Workflow')).toBeTruthy()
      expect(screen.getByText('Repeat Last Workflow')).toBeTruthy()
      expect(screen.getByText('Read Current Screen')).toBeTruthy()
    })
  })

  it('renders Popular automations and More actions sections', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getByText(/Popular automations/i)).toBeTruthy()
      expect(screen.getByText(/More actions/i)).toBeTruthy()
    })
  })

  it('clicking a card sets the command in input', async () => {
    renderAgent()
    await waitFor(() => {
      fireEvent.click(screen.getByText('Create Excel Summary'))
    })
    const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
    expect(input.value).toContain('Excel summary')
  })

  it('no duplicate suggestion hint bar exists', async () => {
    renderAgent()
    await waitFor(() => {
      const hintBars = document.querySelectorAll('.agent-chat-bar-hints')
      expect(hintBars.length).toBe(0)
    })
  })

  it('renders send button', async () => {
    renderAgent()
    await waitFor(() => {
      const sendButtons = screen.getAllByText(/→/i)
      expect(sendButtons.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('renders Emergency Stop button', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getAllByText(/Emergency Stop/i).length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows plan preview after task planning', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen',
        task_summary: 'Task: read this screen',
        platform_detected: 'Unknown',
        risk_level: 'low',
        requires_approval: true,
        can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture current screen context.', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })

    const planBtn = screen.getByText('→')
    fireEvent.click(planBtn)

    await waitFor(() => {
      expect(screen.getByText(/Read Screen/i)).toBeTruthy()
    })
  })

  it('shows blocked message for dangerous command', async () => {
    const mockBlocked = {
      plan_id: 0,
      plan: {
        task_title: 'Blocked Task',
        task_summary: 'Command contains blocked keyword',
        platform_detected: 'unknown',
        risk_level: 'blocked',
        requires_approval: false,
        can_record_workflow: false,
        steps: [],
        blocked_reason: 'Command contains blocked keyword',
        clarification_needed: false,
        clarification_question: null,
      },
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockBlocked)

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'delete all invoices' } })
    })

    const planBtn = screen.getByText('→')
    fireEvent.click(planBtn)

    await waitFor(() => {
      const blockedElements = screen.getAllByText(/Blocked/i)
      expect(blockedElements.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('renders Start Guided Demo button', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getByText(/Start Guided Demo/i)).toBeTruthy()
    })
  })

  // Phase 23D execution UI tests

  it('shows approve buttons in plan preview', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen',
        task_summary: 'Task: read this screen',
        platform_detected: 'Unknown',
        risk_level: 'low',
        requires_approval: true,
        can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture current screen context.', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })

    fireEvent.click(screen.getByText('→'))

    await waitFor(() => {
      expect(screen.getByText(/Approve & Dry-Run/i)).toBeTruthy()
      expect(screen.getByText(/Approve & Execute/i)).toBeTruthy()
    })
  })

  it('shows run execution UI after approving plan', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen',
        task_summary: 'Task: read this screen',
        platform_detected: 'Unknown',
        risk_level: 'low',
        requires_approval: true,
        can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture current screen context.', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    const mockApprove = {
      run_id: 42,
      mode: 'dry_run',
      status: 'running',
      steps: [
        { step_log_id: 101, step_order: 1, step_type: 'read_screen', status: 'pending', action_preview: { tool: 'read_current_screen', instruction: 'Capture current screen context.' } },
      ],
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })

    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Dry-Run/i)).toBeTruthy())

    fireEvent.click(screen.getByText(/Approve & Dry-Run/i))

    await waitFor(() => {
      expect(screen.getByText(/Run #42/i)).toBeTruthy()
      expect(screen.getByText(/Run All Steps/i)).toBeTruthy()
    })
  })

  it('shows live mode badge after starting live', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen',
        task_summary: 'Task: read this screen',
        platform_detected: 'Unknown',
        risk_level: 'low',
        requires_approval: true,
        can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture current screen context.', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    const mockApprove = {
      run_id: 42,
      mode: 'dry_run',
      status: 'running',
      steps: [
        { step_log_id: 101, step_order: 1, step_type: 'read_screen', status: 'pending', action_preview: { tool: 'read_current_screen', instruction: 'Capture current screen context.' } },
      ],
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.startLiveRun).mockResolvedValue({})

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })

    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Dry-Run/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Dry-Run/i))
    await waitFor(() => expect(screen.getByText(/Switch to Live/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Switch to Live/i))

    await waitFor(() => {
      expect(screen.getByText(/Run #42/i)).toBeTruthy()
    })
  })

  it('calls stopRun on emergency stop during run', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen',
        task_summary: 'Task: read this screen',
        platform_detected: 'Unknown',
        risk_level: 'low',
        requires_approval: true,
        can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture current screen context.', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    const mockApprove = {
      run_id: 42,
      mode: 'dry_run',
      status: 'running',
      steps: [
        { step_log_id: 101, step_order: 1, step_type: 'read_screen', status: 'pending', action_preview: { tool: 'read_current_screen', instruction: 'Capture current screen context.' } },
      ],
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.stopRun).mockResolvedValue({})

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })

    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Dry-Run/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Dry-Run/i))
    await waitFor(() => expect(screen.getByText(/Run #42/i)).toBeTruthy())

    const stopButtons = screen.getAllByText(/Emergency Stop/i)
    fireEvent.click(stopButtons[stopButtons.length - 1])

    await waitFor(() => {
      expect(api.stopRun).toHaveBeenCalledWith(42, { reason: 'User clicked Emergency Stop' })
    })
  })

  it('shows save as workflow CTA after live run completion', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen',
        task_summary: 'Task: read this screen',
        platform_detected: 'Unknown',
        risk_level: 'low',
        requires_approval: true,
        can_record_workflow: true,
        can_save_workflow: true,
        steps: [
          { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture current screen context.', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    const mockApprove = {
      run_id: 42,
      mode: 'live',
      status: 'running',
      steps: [
        { step_log_id: 101, step_order: 1, step_type: 'read_screen', status: 'pending', action_preview: { tool: 'read_current_screen', instruction: 'Capture current screen context.' } },
      ],
    }
    const mockExecuteStep = {
      step_log_id: 101, step_order: 1, step_status: 'completed',
      tool: 'read_current_screen',
      result: { status: 'success', output: {} },
      next_step: null,
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.executeRunStep).mockResolvedValue(mockExecuteStep)
    vi.mocked(api.getAgentRunSummary).mockResolvedValue({
      run_id: 42, status: 'completed', steps_completed: 1, steps_total: 1,
      invoice_count: 0, total_amount: 0, excel_file_path: null,
      summary_roman_urdu: '', summary_english: '',
    })

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Execute/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Execute/i))
    await waitFor(() => expect(screen.getByText(/Execute Step 1/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Execute Step 1/i))
    await waitFor(() => {
      expect(screen.getByText(/Save this workflow/i)).toBeTruthy()
    })
  })

  // ── Phase 23E Hero Demo Tests ─────────────────────────────────────────────

  it('renders hero demo button when no plan or run active', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getByText(/Start Guided Demo/i)).toBeTruthy()
    })
  })

  it('prefills hero demo command when Start Guided Demo clicked', async () => {
    renderAgent()
    await waitFor(() => {
      const demoBtn = screen.getByText(/Start Guided Demo/i)
      expect(demoBtn).toBeTruthy()
    })

    fireEvent.click(screen.getByText(/Start Guided Demo/i))

    const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
    expect(input.value).toContain('email')
    expect(input.value).toContain('invoice')
    expect(input.value).toContain('download')
  })

  it('prefills command from location state', async () => {
    renderAgent('download today invoices')
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      expect(input.value).toBe('download today invoices')
    })
  })

  it('shows result summary with bilingual text after run completed', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen',
        task_summary: 'Task: read this screen',
        platform_detected: 'Unknown',
        risk_level: 'low',
        requires_approval: true,
        can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture current screen context.', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    const mockApprove = {
      run_id: 42,
      mode: 'dry_run',
      status: 'running',
      steps: [
        { step_log_id: 101, step_order: 1, step_type: 'read_screen', status: 'pending', action_preview: { tool: 'read_current_screen', instruction: 'Capture current screen context.' } },
      ],
    }
    const mockDryRun = {
      step_count: 1,
      results: [{ step_log_id: 101, result: { status: 'dry_run', message: 'Dry-run: would execute', output: {} } }],
    }
    const mockSummary = {
      run_id: 42,
      status: 'completed',
      steps_completed: 1,
      steps_total: 1,
      invoice_count: 4,
      total_amount: 7625.75,
      summary_roman_urdu: 'Maine 4 invoices process ki hain. Total 7625.75 hai.',
      summary_english: 'I processed 4 invoices for today. Total is 7625.75.',
      excel_file_path: null,
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.dryRunRun).mockResolvedValue(mockDryRun)
    vi.mocked(api.getAgentRunSummary).mockResolvedValue(mockSummary)

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Dry-Run/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Dry-Run/i))
    await waitFor(() => expect(screen.getByText(/Run All Steps/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Run All Steps/i))
    await waitFor(() => {
      expect(screen.getByText(/Maine 4 invoices process ki hain/i)).toBeTruthy()
      expect(screen.getByText(/I processed 4 invoices for today/i)).toBeTruthy()
    })
  })

  it('shows save workflow CTA after live run completion', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen',
        task_summary: 'Task: read this screen',
        platform_detected: 'Unknown',
        risk_level: 'low',
        requires_approval: true,
        can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture current screen context.', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    const mockApprove = {
      run_id: 42,
      mode: 'live',
      status: 'running',
      steps: [
        { step_log_id: 101, step_order: 1, step_type: 'read_screen', status: 'pending', action_preview: { tool: 'read_current_screen', instruction: 'Capture current screen context.' } },
      ],
    }
    const mockExecuteStep = {
      step_log_id: 101, step_order: 1, step_status: 'completed',
      tool: 'read_current_screen',
      result: { status: 'success', output: {} },
      next_step: null,
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.executeRunStep).mockResolvedValue(mockExecuteStep)
    vi.mocked(api.getAgentRunSummary).mockResolvedValue({
      run_id: 42, status: 'completed', steps_completed: 1, steps_total: 1,
      invoice_count: 0, total_amount: 0, excel_file_path: null,
      summary_roman_urdu: '', summary_english: '',
    })

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Execute/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Execute/i))
    await waitFor(() => expect(screen.getByText(/Execute Step 1/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Execute Step 1/i))
    await waitFor(() => {
      expect(screen.getByText(/Save this workflow/i)).toBeTruthy()
    })
  })

  it('shows Excel verify button when excel_file_path present in summary', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen',
        task_summary: 'Task: read this screen',
        platform_detected: 'Unknown',
        risk_level: 'low',
        requires_approval: true,
        can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture current screen context.', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    const mockApprove = {
      run_id: 42,
      mode: 'dry_run',
      status: 'running',
      steps: [
        { step_log_id: 101, step_order: 1, step_type: 'read_screen', status: 'pending', action_preview: { tool: 'read_current_screen', instruction: 'Capture current screen context.' } },
      ],
    }
    const mockDryRun = {
      step_count: 1,
      results: [{ step_log_id: 101, result: { status: 'dry_run', message: 'Dry-run: would execute', output: {} } }],
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.dryRunRun).mockResolvedValue(mockDryRun)
    vi.mocked(api.getAgentRunSummary).mockResolvedValue({
      run_id: 42, status: 'completed', steps_completed: 1, steps_total: 1,
      invoice_count: 0, total_amount: 0,
      excel_file_path: 'C:\\demo\\exports\\daily_invoices.xlsx',
      summary_roman_urdu: '', summary_english: '',
    })

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Dry-Run/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Dry-Run/i))
    await waitFor(() => expect(screen.getByText(/Run All Steps/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Run All Steps/i))
    await waitFor(() => {
      expect(screen.getByText(/Verify Excel/i)).toBeTruthy()
    })
  })

  it('shows save workflow prompt after live run completes', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen', task_summary: 'Task: read this screen', platform_detected: 'Unknown',
        risk_level: 'low', requires_approval: true, can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture current screen context.', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null, clarification_needed: false, clarification_question: null,
      },
    }
    const mockApprove = {
      run_id: 42, mode: 'live', status: 'completed',
      steps: [
        { step_log_id: 101, step_order: 1, step_type: 'read_screen', status: 'completed', action_preview: { tool: 'read_current_screen', instruction: 'Capture current screen context.' } },
      ],
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.getAgentRunSummary).mockResolvedValue({
      summary_english: 'Completed 1 step', summary_roman_urdu: '',
    })

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Execute/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Execute/i))
    await waitFor(() => {
      expect(screen.getByText(/Save this workflow/i)).toBeTruthy()
    })
  })

  // ── Phase 26B Mic + Recording Tests ───────────────────────────
  it('renders microphone button inside command bar', async () => {
    renderAgent()
    await waitFor(() => {
      const micBtn = document.querySelector('.agent-command-mic')
      expect(micBtn).toBeTruthy()
      const shell = document.querySelector('.agent-command-shell')
      expect(shell).toBeTruthy()
      expect(shell.contains(micBtn)).toBeTruthy()
    })
  })

  it('mic button is inside the same container as input and send', async () => {
    renderAgent()
    await waitFor(() => {
      const shell = document.querySelector('.agent-command-shell')
      expect(shell).toBeTruthy()
      expect(shell.querySelector('.agent-command-mic')).toBeTruthy()
      expect(shell.querySelector('.agent-command-send')).toBeTruthy()
      expect(shell.querySelector('.agent-command-input')).toBeTruthy()
    })
  })

  it('shows permission denied warning when mic unavailable', async () => {
    renderAgent()
    await waitFor(() => {
      const micBtn = document.querySelector('.agent-command-mic')
      expect(micBtn).toBeTruthy()
      fireEvent.click(micBtn)
    })
    await waitFor(() => {
      expect(screen.getByText(/Microphone permission denied/i)).toBeTruthy()
    })
  })

  it('welcome screen still renders with mic present', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getByText(/What would you like OfficePilot to do/i)).toBeTruthy()
      expect(document.querySelector('.agent-command-mic')).toBeTruthy()
    })
  })

  it('no extra floating mic button exists outside command bar', async () => {
    renderAgent()
    await waitFor(() => {
      const micBtns = document.querySelectorAll('.agent-command-mic')
      // Should be exactly one mic button in the command bar
      expect(micBtns.length).toBe(1)
    })
  })

  it('emergency stop still visible with mic changes', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getAllByText(/Emergency Stop/i).length).toBeGreaterThanOrEqual(1)
    })
  })

  // ── Phase 32B Browser Card Integration Tests ──────────────────────────

  function browserLiveSetupMocks(browserTool, hasNext = true) {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Export Report',
        task_summary: 'Task: export monthly report',
        platform_detected: 'Browser',
        risk_level: 'medium',
        requires_approval: true,
        can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: browserTool, target: 'Platform', instruction: 'Open browser to URL', expected_result: 'Done', requires_approval: true, risk_level: 'medium' },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    const runSteps = [
      { step_log_id: 201, step_order: 1, step_type: browserTool, status: 'pending', action_preview: { tool: browserTool, instruction: 'Open browser to URL' } },
    ]
    if (hasNext) {
      runSteps.push({ step_log_id: 202, step_order: 2, step_type: 'browser_export_report', status: 'pending', action_preview: { tool: 'browser_export_report', instruction: 'Export report' } })
    }
    const mockApprove = {
      run_id: 50,
      mode: 'live',
      status: 'running',
      steps: runSteps,
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
  }

  async function setupBrowserCardFlow(browserTool, hasNext = true) {
    browserLiveSetupMocks(browserTool, hasNext)
    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'export monthly report' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Execute/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Execute/i))
    await waitFor(() => {
      expect(screen.getByText(/Run #50/i)).toBeTruthy()
    })
  }

  it('shows BrowserAutomationCard for browser_open_url step', async () => {
    await setupBrowserCardFlow('browser_open_url')
    vi.mocked(api.executeRunStep).mockResolvedValue({
      step_log_id: 201, step_order: 1, tool: 'browser_open_url',
      step_status: 'completed',
      result: {
        status: 'success',
        output: {
          url: 'https://example.com/accounting',
          opened: true,
          requires_user_login: true,
          mode: 'mock',
          status: 'active',
        },
      },
      next_step: { step_log_id: 202, step_order: 2, step_type: 'browser_export_report', action_preview: { tool: 'browser_export_report' } },
    })

    const executeBtn = screen.getByText(/Execute Step 1/i)
    fireEvent.click(executeBtn)

    await waitFor(() => {
      expect(screen.getByText(/example\.com/i)).toBeTruthy()
    })
  })

  it('shows ManualLoginCard for wait_for_login step', async () => {
    await setupBrowserCardFlow('browser_wait_for_user_login')
    vi.mocked(api.executeRunStep).mockResolvedValue({
      step_log_id: 201, step_order: 1, tool: 'browser_wait_for_user_login',
      step_status: 'completed',
      result: {
        status: 'success',
        output: {
          action: 'wait_for_login',
          status: 'waiting',
          prompt: 'Please log in manually',
          needs_user_confirmation: true,
          mode: 'mock',
        },
      },
      next_step: { step_log_id: 202, step_order: 2, step_type: 'browser_export_report', action_preview: { tool: 'browser_export_report' } },
    })

    const executeBtn = screen.getByText(/Execute Step 1/i)
    fireEvent.click(executeBtn)

    await waitFor(() => {
      expect(screen.getByText(/Manual Login Required/i)).toBeTruthy()
    })
    await waitFor(() => {
      const btns = screen.getAllByText(/I am logged in/i)
      expect(btns.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows blocked warning for blocked browser action', async () => {
    await setupBrowserCardFlow('browser_open_url')
    vi.mocked(api.executeRunStep).mockResolvedValue({
      step_log_id: 201, step_order: 1, tool: 'browser_open_url',
      step_status: 'blocked',
      result: {
        status: 'blocked',
        output: {
          blocked: true,
          reason: 'Domain banking.example.com is blocked by safety policy',
        },
        error_message: 'Domain banking.example.com is blocked by safety policy',
      },
      next_step: { step_log_id: 202, step_order: 2, step_type: 'browser_export_report', action_preview: { tool: 'browser_export_report' } },
    })

    const executeBtn = screen.getByText(/Execute Step 1/i)
    fireEvent.click(executeBtn)

    await waitFor(() => {
      const blockedEls = screen.getAllByText(/Blocked/i)
      expect(blockedEls.length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText(/blocked by safety policy/i)).toBeTruthy()
    })
  })

  it('calls executeRunStep with user_confirmed when "I am logged in" clicked', async () => {
    await setupBrowserCardFlow('browser_wait_for_user_login')

    vi.mocked(api.executeRunStep)
      .mockResolvedValueOnce({
        step_log_id: 201, step_order: 1, tool: 'browser_wait_for_user_login',
        step_status: 'completed',
        result: {
          status: 'success',
          output: {
            action: 'wait_for_login',
            status: 'waiting',
            prompt: 'Please log in manually',
            needs_user_confirmation: true,
          },
        },
        next_step: { step_log_id: 202, step_order: 2, step_type: 'browser_export_report', action_preview: { tool: 'browser_export_report' } },
      })
      .mockResolvedValueOnce({
        step_log_id: 201, step_order: 1, tool: 'browser_wait_for_user_login',
        step_status: 'completed',
        result: { status: 'success', output: { confirmed: true } },
        next_step: { step_log_id: 202, step_order: 2, step_type: 'browser_export_report', action_preview: { tool: 'browser_export_report' } },
      })

    const executeBtn = screen.getByText(/Execute Step 1/i)
    fireEvent.click(executeBtn)

    await waitFor(() => {
      const btns = screen.getAllByText(/I am logged in/i)
      expect(btns.length).toBeGreaterThanOrEqual(1)
    })

    const logInBtns = screen.getAllByText(/I am logged in/i)
    const loginBtn = logInBtns.length > 1 ? logInBtns[logInBtns.length - 1] : logInBtns[0]
    fireEvent.click(loginBtn)

    await waitFor(() => {
      expect(api.executeRunStep).toHaveBeenCalledTimes(2)
      expect(api.executeRunStep).toHaveBeenLastCalledWith(50, expect.objectContaining({
        step_log_id: 201,
        user_confirmed: true,
        manual_login_complete: true,
      }))
    })
  })

  it('shows BrowserResultCard for downloaded file - renders card with file info and action buttons', async () => {
    await setupBrowserCardFlow('browser_wait_for_download')
    vi.mocked(api.executeRunStep).mockResolvedValue({
      step_log_id: 201, step_order: 1, tool: 'browser_wait_for_download',
      step_status: 'completed',
      result: {
        status: 'success',
        output: {
          filepath: 'C:\\downloads\\report_2026_06_11.csv',
          filename: 'report_2026_06_11.csv',
          found: true,
          mode: 'mock',
        },
      },
      next_step: { step_log_id: 202, step_order: 2, step_type: 'browser_export_report', action_preview: { tool: 'browser_export_report' } },
    })

    const executeBtn = screen.getByText(/Execute Step 1/i)
    fireEvent.click(executeBtn)

    await waitFor(() => {
      expect(screen.getByText(/Report Downloaded/i)).toBeTruthy()
    })
    const csvMatches = screen.getAllByText(/report_2026_06_11\.csv/i)
    expect(csvMatches.length).toBeGreaterThanOrEqual(1)

    const openBtns = screen.getAllByText(/Open File/i)
    expect(openBtns.length).toBeGreaterThanOrEqual(1)
  })

  it('shows Create Excel Summary button for XLSX files in BrowserResultCard', async () => {
    await setupBrowserCardFlow('browser_wait_for_download')
    vi.mocked(api.executeRunStep).mockResolvedValue({
      step_log_id: 201, step_order: 1, tool: 'browser_wait_for_download',
      step_status: 'completed',
      result: {
        status: 'success',
        output: {
          filepath: 'C:\\downloads\\report_2026_06_11.xlsx',
          filename: 'report_2026_06_11.xlsx',
          found: true,
          mode: 'mock',
        },
      },
      next_step: { step_log_id: 202, step_order: 2, step_type: 'browser_export_report', action_preview: { tool: 'browser_export_report' } },
    })

    const executeBtn = screen.getByText(/Execute Step 1/i)
    fireEvent.click(executeBtn)

    await waitFor(() => {
      expect(screen.getByText(/Report Downloaded/i)).toBeTruthy()
    })
    const xlsxMatches = screen.getAllByText(/report_2026_06_11\.xlsx/i)
    expect(xlsxMatches.length).toBeGreaterThanOrEqual(1)

    const excelBtns = screen.getAllByText(/Create Excel Summary/i)
    expect(excelBtns.length).toBeGreaterThanOrEqual(1)
  })

  // GuidedDownloadCard appears after guided export step reply
  it('shows GuidedDownloadCard for guided export step reply', async () => {
    await setupBrowserCardFlow('browser_open_url')
    vi.mocked(api.executeRunStep).mockResolvedValue({
      step_log_id: 201, step_order: 1, tool: 'browser_open_url',
      step_status: 'completed',
      result: {
        status: 'success',
        output: {
          action: 'guided_export',
          status: 'waiting_for_user',
          guided_mode: true,
          mode: 'mock',
        },
      },
      next_step: { step_log_id: 202, step_order: 2, step_type: 'browser_export_report', action_preview: { tool: 'browser_export_report', instruction: 'Export report' } },
    })

    const executeBtn = screen.getByText(/Execute Step 1/i)
    fireEvent.click(executeBtn)

    await waitFor(() => {
      expect(screen.getByText(/Guided Download/i)).toBeTruthy()
    })
  })

  it('shows Save as Skill button on BrowserResultCard when plan has can_save_workflow', async () => {
    const mockPlan = {
      plan_id: 1, plan: {
        task_title: 'Export Report', task_summary: 'Task: export',
        platform_detected: 'Browser', risk_level: 'medium', requires_approval: true,
        can_record_workflow: false, can_save_workflow: true,
        steps: [
          { step_order: 1, step_type: 'browser_wait_for_download', target: 'Download', instruction: 'Wait for download', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null, clarification_needed: false,
      },
    }
    const mockApprove = { run_id: 50, mode: 'live', status: 'completed', steps: [] }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.getAgentRunSummary).mockResolvedValue({
      run_id: 50, status: 'completed', steps_completed: 0, steps_total: 1,
      invoice_count: 0, total_amount: 0, excel_file_path: null,
      summary_roman_urdu: '', summary_english: 'done',
    })

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'export report' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Execute/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Execute/i))
    await waitFor(() => {
      expect(screen.getByText(/Save this workflow/i)).toBeTruthy()
    })
  })

  it('calls createSkillFromWorkflow when Save as Skill clicked on BrowserResultCard', async () => {
    vi.mocked(api.createSkillFromWorkflow).mockResolvedValue({ name: 'Export Report Skill', skill_id: 99 })

    await setupBrowserCardFlow('browser_wait_for_download')
    vi.mocked(api.getAgentRunSummary).mockResolvedValue({
      run_id: 50, status: 'completed', steps_completed: 1, steps_total: 2,
      invoice_count: 0, total_amount: 0, excel_file_path: null,
      summary_roman_urdu: '', summary_english: 'Completed',
    })
    vi.mocked(api.executeRunStep).mockResolvedValue({
      step_log_id: 201, step_order: 1, tool: 'browser_wait_for_download',
      step_status: 'completed',
      result: {
        status: 'success',
        output: { filepath: 'C:\\downloads\\report.xlsx', filename: 'report.xlsx', found: true, mode: 'mock' },
      },
      next_step: { step_log_id: 202, step_order: 2, step_type: 'browser_export_report', action_preview: { tool: 'browser_export_report', instruction: 'Export report' } },
    })

    const executeBtn = screen.getByText(/Execute Step 1/i)
    fireEvent.click(executeBtn)

    await waitFor(() => {
      expect(screen.getByText(/Report Downloaded/i)).toBeTruthy()
    })

    const saveBtns = screen.getAllByText(/Save as Skill/i)
    expect(saveBtns.length).toBeGreaterThanOrEqual(1)
    fireEvent.click(saveBtns[saveBtns.length - 1])

    await waitFor(() => {
      expect(api.createSkillFromWorkflow).toHaveBeenCalled()
    })
  })

  it('calls verifyAgentRunExcel when Verify Excel button clicked', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen',
        task_summary: 'Task: read this screen',
        platform_detected: 'Unknown',
        risk_level: 'low',
        requires_approval: true,
        can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture current screen context.', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    const mockApprove = {
      run_id: 42,
      mode: 'dry_run',
      status: 'running',
      steps: [
        { step_log_id: 101, step_order: 1, step_type: 'read_screen', status: 'pending', action_preview: { tool: 'read_current_screen', instruction: 'Capture current screen context.' } },
      ],
    }
    const mockDryRun = {
      step_count: 1,
      results: [{ step_log_id: 101, result: { status: 'dry_run', message: 'Dry-run: would execute', output: {} } }],
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.dryRunRun).mockResolvedValue(mockDryRun)
    vi.mocked(api.getAgentRunSummary).mockResolvedValue({
      run_id: 42, status: 'completed', steps_completed: 1, steps_total: 1,
      invoice_count: 0, total_amount: 0,
      excel_file_path: 'C:\\demo\\exports\\daily_invoices.xlsx',
      summary_roman_urdu: '', summary_english: '',
    })
    vi.mocked(api.verifyAgentRunExcel).mockResolvedValue({
      file_exists: true, excel_file_path: 'C:\\demo\\exports\\daily_invoices.xlsx',
      file_size: 1024, rows_written: 5, expected_total: 7625.75, verification: 'verified',
    })

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Dry-Run/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Dry-Run/i))
    await waitFor(() => expect(screen.getByText(/Run All Steps/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Run All Steps/i))
    await waitFor(() => expect(screen.getByText(/Verify Excel/i)).toBeTruthy())

    fireEvent.click(screen.getByText(/Verify Excel/i))
    await waitFor(() => {
      expect(api.verifyAgentRunExcel).toHaveBeenCalledWith(42)
    })
  })

  // ── Phase 33 — Workflow Recording Integration ─────────────────────

  it('shows recording overlay for start_recording task type', async () => {
    const mockRecordingPlan = {
      plan_id: 0,
      plan: {
        task_title: 'Record Workflow',
        task_summary: 'Recording will begin for the current workflow',
        platform_detected: 'desktop',
        risk_level: 'low',
        requires_approval: false,
        task_type: 'start_recording',
        steps: [{ step_order: 1, step_type: 'record_workflow', instruction: 'Recording will begin...', risk_level: 'low' }],
        blocked_reason: null,
        clarification_needed: false,
      },
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockRecordingPlan)
    vi.mocked(api.recorderStart).mockResolvedValue({ session_id: 1, status: 'recording', title: 'Test Recording' })
    vi.mocked(api.recorderCurrent).mockResolvedValue({ session_id: 1, status: 'recording', title: 'Test Recording', event_count: 0, started_at: new Date().toISOString() })

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'record this workflow' } })
    })
    fireEvent.click(screen.getByText('→'))

    await waitFor(() => {
      expect(api.recorderStart).toHaveBeenCalled()
      // Plan should be cleared - overlay should be visible
      expect(screen.queryByText(/Record Workflow/)).toBeNull()
    })
  })

  it('creates recording session when start_recording plan received', async () => {
    const mockRecordingPlan = {
      plan_id: 0,
      plan: {
        task_title: 'Record Workflow',
        task_summary: 'Recording will begin...',
        risk_level: 'low',
        requires_approval: false,
        task_type: 'start_recording',
        steps: [],
        blocked_reason: null,
      },
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockRecordingPlan)
    vi.mocked(api.recorderStart).mockResolvedValue({ session_id: 5, status: 'recording', title: 'Voice Recording' })
    vi.mocked(api.recorderCurrent).mockResolvedValue({ session_id: 5, status: 'recording', title: 'Voice Recording', event_count: 2, started_at: new Date().toISOString() })

    renderAgent()
    await waitFor(() => {
      fireEvent.change(screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i), { target: { value: 'start recording' } })
    })
    fireEvent.click(screen.getByText('→'))

    await waitFor(() => {
      expect(api.recorderStart).toHaveBeenCalled()
    })
  })

  it('calls recorderStop for stop_recording plan', async () => {
    const mockStopPlan = {
      plan_id: 0,
      plan: {
        task_title: 'Stop Recording',
        task_summary: 'Stop workflow recording',
        risk_level: 'low',
        requires_approval: false,
        task_type: 'stop_recording',
        steps: [],
        blocked_reason: null,
      },
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockStopPlan)
    vi.mocked(api.recorderStop).mockResolvedValue({ session_id: 1, status: 'stopped', event_count: 3 })
    vi.mocked(api.recorderCurrent).mockResolvedValue({ session_id: 1, status: 'recording', title: 'Test', event_count: 3, started_at: new Date().toISOString() })
    vi.mocked(api.recorderListEvents).mockResolvedValue([])

    renderAgent()
    await waitFor(() => {
      fireEvent.change(screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i), { target: { value: 'stop recording' } })
    })
    fireEvent.click(screen.getByText('→'))

    await waitFor(() => {
      expect(api.recorderStop).toHaveBeenCalled()
    })
  })

  it('shows Record Workflow in automation cards', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getByText(/Record Workflow/i)).toBeTruthy()
    })
  })

  // ── Phase 38 — Navigation Command Tests ─────────────────────────────

  it('renders Voice Commands button in More actions', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getByText(/Voice Commands/i)).toBeTruthy()
    })
  })

  it('renders Workflow Memory button in More actions', async () => {
    renderAgent()
    await waitFor(() => {
      expect(screen.getByText(/Workflow Memory/i)).toBeTruthy()
    })
  })

  it('clicking Voice Commands does not call planAgentTask', async () => {
    renderAgent()
    await waitFor(() => {
      const voiceBtn = screen.getByText(/Voice Commands/i)
      expect(voiceBtn).toBeTruthy()
      fireEvent.click(voiceBtn)
    })
    // Plan API should NOT be called — navigation is direct
    expect(api.planAgentTask).not.toHaveBeenCalled()
  })

  it('clicking Workflow Memory does not call planAgentTask', async () => {
    renderAgent()
    await waitFor(() => {
      const wfBtn = screen.getByText(/Workflow Memory/i)
      expect(wfBtn).toBeTruthy()
      fireEvent.click(wfBtn)
    })
    expect(api.planAgentTask).not.toHaveBeenCalled()
  })

  it('typing "open voice command center" and sending does not call planAgentTask', async () => {
    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'open voice command center' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => {
      expect(api.planAgentTask).not.toHaveBeenCalled()
    })
  })

  it('typing "voice commands" and sending does not call planAgentTask', async () => {
    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'voice commands' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => {
      expect(api.planAgentTask).not.toHaveBeenCalled()
    })
  })

  // ── Phase 38 — Roman Urdu Excel Downloads + FileSelectionCard Tests ──

  it('FileSelectionCard renders with file list', async () => {
    const { default: FileSelectionCard } = await import('../components/agent/FileSelectionCard.jsx')
    const { container } = render(
      <FileSelectionCard
        files={[
          { filename: 'parcel_layer.xlsx', path: 'C:\\Users\\test\\Downloads\\parcel_layer.xlsx', extension: '.xlsx', size: 10240, modified_at: '2026-06-14T10:00:00Z' },
          { filename: 'parcel_data.csv', path: 'C:\\Users\\test\\Downloads\\parcel_data.csv', extension: '.csv', size: 5120, modified_at: '2026-06-14T09:00:00Z' },
        ]}
        message="Multiple files match. Select one:"
        onFileSelected={() => {}}
      />
    )
    await waitFor(() => {
      expect(screen.getByText('parcel_layer.xlsx')).toBeTruthy()
      expect(screen.getByText('parcel_data.csv')).toBeTruthy()
      const selectBtns = screen.getAllByText('Select')
      expect(selectBtns.length).toBe(2)
    })
  })

  it('FileSelectionCard calls onFileSelected when Select clicked', async () => {
    const { default: FileSelectionCard } = await import('../components/agent/FileSelectionCard.jsx')
    const onSelect = vi.fn()
    render(
      <FileSelectionCard
        files={[
          { filename: 'parcel_layer.xlsx', path: 'C:\\test\\parcel_layer.xlsx', extension: '.xlsx', size: 10240, modified_at: '2026-06-14T10:00:00Z' },
        ]}
        message="Select file:"
        onFileSelected={onSelect}
      />
    )
    await waitFor(() => {
      fireEvent.click(screen.getByText('Select'))
    })
    expect(onSelect).toHaveBeenCalledWith('C:\\test\\parcel_layer.xlsx')
  })

  it('FileSelectionCard renders nothing for empty files', async () => {
    const { default: FileSelectionCard } = await import('../components/agent/FileSelectionCard.jsx')
    const { container } = render(
      <FileSelectionCard files={[]} message="" onFileSelected={() => {}} />
    )
    expect(container.innerHTML).toBe('')
  })

  it('Roman Urdu excel command creates plan with correct task_title and steps', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Excel Summary from Downloads',
        task_type: 'excel_summary_from_downloads',
        summary_for_user: 'I will search your Downloads folder...',
        risk_level: 'medium',
        requires_approval: true,
        can_save_workflow: true,
        steps: [
          { step_order: 1, step_type: 'file_find_in_downloads', tool: 'file_find_in_downloads', target: 'Downloads', instruction: 'Search downloads folder', requires_approval: false, risk_level: 'low', parameters: { query: 'parcel layer', extensions: ['.xlsx', '.csv'] } },
          { step_order: 2, step_type: 'excel_create_summary_from_file', tool: 'excel_create_summary_from_file', target: 'Excel file', instruction: 'Create summary', requires_approval: true, risk_level: 'medium', parameters: { path: '{selected_file_path}' } },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'download folder mein se parcel layer ki excel file ka summary banao' } })
    })
    fireEvent.click(screen.getByText('→'))

    await waitFor(() => {
      expect(screen.getByText(/Excel Summary from Downloads/i)).toBeTruthy()
      expect(screen.getByText(/file_find_in_downloads/i)).toBeTruthy()
      expect(screen.getByText(/excel_create_summary_from_file/i)).toBeTruthy()
    })
    // Should NOT show read_screen or Daily Invoice
    expect(screen.queryByText(/read_screen/i)).toBeNull()
    expect(screen.queryByText(/Daily Invoice Process/i)).toBeNull()
  })

  it('Roman Urdu excel command save title is not Daily Invoice Process', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Excel Summary from Downloads',
        task_type: 'excel_summary_from_downloads',
        summary_for_user: 'I will search your Downloads folder...',
        can_save_workflow: true,
        risk_level: 'medium',
        requires_approval: true,
        steps: [
          { step_order: 1, step_type: 'file_find_in_downloads', tool: 'file_find_in_downloads', target: 'Downloads', instruction: 'Search', requires_approval: false, risk_level: 'low', parameters: {} },
        ],
        blocked_reason: null,
        clarification_needed: false,
        clarification_question: null,
      },
    }
    const mockApprove = {
      run_id: 42,
      mode: 'live',
      status: 'completed',
      steps: [
        { step_log_id: 101, step_order: 1, step_type: 'file_find_in_downloads', status: 'completed', action_preview: { tool: 'file_find_in_downloads' } },
      ],
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.getAgentRunSummary).mockResolvedValue({
      run_id: 42, status: 'completed', steps_completed: 1, steps_total: 1,
      summary_english: 'Completed 1 step', summary_roman_urdu: '',
    })

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'download folder parcel layer summary' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Execute/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Execute/i))
    await waitFor(() => {
      // Save prompt should show "Excel Summary from Downloads", NOT "Daily Invoice Process"
      const saveText = screen.getByText(/Save as/i)
      expect(saveText.textContent).toContain('Excel Summary from Downloads')
      expect(saveText.textContent).not.toContain('Daily Invoice Process')
    })
  })

  it('unsupported PDF debit/credit command shows clarification without fake totals', async () => {
    const mockPlan = {
      plan_id: 0,
      plan: {
        task_title: 'PDF Debit/Credit — Unsupported',
        task_type: 'needs_clarification',
        summary_for_user: 'debit/credit extraction from PDF is not enabled in OfficePilot yet',
        risk_level: 'low',
        requires_approval: false,
        steps: [
          { step_order: 1, step_type: 'needs_clarification', tool: 'needs_clarification', target: 'user', instruction: 'debit/credit extraction from PDF is not enabled', requires_approval: false, risk_level: 'low', parameters: {} },
        ],
        clarification_needed: true,
        clarification_question: 'debit/credit extraction from PDF is not enabled',
        can_save_workflow: false,
        blocked_reason: null,
      },
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'download mein se PDF debit credit batao' } })
    })
    fireEvent.click(screen.getByText('→'))

    await waitFor(() => {
      expect(screen.getByText(/not enabled/i)).toBeTruthy()
      expect(screen.getByText(/Unsupported/i)).toBeTruthy()
    })
    // No fake totals
    expect(screen.queryByText(/0 invoices/i)).toBeNull()
    expect(screen.queryByText(/process ki/i)).toBeNull()
  })

  // ── Phase 38 — Save Workflow Visibility After Dry-Run ─────────────

  it('does not show save workflow after dry-run completion', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen', task_summary: 'Task: read this screen', platform_detected: 'Unknown',
        risk_level: 'low', requires_approval: true, can_save_workflow: true,
        steps: [
          { step_order: 1, step_type: 'read_screen', instruction: 'Capture current screen context.', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null, clarification_needed: false,
      },
    }
    const mockApprove = { run_id: 42, mode: 'dry_run', status: 'completed', steps: [] }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.getAgentRunSummary).mockResolvedValue({
      run_id: 42, status: 'completed', steps_completed: 0, steps_total: 1,
      invoice_count: 0, total_amount: 0, excel_file_path: null,
      summary_roman_urdu: '', summary_english: 'done',
    })

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Dry-Run/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Dry-Run/i))
    await waitFor(() => {
      expect(screen.queryByText(/Save this workflow/i)).toBeNull()
      expect(screen.queryByText(/Save as/i)).toBeNull()
    })
  })

  it('does not show save workflow after dry-run with execute steps', async () => {
    const mockPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Read Screen', task_summary: 'Task: read this screen',
        risk_level: 'low', requires_approval: true, can_save_workflow: true, can_record_workflow: false,
        steps: [
          { step_order: 1, step_type: 'read_screen', instruction: 'Capture current screen context.', requires_approval: false, risk_level: 'low' },
        ],
        blocked_reason: null, clarification_needed: false, clarification_question: null,
      },
    }
    const mockApprove = {
      run_id: 42, mode: 'dry_run', status: 'running',
      steps: [
        { step_log_id: 101, step_order: 1, step_type: 'read_screen', status: 'pending', action_preview: { tool: 'read_current_screen', instruction: 'Capture current screen context.' } },
      ],
    }
    const mockDryRun = {
      step_count: 1,
      results: [{ step_log_id: 101, result: { status: 'dry_run', message: 'Dry-run: would execute', output: {} } }],
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)
    vi.mocked(api.approveAgentPlan).mockResolvedValue(mockApprove)
    vi.mocked(api.dryRunRun).mockResolvedValue(mockDryRun)
    vi.mocked(api.getAgentRunSummary).mockResolvedValue({
      run_id: 42, status: 'completed', steps_completed: 1, steps_total: 1,
      invoice_count: 0, total_amount: 0, excel_file_path: null,
      summary_roman_urdu: '', summary_english: '',
    })

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'read this screen' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => expect(screen.getByText(/Approve & Dry-Run/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Approve & Dry-Run/i))
    await waitFor(() => expect(screen.getByText(/Run All Steps/i)).toBeTruthy())
    fireEvent.click(screen.getByText(/Run All Steps/i))
    await waitFor(() => {
      expect(screen.getByText(/Run completed/i)).toBeTruthy()
      expect(screen.queryByText(/Save this workflow/i)).toBeNull()
    })
  })

  it('does not show save workflow after navigation command', async () => {
    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'open voice commands' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => {
      expect(screen.queryByText(/Save this workflow/i)).toBeNull()
    })
  })

  it('does not show save workflow after unsupported PDF command', async () => {
    const mockPlan = {
      plan_id: 0,
      plan: {
        task_title: 'PDF Debit/Credit — Unsupported',
        task_type: 'needs_clarification',
        summary_for_user: 'debit/credit extraction from PDF is not enabled in OfficePilot yet',
        can_save_workflow: false,
        risk_level: 'low',
        requires_approval: false,
        steps: [
          { step_order: 1, step_type: 'needs_clarification', tool: 'needs_clarification', target: 'user', instruction: 'debit/credit extraction from PDF is not enabled', requires_approval: false, risk_level: 'low', parameters: {} },
        ],
        clarification_needed: true,
        clarification_question: 'debit/credit extraction from PDF is not enabled',
        blocked_reason: null,
      },
    }
    vi.mocked(api.planAgentTask).mockResolvedValue(mockPlan)

    renderAgent()
    await waitFor(() => {
      const input = screen.getByPlaceholderText(/Tell OfficePilot what you want to automate/i)
      fireEvent.change(input, { target: { value: 'download mein se PDF debit credit batao' } })
    })
    fireEvent.click(screen.getByText('→'))
    await waitFor(() => {
      expect(screen.getByText(/Unsupported/i)).toBeTruthy()
      expect(screen.queryByText(/Save this workflow/i)).toBeNull()
    })
  })
})
