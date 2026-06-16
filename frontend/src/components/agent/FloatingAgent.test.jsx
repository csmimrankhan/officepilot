import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TrayFloatingAgent from './TrayFloatingAgent.jsx'
import AgentModeSwitcher from './AgentModeSwitcher.jsx'
import AgentPlanCard from './AgentPlanCard.jsx'
import AgentApprovalCard from './AgentApprovalCard.jsx'
import AgentProgressTimeline from './AgentProgressTimeline.jsx'
import AgentResultCard from './AgentResultCard.jsx'
import WorkflowMemoryQuickList from './WorkflowMemoryQuickList.jsx'
import { api } from '../../api.js'

vi.mock('../../api.js', () => ({
  api: {
    agentStatus: vi.fn(),
    getAgentMode: vi.fn(),
    setAgentMode: vi.fn(),
    getCurrentTask: vi.fn(),
    getCurrentRun: vi.fn(),
    listAgentWorkflows: vi.fn(),
    planAgentTask: vi.fn(),
    approveAgentPlan: vi.fn(),
    dryRunRun: vi.fn(),
    startLiveRun: vi.fn(),
    emergencyStopAgent: vi.fn(),
    saveAgentWorkflow: vi.fn(),
    repeatAgentWorkflow: vi.fn(),
    replayYesterday: vi.fn(),
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    getAgentRunSummary: vi.fn(),
    pnlCompareDemo: vi.fn(),
    pnlCompareUploaded: vi.fn(),
    listPnlRuns: vi.fn(),
    getPnlRun: vi.fn(),
  },
}))

const mockStatus = { provider: 'mock', status: 'mock', dry_run_default: true }
const mockMode = { mode: 'plan' }
const mockWorkflows = { workflows: [] }

function setup() {
  vi.mocked(api.agentStatus).mockResolvedValue(mockStatus)
  vi.mocked(api.getAgentMode).mockResolvedValue(mockMode)
  vi.mocked(api.listAgentWorkflows).mockResolvedValue(mockWorkflows)
}

beforeEach(() => {
  vi.clearAllMocks()
  setup()
})

describe('TrayFloatingAgent', () => {
  it('renders the floating toggle button', () => {
    render(<MemoryRouter><TrayFloatingAgent /></MemoryRouter>)
    expect(screen.getByTitle(/Open Accountant Agent/i)).toBeTruthy()
  })

  it('opens floating window when toggle clicked', async () => {
    render(<MemoryRouter><TrayFloatingAgent /></MemoryRouter>)
    const toggle = screen.getByTitle(/Open Accountant Agent/i)
    fireEvent.click(toggle)
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Ask your Accountant Agent/i)).toBeTruthy()
    })
  })

  it('shows mode indicator in floating window', async () => {
    render(<MemoryRouter><TrayFloatingAgent /></MemoryRouter>)
    fireEvent.click(screen.getByTitle(/Open Accountant Agent/i))
    await waitFor(() => {
      expect(screen.getByText(/Mode:/i)).toBeTruthy()
    })
  })

  it('shows emergency stop button in header', async () => {
    render(<MemoryRouter><TrayFloatingAgent /></MemoryRouter>)
    fireEvent.click(screen.getByTitle(/Open Accountant Agent/i))
    await waitFor(() => {
      expect(screen.getByTitle(/Emergency Stop/i)).toBeTruthy()
    })
  })

  it('calls emergencyStopAgent when emergency stop clicked', async () => {
    vi.mocked(api.emergencyStopAgent).mockResolvedValue({ ok: true, stopped_count: 1 })
    render(<MemoryRouter><TrayFloatingAgent /></MemoryRouter>)
    fireEvent.click(screen.getByTitle(/Open Accountant Agent/i))
    await waitFor(() => {
      expect(screen.getByTitle(/Emergency Stop/i)).toBeTruthy()
    })
    fireEvent.click(screen.getByTitle(/Emergency Stop/i))
    await waitFor(() => {
      expect(api.emergencyStopAgent).toHaveBeenCalled()
    })
  })

  it('sends a command and shows response', async () => {
    vi.mocked(api.planAgentTask).mockResolvedValue({
      plan_id: 1,
      plan: {
        task_title: 'Read Screen',
        task_summary: 'Read the current screen',
        risk_level: 'low',
        requires_approval: true,
        steps: [{ step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture context', expected_result: 'Done', requires_approval: false, risk_level: 'low' }],
        blocked_reason: null, clarification_needed: false, can_save_workflow: false,
      },
      voice_reply_text: 'Plan ready. Risk level: low.',
    })

    render(<MemoryRouter><TrayFloatingAgent /></MemoryRouter>)
    fireEvent.click(screen.getByTitle(/Open Accountant Agent/i))
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Ask your Accountant Agent/i)).toBeTruthy()
    })

    const input = screen.getByPlaceholderText(/Ask your Accountant Agent/i)
    fireEvent.change(input, { target: { value: 'read this screen' } })
    fireEvent.click(screen.getByText(/Send/i))

    await waitFor(() => {
      expect(api.planAgentTask).toHaveBeenCalledWith({ command: 'read this screen' })
    })
  })

  it('handles emergency stop command via text input', async () => {
    vi.mocked(api.emergencyStopAgent).mockResolvedValue({ ok: true, stopped_count: 1 })

    render(<MemoryRouter><TrayFloatingAgent /></MemoryRouter>)
    fireEvent.click(screen.getByTitle(/Open Accountant Agent/i))
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Ask your Accountant Agent/i)).toBeTruthy()
    })

    const input = screen.getByPlaceholderText(/Ask your Accountant Agent/i)
    fireEvent.change(input, { target: { value: 'emergency stop' } })
    fireEvent.click(screen.getByText(/Send/i))

    await waitFor(() => {
      expect(api.emergencyStopAgent).toHaveBeenCalledWith({ reason: 'User command' })
    })
  })
})

describe('AgentModeSwitcher', () => {
  it('renders all 4 mode buttons', () => {
    render(<AgentModeSwitcher currentMode="plan" onModeChange={() => {}} />)
    expect(screen.getByText('Plan')).toBeTruthy()
    expect(screen.getByText('Work')).toBeTruthy()
    expect(screen.getByText('Record')).toBeTruthy()
    expect(screen.getByText('Replay')).toBeTruthy()
  })

  it('highlights active mode', () => {
    render(<AgentModeSwitcher currentMode="work" onModeChange={() => {}} />)
    const btn = screen.getByText('Work').closest('button')
    expect(btn.className).toContain('active')
    expect(btn.className).toContain('work')
  })

  it('calls onModeChange when clicked', () => {
    const onChange = vi.fn()
    render(<AgentModeSwitcher currentMode="plan" onModeChange={onChange} />)
    fireEvent.click(screen.getByText('Record'))
    expect(onChange).toHaveBeenCalledWith('record')
  })
})

describe('AgentPlanCard', () => {
  const mockPlan = {
    plan_id: 1,
    plan: {
      task_title: 'Read Screen',
      task_summary: 'Capture current screen context.',
      risk_level: 'low',
      requires_approval: true,
      steps: [
        { step_order: 1, step_type: 'read_screen', target: 'screen', instruction: 'Capture screenshot', expected_result: 'Done', requires_approval: false, risk_level: 'low' },
      ],
      blocked_reason: null, clarification_needed: false, can_save_workflow: false,
    },
  }

  it('renders plan title and risk badge', () => {
    render(<AgentPlanCard plan={mockPlan} />)
    expect(screen.getByText('Read Screen')).toBeTruthy()
    expect(screen.getByText('low')).toBeTruthy()
  })

  it('renders steps', () => {
    render(<AgentPlanCard plan={mockPlan} />)
    expect(screen.getByText(/read_screen/)).toBeTruthy()
    expect(screen.getByText(/Capture screenshot/)).toBeTruthy()
    expect(screen.getByText('1')).toBeTruthy()
  })

  it('renders blocked message when blocked', () => {
    const blockedPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Blocked Task',
        task_summary: '',
        risk_level: 'blocked',
        blocked_reason: 'Task contains dangerous command.',
        clarification_needed: false, steps: [],
      },
    }
    render(<AgentPlanCard plan={blockedPlan} />)
    expect(screen.getByText(/Task contains dangerous command/)).toBeTruthy()
  })

  it('renders clarification when needed', () => {
    const clarifyPlan = {
      plan_id: 1,
      plan: {
        task_title: 'Unclear Task',
        task_summary: '',
        risk_level: 'low',
        clarification_needed: true,
        clarification_question: 'Which invoices?',
        blocked_reason: null, steps: [],
      },
    }
    render(<AgentPlanCard plan={clarifyPlan} />)
    expect(screen.getByText(/Which invoices/)).toBeTruthy()
  })
})

describe('AgentApprovalCard', () => {
  it('renders approve and reject buttons', () => {
    render(<AgentApprovalCard planId={1} onApprove={() => {}} onReject={() => {}} loading={false} />)
    expect(screen.getByText(/Approve \(Dry-Run\)/i)).toBeTruthy()
    expect(screen.getByText(/Approve & Execute/i)).toBeTruthy()
    expect(screen.getByText(/Reject/i)).toBeTruthy()
  })

  it('calls onApprove with dry_run mode', () => {
    const onApprove = vi.fn()
    render(<AgentApprovalCard planId={42} onApprove={onApprove} onReject={() => {}} loading={false} />)
    fireEvent.click(screen.getByText(/Approve \(Dry-Run\)/i))
    expect(onApprove).toHaveBeenCalledWith(42, 'dry_run')
  })

  it('calls onApprove with live mode', () => {
    const onApprove = vi.fn()
    render(<AgentApprovalCard planId={42} onApprove={onApprove} onReject={() => {}} loading={false} />)
    fireEvent.click(screen.getByText(/Approve & Execute/i))
    expect(onApprove).toHaveBeenCalledWith(42, 'live')
  })

  it('calls onReject when reject clicked', () => {
    const onReject = vi.fn()
    render(<AgentApprovalCard planId={1} onApprove={() => {}} onReject={onReject} loading={false} />)
    fireEvent.click(screen.getByText(/Reject/i))
    expect(onReject).toHaveBeenCalledWith(1)
  })
})

describe('AgentProgressTimeline', () => {
  const mockRun = {
    run_id: 1,
    mode: 'dry_run',
    status: 'running',
    steps: [
      { step_log_id: 101, step_order: 1, step_type: 'read_screen', status: 'pending' },
      { step_log_id: 102, step_order: 2, step_type: 'extract_data', status: 'pending' },
    ],
  }

  it('renders run mode and status', () => {
    render(<AgentProgressTimeline run={mockRun} onDryRun={() => {}} onStartLive={() => {}} onEmergencyStop={() => {}} loading={false} />)
    expect(screen.getByText(/DRY_RUN/)).toBeTruthy()
    expect(screen.getByText(/RUNNING/)).toBeTruthy()
  })

  it('renders step list', () => {
    render(<AgentProgressTimeline run={mockRun} onDryRun={() => {}} onStartLive={() => {}} onEmergencyStop={() => {}} loading={false} />)
    expect(screen.getByText(/read_screen/)).toBeTruthy()
    expect(screen.getByText(/extract_data/)).toBeTruthy()
    expect(screen.getByText(/2 steps/)).toBeTruthy()
  })

  it('shows Dry-Run button for dry_run mode', () => {
    render(<AgentProgressTimeline run={mockRun} onDryRun={() => {}} onStartLive={() => {}} onEmergencyStop={() => {}} loading={false} />)
    expect(screen.getByText(/Run All Steps \(Dry-Run\)/i)).toBeTruthy()
  })

  it('shows emergency stop button always', () => {
    render(<AgentProgressTimeline run={mockRun} onDryRun={() => {}} onStartLive={() => {}} onEmergencyStop={() => {}} loading={false} />)
    expect(screen.getByText(/Emergency Stop/i)).toBeTruthy()
  })

  it('calls onDryRun when dry-run clicked', () => {
    const onDryRun = vi.fn()
    render(<AgentProgressTimeline run={mockRun} onDryRun={onDryRun} onStartLive={() => {}} onEmergencyStop={() => {}} loading={false} />)
    fireEvent.click(screen.getByText(/Run All Steps \(Dry-Run\)/i))
    expect(onDryRun).toHaveBeenCalledWith(1)
  })

  it('calls onEmergencyStop when emergency stop clicked', () => {
    const onEmergency = vi.fn()
    render(<AgentProgressTimeline run={mockRun} onDryRun={() => {}} onStartLive={() => {}} onEmergencyStop={onEmergency} loading={false} />)
    fireEvent.click(screen.getByText(/Emergency Stop/i))
    expect(onEmergency).toHaveBeenCalled()
  })
})

describe('AgentResultCard', () => {
  const mockSummary = {
    run_id: 1, status: 'completed', steps_completed: 3, steps_total: 3,
    invoice_count: 4, total_amount: 7625.75,
    excel_file_path: 'C:\\exports\\invoices.xlsx',
    summary_english: 'I processed 4 invoices for today. Total is 7625.75.',
    summary_roman_urdu: 'Maine aaj ki 4 invoices process ki hain. Total 7625.75 hai.',
  }

  it('renders success message', () => {
    render(<AgentResultCard summary={mockSummary} />)
    expect(screen.getByText(/Task Complete/i)).toBeTruthy()
  })

  it('renders English summary', () => {
    render(<AgentResultCard summary={mockSummary} />)
    expect(screen.getByText(/I processed 4 invoices for today/)).toBeTruthy()
  })

  it('renders Roman Urdu summary', () => {
    render(<AgentResultCard summary={mockSummary} />)
    expect(screen.getByText(/Maine aaj ki 4 invoices/)).toBeTruthy()
  })

  it('renders invoice count and total', () => {
    render(<AgentResultCard summary={mockSummary} />)
    const totals = screen.getAllByText(/7625\.75/)
    expect(totals.length).toBe(3)
    expect(screen.getByText(/Invoices:/i)).toBeTruthy()
  })

  it('renders excel file path', () => {
    render(<AgentResultCard summary={mockSummary} />)
    expect(screen.getByText(/invoices.xlsx/)).toBeTruthy()
  })
})

describe('WorkflowMemoryQuickList', () => {
  const workflows = [
    { id: 1, workflow_name: 'Daily Invoice Process', workflow_description: 'Auto invoice', platform_hint: 'Excel', run_count: 3, last_run_at: '2026-06-01T10:00:00' },
    { id: 2, workflow_name: 'Monthly Summary', platform_hint: 'QuickBooks', run_count: 1, last_run_at: null },
  ]

  it('renders workflow list', () => {
    render(<WorkflowMemoryQuickList workflows={workflows} onRepeat={() => {}} />)
    expect(screen.getByText(/Workflow Memory/i)).toBeTruthy()
    expect(screen.getByText(/Daily Invoice Process/)).toBeTruthy()
    expect(screen.getByText(/Monthly Summary/)).toBeTruthy()
  })

  it('shows workflow count', () => {
    render(<WorkflowMemoryQuickList workflows={workflows} onRepeat={() => {}} />)
    expect(screen.getByText(/\(2\)/)).toBeTruthy()
  })

  it('shows Repeat buttons', () => {
    render(<WorkflowMemoryQuickList workflows={workflows} onRepeat={() => {}} />)
    const buttons = screen.getAllByText(/Repeat/i)
    expect(buttons.length).toBe(2)
  })

  it('calls onRepeat when repeat clicked', () => {
    const onRepeat = vi.fn()
    render(<WorkflowMemoryQuickList workflows={workflows} onRepeat={onRepeat} />)
    const buttons = screen.getAllByText(/Repeat/i)
    fireEvent.click(buttons[0])
    expect(onRepeat).toHaveBeenCalledWith(1)
  })

  it('renders empty state when no workflows', () => {
    const { container } = render(<WorkflowMemoryQuickList workflows={[]} onRepeat={() => {}} />)
    expect(container.innerHTML).toBe('')
  })
})
