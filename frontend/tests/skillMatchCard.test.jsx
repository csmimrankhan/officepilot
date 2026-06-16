import { vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SkillMatchCard from '../src/components/agent/SkillMatchCard.jsx'

const mockSkill = {
  skill_id: 1,
  name: 'Daily Invoice Process',
  description: 'Automated daily invoice workflow',
  confidence: 0.92,
  match_type: 'strong',
  matched_trigger: 'process today invoices',
  trigger_phrases: ['process today invoices', 'daily invoice process'],
  steps: [
    { step_order: 1, step_type: 'scan_local_folder', target: 'file system', instruction: 'Scan for invoice files', risk_level: 'low' },
    { step_order: 2, step_type: 'extract_invoice_data', target: 'invoice files', instruction: 'Extract data', risk_level: 'low' },
    { step_order: 3, step_type: 'create_daily_invoices_excel', target: 'Excel', instruction: 'Create workbook', risk_level: 'medium', requires_approval: true },
  ],
  safety_rules: { max_risk_level: 'medium', approval_required: true },
  approval_required: true,
  run_count: 3,
  version: 1,
}

const mockPossibleSkill = {
  ...mockSkill,
  confidence: 0.72,
  match_type: 'possible',
  matched_trigger: 'monthly report generation',
}

const mockApi = vi.hoisted(() => ({
  dryRunSkill: vi.fn(),
  executeSkill: vi.fn(),
}))
vi.mock('../src/api.js', () => ({ api: mockApi }))

beforeEach(() => { vi.clearAllMocks() })

describe('SkillMatchCard', () => {
  it('renders skill name and confidence', () => {
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    expect(screen.getByText('Daily Invoice Process')).toBeTruthy()
    expect(screen.getByText(/92%/)).toBeTruthy()
    expect(screen.getByText(/Strong Match/)).toBeTruthy()
  })

  it('renders possible match badge for lower confidence', () => {
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockPossibleSkill} /></MemoryRouter>)
    expect(screen.getByText(/Possible Match/)).toBeTruthy()
    expect(screen.getByText(/72%/)).toBeTruthy()
  })

  it('renders matched trigger phrase', () => {
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    expect(screen.getByText(/process today invoices/)).toBeTruthy()
  })

  it('renders steps preview', () => {
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    expect(screen.getByText('3 steps')).toBeTruthy()
    expect(screen.getByText('scan_local_folder')).toBeTruthy()
    expect(screen.getByText('extract_invoice_data')).toBeTruthy()
    expect(screen.getByText('create_daily_invoices_excel')).toBeTruthy()
  })

  it('renders safety badges', () => {
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    expect(screen.getByText(/medium/)).toBeTruthy()
    expect(screen.getByText(/Approval Required/)).toBeTruthy()
  })

  it('renders Dry-run Skill button', () => {
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    expect(screen.getByText('Dry-run Skill')).toBeTruthy()
  })

  it('renders Edit Skill button', () => {
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    expect(screen.getByText('Edit Skill')).toBeTruthy()
  })

  it('renders Create New Plan Instead button', () => {
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    expect(screen.getByText('Create New Plan Instead')).toBeTruthy()
  })

  it('renders Cancel button', () => {
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    expect(screen.getByText('Cancel')).toBeTruthy()
  })

  it('calls dryRunSkill on button click', async () => {
    mockApi.dryRunSkill.mockResolvedValue({ ok: true, run_id: 42 })
    const onDryRun = vi.fn()
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} onDryRun={onDryRun} /></MemoryRouter>)
    fireEvent.click(screen.getByText('Dry-run Skill'))
    await waitFor(() => {
      expect(mockApi.dryRunSkill).toHaveBeenCalledWith(1)
      expect(onDryRun).toHaveBeenCalled()
    })
  })

  it('shows dry-run success message', async () => {
    mockApi.dryRunSkill.mockResolvedValue({ ok: true, run_id: 42 })
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    fireEvent.click(screen.getByText('Dry-run Skill'))
    await waitFor(() => {
      expect(screen.getByText(/Dry-run completed/)).toBeTruthy()
      expect(screen.getByText('Approve & Execute')).toBeTruthy()
    })
  })

  it('shows dry-run error message on failure', async () => {
    mockApi.dryRunSkill.mockRejectedValue(new Error('Network error'))
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    fireEvent.click(screen.getByText('Dry-run Skill'))
    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeTruthy()
    })
  })

  it('calls onCreateNewPlan when button clicked', () => {
    const onCreateNewPlan = vi.fn()
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} onCreateNewPlan={onCreateNewPlan} /></MemoryRouter>)
    fireEvent.click(screen.getByText('Create New Plan Instead'))
    expect(onCreateNewPlan).toHaveBeenCalled()
  })

  it('calls onCancel when button clicked', () => {
    const onCancel = vi.fn()
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} onCancel={onCancel} /></MemoryRouter>)
    fireEvent.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalled()
  })

  it('renders voice reply text', () => {
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} voiceReply="I found a saved skill!" /></MemoryRouter>)
    expect(screen.getByText('I found a saved skill!')).toBeTruthy()
  })

  it('renders description', () => {
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    expect(screen.getByText('Automated daily invoice workflow')).toBeTruthy()
  })

  it('calls executeSkill after dry-run success', async () => {
    mockApi.dryRunSkill.mockResolvedValue({ ok: true, run_id: 42 })
    mockApi.executeSkill.mockResolvedValue({ ok: true, run_id: 43 })
    render(<MemoryRouter><SkillMatchCard matchedSkill={mockSkill} /></MemoryRouter>)
    fireEvent.click(screen.getByText('Dry-run Skill'))
    await waitFor(() => {
      expect(screen.getByText('Approve & Execute')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Approve & Execute'))
    await waitFor(() => {
      expect(mockApi.executeSkill).toHaveBeenCalledWith(1, {})
    })
  })
})
