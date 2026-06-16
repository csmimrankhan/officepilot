import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

vi.mock('../src/api.js', async () => {
  const actual = await vi.importActual('../src/api.js')
  return {
    ...actual,
    api: {
      listWorkflowGraphs: vi.fn(),
      listWorkflowRuns: vi.fn(),
      getWorkflowRun: vi.fn(),
      approveWorkflowRun: vi.fn(),
      rejectWorkflowRun: vi.fn(),
      cancelWorkflowRun: vi.fn(),
      retryWorkflowRun: vi.fn()
    }
  }
})

import { api } from '../src/api.js'
import WorkflowRuns from '../src/pages/WorkflowRuns.jsx'
import WorkflowRunDetail from '../src/pages/WorkflowRunDetail.jsx'
import PendingApprovals from '../src/pages/PendingApprovals.jsx'

const fakeGraphs = {
  graphs: [
    { name: 'invoice_upload_processing', description: 'Phase 6 upload graph', node_names: ['store_file'] },
    { name: 'excel_export_processing', description: 'Phase 6 export graph', node_names: ['human_approval_checkpoint'] }
  ]
}

const fakeRun = {
  id: 1,
  workflow_name: 'invoice_upload_processing',
  status: 'completed',
  current_node: 'audit_log',
  input: { actor: 'alice' },
  state: { invoice_id: 99 },
  error_message: null,
  actor: 'alice',
  started_at: '2026-05-12T10:00:00Z',
  completed_at: '2026-05-12T10:00:05Z',
  logs: [
    { id: 1, node_name: 'store_file', status: 'ok', message: 'started', data: {}, created_at: '2026-05-12T10:00:00Z' },
    { id: 2, node_name: 'parse_invoice', status: 'ok', message: 'parsed', data: { confidence: 0.9 }, created_at: '2026-05-12T10:00:01Z' }
  ],
  approvals: [],
  pending_approval: null
}

const fakeAwaitingRun = {
  ...fakeRun,
  id: 2,
  status: 'awaiting_approval',
  current_node: 'human_approval_checkpoint',
  pending_approval: {
    id: 1,
    node_name: 'human_approval_checkpoint',
    status: 'pending',
    message: 'Approve export of 3 invoices to approved_invoices_2026.xlsx',
    before: { invoice_ids: [1, 2, 3] },
    after: { excel_path: 'approved_invoices_2026.xlsx' },
    approved_by: null,
    approved_at: null,
    decision_note: null,
    created_at: '2026-05-12T10:00:03Z'
  },
  approvals: [
    {
      id: 1, node_name: 'human_approval_checkpoint', status: 'pending',
      message: 'Approve export of 3 invoices', before: null, after: null,
      approved_by: null, approved_at: null, decision_note: null,
      created_at: '2026-05-12T10:00:03Z'
    }
  ]
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/workflows" element={<WorkflowRuns />} />
        <Route path="/workflows/approvals" element={<PendingApprovals />} />
        <Route path="/workflows/:id" element={<WorkflowRunDetail />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  // Default: confirm() returns true.
  vi.spyOn(window, 'confirm').mockReturnValue(true)
})

describe('WorkflowRuns page', () => {
  it('lists runs and shows graph filter options', async () => {
    api.listWorkflowGraphs.mockResolvedValue(fakeGraphs)
    api.listWorkflowRuns.mockResolvedValue({ runs: [
      { ...fakeRun, status: 'completed' },
      { ...fakeRun, id: 2, status: 'failed', error_message: 'parse failed' }
    ] })
    renderAt('/workflows')
    await waitFor(() => {
      expect(screen.getByText('Workflow Runs')).toBeTruthy()
    })
    // Look for badges specifically (not filter <option> labels which
    // also contain the status name).
    const rows = screen.getAllByRole('row')
    expect(rows.length).toBeGreaterThan(1)
    const rowText = rows.map((r) => r.textContent).join(' ')
    expect(rowText).toMatch(/Completed/)
    expect(rowText).toMatch(/Failed/)
    // Graph filter option present
    const select = screen.getAllByRole('combobox').find((s) =>
      Array.from(s.options).some((o) => o.textContent === 'invoice_upload_processing')
    )
    expect(select).toBeTruthy()
  })

  it('shows empty state when no runs', async () => {
    api.listWorkflowGraphs.mockResolvedValue(fakeGraphs)
    api.listWorkflowRuns.mockResolvedValue({ runs: [] })
    renderAt('/workflows')
    await waitFor(() => {
      expect(screen.getByText(/No workflow runs match these filters/i)).toBeTruthy()
    })
  })
})

describe('PendingApprovals page', () => {
  it('lists awaiting runs and links to detail', async () => {
    api.listWorkflowRuns.mockResolvedValue({ runs: [fakeAwaitingRun] })
    renderAt('/workflows/approvals')
    await waitFor(() => {
      expect(screen.getByText('Pending Approvals')).toBeTruthy()
    })
    expect(screen.getByText('human_approval_checkpoint')).toBeTruthy()
    const reviewLink = screen.getByText('Review')
    expect(reviewLink.getAttribute('href')).toBe('/workflows/2')
  })

  it('shows empty state', async () => {
    api.listWorkflowRuns.mockResolvedValue({ runs: [] })
    renderAt('/workflows/approvals')
    await waitFor(() => {
      expect(screen.getByText(/No workflow runs are currently awaiting approval/i)).toBeTruthy()
    })
  })
})

describe('WorkflowRunDetail page', () => {
  it('shows run details and timeline', async () => {
    api.getWorkflowRun.mockResolvedValue(fakeRun)
    renderAt('/workflows/1')
    await waitFor(() => {
      expect(screen.getByText('Workflow Run #1')).toBeTruthy()
    })
    expect(screen.getByText('store_file')).toBeTruthy()
    expect(screen.getByText('parse_invoice')).toBeTruthy()
    expect(screen.getByText('Final state')).toBeTruthy()
  })

  it('shows the approve button when run is awaiting approval', async () => {
    api.getWorkflowRun.mockResolvedValue(fakeAwaitingRun)
    api.approveWorkflowRun.mockResolvedValue({ ...fakeAwaitingRun, status: 'completed' })
    renderAt('/workflows/2')
    await waitFor(() => {
      expect(screen.getByText(/Review.*approve/)).toBeTruthy()
    })
    fireEvent.click(screen.getByText(/Review.*approve/))
    await waitFor(() => {
      // Modal opens with the approval title (h3 "Approval required").
      const modalTitles = screen.getAllByText('Approval required')
      expect(modalTitles.length).toBeGreaterThan(0)
    })
  })

  it('hides approve button for completed runs', async () => {
    api.getWorkflowRun.mockResolvedValue(fakeRun)
    renderAt('/workflows/1')
    await waitFor(() => {
      expect(screen.getByText('Workflow Run #1')).toBeTruthy()
    })
    expect(screen.queryByText(/Review.*approve/)).toBeNull()
  })

  it('shows error message when present', async () => {
    api.getWorkflowRun.mockResolvedValue({ ...fakeRun, status: 'failed', error_message: 'parse crashed' })
    renderAt('/workflows/1')
    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeTruthy()
      expect(screen.getByText(/parse crashed/)).toBeTruthy()
    })
  })
})
