import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import WorkflowRecordingOverlay from './WorkflowRecordingOverlay.jsx'
import RecordedWorkflowPreview from './RecordedWorkflowPreview.jsx'
import SkillDraftReview from './SkillDraftReview.jsx'

// ── WorkflowRecordingOverlay ────────────────────────────────────────────

describe('WorkflowRecordingOverlay', () => {
  const defaultOverlay = {
    sessionId: 1,
    title: 'Test Recording',
    startedAt: new Date().toISOString(),
    eventCount: 5,
    onStop: vi.fn(),
    onCancel: vi.fn(),
  }

  it('renders nothing when sessionId is null', () => {
    const { container } = render(<WorkflowRecordingOverlay sessionId={null} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders title and event count', () => {
    render(<WorkflowRecordingOverlay {...defaultOverlay} />)
    expect(screen.getByText('Recording Workflow')).toBeTruthy()
    expect(screen.getByText('Test Recording')).toBeTruthy()
    expect(screen.getByText(/Events captured/)).toBeTruthy()
    expect(screen.getByText('5')).toBeTruthy()
  })

  it('renders Stop and Cancel buttons', () => {
    render(<WorkflowRecordingOverlay {...defaultOverlay} />)
    expect(screen.getByText('Stop Recording')).toBeTruthy()
    expect(screen.getByText('Cancel')).toBeTruthy()
  })

  it('calls onStop when Stop is clicked', () => {
    const onStop = vi.fn()
    render(<WorkflowRecordingOverlay {...defaultOverlay} onStop={onStop} />)
    fireEvent.click(screen.getByText('Stop Recording'))
    expect(onStop).toHaveBeenCalled()
  })

  it('calls onCancel when Cancel is clicked', () => {
    const onCancel = vi.fn()
    render(<WorkflowRecordingOverlay {...defaultOverlay} onCancel={onCancel} />)
    fireEvent.click(screen.getByText('Cancel'))
    expect(onCancel).toHaveBeenCalled()
  })

  it('shows safety note about redaction', () => {
    render(<WorkflowRecordingOverlay {...defaultOverlay} />)
    expect(screen.getByText(/No passwords, OTPs, or secrets are recorded/)).toBeTruthy()
  })

  it('shows timer display', () => {
    render(<WorkflowRecordingOverlay {...defaultOverlay} />)
    const timer = screen.getByText(/0:0\d/)
    expect(timer).toBeTruthy()
  })
})

// ── RecordedWorkflowPreview ─────────────────────────────────────────────

describe('RecordedWorkflowPreview', () => {
  const sampleEvents = [
    { id: 1, event_order: 1, event_type: 'click', label: 'Save button', app_name: 'Notepad', risk_level: 'medium', was_redacted: false },
    { id: 2, event_order: 2, event_type: 'type_text', label: 'password', app_name: 'Notepad', risk_level: 'medium', was_redacted: true },
    { id: 3, event_order: 3, event_type: 'browser_url_open', label: 'example.com', browser_url: 'https://example.com', risk_level: 'low', was_redacted: false },
  ]

  it('shows empty state when no events', () => {
    render(<RecordedWorkflowPreview events={[]} />)
    expect(screen.getByText(/No events recorded yet/)).toBeTruthy()
  })

  it('renders step count', () => {
    render(<RecordedWorkflowPreview events={sampleEvents} />)
    expect(screen.getByText(/Recorded Steps \(3\)/)).toBeTruthy()
  })

  it('renders event types', () => {
    render(<RecordedWorkflowPreview events={sampleEvents} />)
    expect(screen.getByText('click')).toBeTruthy()
    expect(screen.getByText('type_text')).toBeTruthy()
  })

  it('renders [REDACTED] badge for redacted events', () => {
    render(<RecordedWorkflowPreview events={sampleEvents} />)
    const badges = screen.getAllByText('[REDACTED]')
    expect(badges.length).toBeGreaterThanOrEqual(1)
  })

  it('shows url indicator for browser events', () => {
    render(<RecordedWorkflowPreview events={sampleEvents} />)
    const urlIndicators = screen.getAllByText('url')
    expect(urlIndicators.length).toBeGreaterThanOrEqual(1)
  })

  it('renders Convert to Skill button when callback provided', () => {
    render(<RecordedWorkflowPreview events={sampleEvents} onConvertToSkill={vi.fn()} />)
    expect(screen.getByText('Convert to Skill')).toBeTruthy()
  })

  it('calls onConvertToSkill when button clicked', () => {
    const onConvert = vi.fn()
    render(<RecordedWorkflowPreview events={sampleEvents} onConvertToSkill={onConvert} />)
    fireEvent.click(screen.getByText('Convert to Skill'))
    expect(onConvert).toHaveBeenCalled()
  })

  it('shows loading state on convert button', () => {
    render(<RecordedWorkflowPreview events={sampleEvents} onConvertToSkill={vi.fn()} loading={true} />)
    expect(screen.getByText('Converting...')).toBeTruthy()
  })

  it('calls onDeleteEvent when delete button clicked', () => {
    const onDelete = vi.fn()
    render(<RecordedWorkflowPreview events={sampleEvents} onDeleteEvent={onDelete} />)
    const deleteButtons = screen.getAllByTitle('Remove step')
    fireEvent.click(deleteButtons[0])
    expect(onDelete).toHaveBeenCalledWith(1)
  })
})

// ── SkillDraftReview ───────────────────────────────────────────────────

describe('SkillDraftReview', () => {
  const sampleDraft = {
    id: 42,
    name: 'My Recorded Skill',
    description: 'Converted from recorded workflow',
    trigger_phrases: ['run notepad workflow', 'start notepad tasks', 'run recorded workflow'],
    steps: [
      { step_order: 1, step_type: 'desktop_click', target: 'Save button', risk_level: 'medium' },
      { step_order: 2, step_type: 'desktop_type', target: 'password', risk_level: 'medium' },
    ],
    safety_rules: {
      requires_dry_run: true,
      approval_required: true,
      max_risk_level: 'medium',
    },
    status: 'draft',
  }

  it('renders nothing when no draft', () => {
    const { container } = render(<SkillDraftReview draft={null} />)
    expect(container.innerHTML).toBe('')
  })

  it('renders draft name and description', () => {
    render(<SkillDraftReview draft={sampleDraft} />)
    expect(screen.getByText('Skill Draft Review')).toBeTruthy()
    expect(screen.getByText('My Recorded Skill')).toBeTruthy()
    expect(screen.getByText('Converted from recorded workflow')).toBeTruthy()
  })

  it('renders trigger phrases', () => {
    render(<SkillDraftReview draft={sampleDraft} />)
    expect(screen.getByText(/Trigger Phrases/)).toBeTruthy()
    expect(screen.getByText('run notepad workflow')).toBeTruthy()
    expect(screen.getByText('start notepad tasks')).toBeTruthy()
  })

  it('renders steps', () => {
    render(<SkillDraftReview draft={sampleDraft} />)
    expect(screen.getByText(/Steps \(2\)/)).toBeTruthy()
    expect(screen.getByText('desktop_click')).toBeTruthy()
    expect(screen.getByText('desktop_type')).toBeTruthy()
  })

  it('renders safety rules', () => {
    render(<SkillDraftReview draft={sampleDraft} />)
    expect(screen.getByText('Dry-run required')).toBeTruthy()
    expect(screen.getByText('Approval required')).toBeTruthy()
    expect(screen.getByText(/Max risk: medium/)).toBeTruthy()
  })

  it('renders Save Skill and Reject buttons', () => {
    render(<SkillDraftReview draft={sampleDraft} onSaveSkill={vi.fn()} onRejectDraft={vi.fn()} />)
    expect(screen.getByText('Save Skill')).toBeTruthy()
    expect(screen.getByText('Reject')).toBeTruthy()
  })

  it('calls onSaveSkill when Save is clicked', () => {
    const onSave = vi.fn()
    render(<SkillDraftReview draft={sampleDraft} onSaveSkill={onSave} />)
    fireEvent.click(screen.getByText('Save Skill'))
    expect(onSave).toHaveBeenCalled()
  })

  it('calls onRejectDraft when Reject is clicked', () => {
    const onReject = vi.fn()
    render(<SkillDraftReview draft={sampleDraft} onRejectDraft={onReject} />)
    fireEvent.click(screen.getByText('Reject'))
    expect(onReject).toHaveBeenCalled()
  })

  it('shows loading on save button during save', () => {
    render(<SkillDraftReview draft={sampleDraft} onSaveSkill={vi.fn()} loading={true} />)
    expect(screen.getByText('Saving...')).toBeTruthy()
  })
})
