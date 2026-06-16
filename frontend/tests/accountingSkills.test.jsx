import { vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AccountingSkills from '../src/pages/AccountingSkills.jsx'

const mockSkills = [
  {
    id: 1,
    name: 'Daily Invoice Summary',
    description: 'Auto-create daily invoice summary',
    trigger_phrases: ['daily invoice', 'invoice summary', 'aaj ka invoice'],
    steps_count: 5,
    approval_required: true,
    version: 2,
    status: 'active',
    run_count: 3,
    last_used_at: '2026-06-09T12:00:00Z',
    created_at: '2026-06-01T12:00:00Z',
    updated_at: '2026-06-09T12:00:00Z',
  },
  {
    id: 2,
    name: 'Monthly P&L',
    description: 'Monthly profit and loss comparison',
    trigger_phrases: ['monthly pnl', 'profit loss'],
    steps_count: 8,
    approval_required: true,
    version: 1,
    status: 'active',
    run_count: 1,
    last_used_at: null,
    created_at: '2026-06-05T12:00:00Z',
    updated_at: '2026-06-05T12:00:00Z',
  },
]

const mockDetail = {
  id: 1,
  name: 'Daily Invoice Summary',
  description: 'Auto-create daily invoice summary',
  trigger_phrases: ['daily invoice', 'invoice summary'],
  workflow_steps: [
    { step_type: 'scan_folder', target: 'invoices/', risk_level: 'low' },
    { step_type: 'extract_data', target: 'invoice.pdf', risk_level: 'low' },
    { step_type: 'create_excel', target: 'Daily_Invoices.xlsx', risk_level: 'medium' },
  ],
  variables: [{ name: 'date', type: 'string', example: '2026-06-10' }],
  safety_rules: { approval_required: true, max_risk_level: 'medium' },
  approval_required: true,
  version: 2,
  status: 'active',
  run_count: 3,
  last_used_at: '2026-06-09T12:00:00Z',
  created_at: '2026-06-01T12:00:00Z',
  updated_at: '2026-06-09T12:00:00Z',
}

const mockVersions = [
  { version: 2, name: 'Daily Invoice Summary v2', steps_count: 5, approval_required: true, created_at: '2026-06-09T12:00:00Z' },
  { version: 1, name: 'Daily Invoice Summary v1', steps_count: 4, approval_required: true, created_at: '2026-06-01T12:00:00Z' },
]

const mockRuns = [
  { id: 10, skill_id: 1, command_text: 'dry-run: Daily Invoice Summary', status: 'dry_run', created_at: '2026-06-09T13:00:00Z', completed_at: null },
  { id: 9, skill_id: 1, command_text: 'dry-run: Daily Invoice Summary', status: 'completed', created_at: '2026-06-08T13:00:00Z', completed_at: '2026-06-08T13:01:00Z' },
]

const mockApi = vi.hoisted(() => ({
  listSkills: vi.fn(),
  getSkill: vi.fn(),
  getSkillVersions: vi.fn(),
  listSkillRuns: vi.fn(),
  updateSkill: vi.fn(),
  dryRunSkill: vi.fn(),
  executeSkill: vi.fn(),
  archiveSkill: vi.fn(),
  restoreSkillVersion: vi.fn(),
  createSkillFromWorkflow: vi.fn(),
}))
vi.mock('../src/api.js', () => ({ api: mockApi }))

function setup() {
  mockApi.listSkills.mockResolvedValue(mockSkills)
  mockApi.getSkill.mockResolvedValue(mockDetail)
  mockApi.getSkillVersions.mockResolvedValue(mockVersions)
  mockApi.listSkillRuns.mockResolvedValue(mockRuns)
}

beforeEach(() => { vi.clearAllMocks(); setup() })

describe('AccountingSkills Page', () => {
  it('renders page title and subtitle', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Skills')).toBeTruthy()
      expect(screen.getByText(/Reusable automation workflows/i)).toBeTruthy()
    })
  })

  it('renders skill cards', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => {
      const cards = screen.getAllByText(/Daily Invoice Summary|Monthly P&L/)
      expect(cards.length).toBeGreaterThanOrEqual(2)
    })
  })

  it('shows empty state when no skills', async () => {
    mockApi.listSkills.mockResolvedValue([])
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText(/No skills found/)).toBeTruthy()
    })
  })

  it('shows search input and category filter', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Search skills/)).toBeTruthy()
      expect(screen.getByText('All Categories')).toBeTruthy()
    })
  })

  it('selects a skill and shows detail panel', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Daily Invoice Summary')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Daily Invoice Summary'))
    await waitFor(() => {
      expect(mockApi.getSkill).toHaveBeenCalledWith(1)
      expect(mockApi.getSkillVersions).toHaveBeenCalledWith(1)
      expect(mockApi.listSkillRuns).toHaveBeenCalledWith(1)
    })
  })

  it('shows empty state when no skill selected', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Select a skill')).toBeTruthy()
    })
  })

  it('shows trigger phrases on selected skill', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('Daily Invoice Summary')).toBeTruthy() })
    fireEvent.click(screen.getByText('Daily Invoice Summary'))
    await waitFor(() => {
      expect(screen.getByText('daily invoice')).toBeTruthy()
      expect(screen.getByText('invoice summary')).toBeTruthy()
    })
  })

  it('shows workflow steps on selected skill', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('Daily Invoice Summary')).toBeTruthy() })
    fireEvent.click(screen.getByText('Daily Invoice Summary'))
    await waitFor(() => {
      expect(screen.getByText('scan_folder')).toBeTruthy()
      expect(screen.getByText('extract_data')).toBeTruthy()
      expect(screen.getByText('create_excel')).toBeTruthy()
    })
  })

  it('shows edit button and toggles edit mode', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('Daily Invoice Summary')).toBeTruthy() })
    fireEvent.click(screen.getByText('Daily Invoice Summary'))
    await waitFor(() => { expect(screen.getByText('Edit')).toBeTruthy() })
    fireEvent.click(screen.getByText('Edit'))
    await waitFor(() => {
      expect(screen.getByText(/Edit Skill/)).toBeTruthy()
    })
  })

  it('shows Dry Run and Run Skill buttons on selected skill', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('Daily Invoice Summary')).toBeTruthy() })
    fireEvent.click(screen.getByText('Daily Invoice Summary'))
    await waitFor(() => {
      expect(screen.getAllByText('Dry Run').length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('Run Skill')).toBeTruthy()
    })
  })

  it('shows version history on selected skill', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('Daily Invoice Summary')).toBeTruthy() })
    fireEvent.click(screen.getByText('Daily Invoice Summary'))
    await waitFor(() => {
      expect(screen.getByText('Version History')).toBeTruthy()
    })
  })

  it('shows restore button for previous versions', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('Daily Invoice Summary')).toBeTruthy() })
    fireEvent.click(screen.getByText('Daily Invoice Summary'))
    await waitFor(() => {
      const restoreButtons = screen.getAllByText('Restore')
      expect(restoreButtons.length).toBeGreaterThanOrEqual(1)
    })
  })

  it('shows recent runs on selected skill', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('Daily Invoice Summary')).toBeTruthy() })
    fireEvent.click(screen.getByText('Daily Invoice Summary'))
    await waitFor(() => {
      expect(screen.getByText('Recent Runs')).toBeTruthy()
    })
  })

  it('calls dryRunSkill on Dry Run button click', async () => {
    mockApi.dryRunSkill.mockResolvedValue({ ok: true, run_id: 11 })
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('Daily Invoice Summary')).toBeTruthy() })
    fireEvent.click(screen.getByText('Daily Invoice Summary'))
    await waitFor(() => {
      const btns = screen.getAllByText('Dry Run')
      expect(btns.length).toBeGreaterThanOrEqual(1)
      fireEvent.click(btns[0])
    })
    await waitFor(() => {
      expect(mockApi.dryRunSkill).toHaveBeenCalledWith(1)
    })
  })

  it('calls archiveSkill on archive button click', async () => {
    mockApi.archiveSkill.mockResolvedValue({ ok: true, skill_id: 1 })
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('Daily Invoice Summary')).toBeTruthy() })
    fireEvent.click(screen.getByText('Daily Invoice Summary'))
    await waitFor(() => { expect(screen.getByText('Archive')).toBeTruthy() })
    fireEvent.click(screen.getByText('Archive'))
    await waitFor(() => {
      expect(mockApi.archiveSkill).toHaveBeenCalledWith(1)
    })
  })

  it('calls restoreSkillVersion on restore button click', async () => {
    mockApi.restoreSkillVersion.mockResolvedValue({ ok: true })
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('Daily Invoice Summary')).toBeTruthy() })
    fireEvent.click(screen.getByText('Daily Invoice Summary'))
    await waitFor(() => {
      const restoreBtns = screen.getAllByText('Restore')
      fireEvent.click(restoreBtns[0])
    })
    await waitFor(() => {
      expect(mockApi.restoreSkillVersion).toHaveBeenCalledWith(1, 1)
    })
  })

  it('displays skill version and run count in cards', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText(/v2/)).toBeTruthy()
    })
  })

  it('searches skills by name', async () => {
    render(<MemoryRouter><AccountingSkills /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByPlaceholderText(/Search skills/)).toBeTruthy() })
    const input = screen.getByPlaceholderText(/Search skills/)
    fireEvent.change(input, { target: { value: 'Monthly' } })
    await waitFor(() => {
      expect(screen.getByText('Monthly P&L')).toBeTruthy()
      expect(screen.queryByText('Daily Invoice Summary')).toBeNull()
    })
  })
})