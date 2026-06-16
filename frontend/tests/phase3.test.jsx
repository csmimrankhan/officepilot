import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import FolderSettings from '../src/pages/FolderSettings.jsx'
import AuditTimeline from '../src/components/AuditTimeline.jsx'

vi.mock('../src/api.js', () => {
  return {
    api: {
      base: 'http://test',
      getFolderRules: vi.fn(),
      updateFolderRules: vi.fn(),
      folderRulesAudit: vi.fn(),
      invoiceAuditTimeline: vi.fn()
    },
    formatDateTime: (v) => (v ? new Date(v).toISOString() : '')
  }
})

import { api } from '../src/api.js'

beforeEach(() => vi.clearAllMocks())

describe('FolderSettings', () => {
  it('loads current rules and saves a patch', async () => {
    api.getFolderRules.mockResolvedValueOnce({
      enabled: true,
      pattern: 'A/{vendor}.{ext}',
      conflict_strategy: 'suffix',
      move_on_approve: true
    })
    api.folderRulesAudit.mockResolvedValueOnce([])
    api.updateFolderRules.mockResolvedValueOnce({
      enabled: true,
      pattern: 'B/{vendor}.{ext}',
      conflict_strategy: 'suffix',
      move_on_approve: true
    })
    api.folderRulesAudit.mockResolvedValueOnce([
      {
        id: 1,
        actor: 'alice',
        created_at: '2026-01-02T00:00:00Z',
        before: { enabled: true, pattern: 'A/{vendor}.{ext}', conflict_strategy: 'suffix', move_on_approve: true },
        after: { enabled: true, pattern: 'B/{vendor}.{ext}', conflict_strategy: 'suffix', move_on_approve: true }
      }
    ])

    render(<MemoryRouter><FolderSettings /></MemoryRouter>)
    const input = await screen.findByDisplayValue('A/{vendor}.{ext}')
    fireEvent.change(input, { target: { value: 'B/{vendor}.{ext}' } })
    fireEvent.click(screen.getByText(/Save changes/))
    await waitFor(() => expect(api.updateFolderRules).toHaveBeenCalled())
    expect(await screen.findByText('Saved.')).toBeInTheDocument()
  })

  it('shows change history rows', async () => {
    api.getFolderRules.mockResolvedValueOnce({
      enabled: true,
      pattern: 'A/{vendor}.{ext}',
      conflict_strategy: 'suffix',
      move_on_approve: true
    })
    api.folderRulesAudit.mockResolvedValueOnce([
      {
        id: 7,
        actor: 'bob',
        created_at: '2026-01-02T00:00:00Z',
        before: { enabled: true, pattern: 'OLD', conflict_strategy: 'suffix', move_on_approve: true },
        after: { enabled: true, pattern: 'NEW', conflict_strategy: 'suffix', move_on_approve: true }
      }
    ])
    render(<MemoryRouter><FolderSettings /></MemoryRouter>)
    expect(await screen.findByText('bob')).toBeInTheDocument()
    const pres = document.querySelectorAll('pre')
    const all = Array.from(pres).map((p) => p.textContent).join('\n')
    expect(all).toContain('OLD')
    expect(all).toContain('NEW')
  })
})

describe('AuditTimeline', () => {
  it('renders entries from the timeline endpoint', async () => {
    api.invoiceAuditTimeline.mockResolvedValueOnce([
      { id: 1, action: 'upload', actor: 'user', timestamp: '2026-01-02T00:00:00Z',
        details: 'Uploaded a.pdf', extra_json: {}, before_data_json: null, after_data_json: null },
      { id: 2, action: 'approve', actor: 'manager', timestamp: '2026-01-03T00:00:00Z',
        details: 'Approved invoice #1', extra_json: {},
        before_data_json: { status: 'ready_for_approval' },
        after_data_json: { status: 'approved' } }
    ])
    render(<MemoryRouter><AuditTimeline invoiceId={1} /></MemoryRouter>)
    expect(await screen.findByText('Uploaded')).toBeInTheDocument()
    expect(screen.getByText('Approved')).toBeInTheDocument()
  })

  it('shows an empty state when there are no entries', async () => {
    api.invoiceAuditTimeline.mockResolvedValueOnce([])
    render(<MemoryRouter><AuditTimeline invoiceId={1} /></MemoryRouter>)
    expect(await screen.findByText(/No audit entries/)).toBeInTheDocument()
  })

  it('expands a diff when the button is clicked', async () => {
    api.invoiceAuditTimeline.mockResolvedValueOnce([
      { id: 1, action: 'approve', actor: 'manager', timestamp: '2026-01-02T00:00:00Z',
        details: 'Approved invoice #1', extra_json: {},
        before_data_json: { status: 'ready_for_approval' },
        after_data_json: { status: 'approved' } }
    ])
    render(<MemoryRouter><AuditTimeline invoiceId={1} /></MemoryRouter>)
    expect(await screen.findByText('Approved')).toBeInTheDocument()
    fireEvent.click(screen.getByText(/View diff/))
    // Diff renders in a table — find the "status" row and confirm values are present
    await waitFor(() => {
      const all = document.body.textContent
      expect(all).toContain('ready_for_approval')
      expect(all).toContain('approved')
    })
  })
})
