import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ApprovalModal from '../src/components/ApprovalModal.jsx'

const approval = {
  id: 1,
  node_name: 'human_approval_checkpoint',
  status: 'pending',
  message: 'Approve export of 3 invoices',
  before: { invoice_ids: [1, 2, 3] },
  after: { excel_path: 'foo.xlsx' },
  approved_by: null,
  approved_at: null,
  decision_note: null,
  created_at: '2026-05-12T10:00:03Z'
}

describe('ApprovalModal', () => {
  it('renders nothing when approval is null', () => {
    const { container } = render(
      <ApprovalModal approval={null} onApprove={() => {}} onReject={() => {}} onClose={() => {}} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('shows before/after JSON and node name', () => {
    render(
      <ApprovalModal approval={approval} onApprove={() => {}} onReject={() => {}} onClose={() => {}} />
    )
    expect(screen.getByText(/Approval required/i)).toBeTruthy()
    expect(screen.getByText('human_approval_checkpoint')).toBeTruthy()
    expect(screen.getByText(/Approve export of 3 invoices/)).toBeTruthy()
    // The before/after JSON should include the key invoice_ids and excel_path
    expect(screen.getByText(/"invoice_ids"/)).toBeTruthy()
    expect(screen.getByText(/"excel_path"/)).toBeTruthy()
  })

  it('calls onApprove with the typed note', () => {
    const onApprove = vi.fn()
    render(
      <ApprovalModal approval={approval} onApprove={onApprove} onReject={() => {}} onClose={() => {}} />
    )
    const textarea = screen.getByPlaceholderText(/verified totals/i)
    fireEvent.change(textarea, { target: { value: 'all good' } })
    fireEvent.click(screen.getByText('Approve'))
    expect(onApprove).toHaveBeenCalledWith('all good')
  })

  it('calls onReject with the typed note', () => {
    const onReject = vi.fn()
    render(
      <ApprovalModal approval={approval} onApprove={() => {}} onReject={onReject} onClose={() => {}} />
    )
    const textarea = screen.getByPlaceholderText(/verified totals/i)
    fireEvent.change(textarea, { target: { value: 'totals wrong' } })
    fireEvent.click(screen.getByText('Reject'))
    expect(onReject).toHaveBeenCalledWith('totals wrong')
  })

  it('calls onClose when backdrop is clicked', () => {
    const onClose = vi.fn()
    const { container } = render(
      <ApprovalModal approval={approval} onApprove={() => {}} onReject={() => {}} onClose={onClose} />
    )
    // The backdrop is the first child div with class modal-backdrop.
    fireEvent.click(container.querySelector('.modal-backdrop'))
    expect(onClose).toHaveBeenCalled()
  })
})
