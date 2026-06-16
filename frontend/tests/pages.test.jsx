import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import UploadInvoice from '../src/pages/UploadInvoice.jsx'
import ReviewQueue from '../src/pages/ReviewQueue.jsx'

vi.mock('../src/api.js', () => {
  return {
    api: {
      base: 'http://test',
      uploadInvoice: vi.fn(),
      listInvoices: vi.fn(),
      getInvoice: vi.fn(),
      updateInvoice: vi.fn(),
      approveInvoice: vi.fn(),
      rejectInvoice: vi.fn(),
      reviewQueue: vi.fn(),
      invoiceAuditTimeline: vi.fn(),
      organizeFile: vi.fn(),
      markDuplicate: vi.fn(),
      exportExcelUrl: () => 'http://test/api/invoices/export/excel?actor=user',
      fileUrl: (id) => `http://test/api/invoices/${id}/file?inline=true`,
      fileDownloadUrl: (id) => `http://test/api/invoices/${id}/file?inline=false`,
      listAuditLogs: vi.fn()
    },
    STATUS_LABELS: {
      imported: 'Imported',
      extracting: 'Extracting',
      needs_review: 'Needs Review',
      ready_for_approval: 'Ready for Approval',
      approved: 'Approved',
      rejected: 'Rejected',
      duplicate: 'Duplicate',
      exported: 'Exported'
    },
    formatMoney: (v, c) => (v == null ? '' : `${c || '$'}${Number(v).toFixed(2)}`),
    formatDateTime: (v) => (v ? new Date(v).toISOString() : '')
  }
})

import { api } from '../src/api.js'

beforeEach(() => vi.clearAllMocks())

describe('UploadInvoice', () => {
  it('rejects empty submit', async () => {
    render(<MemoryRouter><UploadInvoice /></MemoryRouter>)
    fireEvent.click(screen.getByText(/Upload & Extract/i))
    expect(await screen.findByText(/Please choose a file/)).toBeInTheDocument()
    expect(api.uploadInvoice).not.toHaveBeenCalled()
  })

  it('calls api.uploadInvoice with the selected file', async () => {
    api.uploadInvoice.mockResolvedValueOnce({ id: 7, status: 'ready_for_approval' })
    render(<MemoryRouter><UploadInvoice /></MemoryRouter>)
    const file = new File(['x'], 'a.pdf', { type: 'application/pdf' })
    const input = screen.getByLabelText(/Choose file/i)
    fireEvent.change(input, { target: { files: [file] } })
    fireEvent.click(screen.getByText(/Upload & Extract/i))
    await waitFor(() => expect(api.uploadInvoice).toHaveBeenCalledWith(file, 'user'))
    expect(await screen.findByText(/Uploaded as invoice/)).toBeInTheDocument()
  })

  it('surfaces server error messages', async () => {
    api.uploadInvoice.mockRejectedValueOnce(new Error('415 Unsupported File Type'))
    render(<MemoryRouter><UploadInvoice /></MemoryRouter>)
    const file = new File(['x'], 'a.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText(/Choose file/i), { target: { files: [file] } })
    fireEvent.click(screen.getByText(/Upload & Extract/i))
    expect(await screen.findByText(/Unsupported File Type/)).toBeInTheDocument()
  })
})

describe('ReviewQueue', () => {
  it('renders a row for each invoice and an open link', async () => {
    api.reviewQueue.mockResolvedValueOnce({
      by_status: {
        ready_for_approval: [
          { id: 1, vendor_name: 'ACME', invoice_number: 'INV-1', invoice_date: '2026-01-01',
            total_amount: 10, currency: 'USD', confidence_score: 0.9, status: 'ready_for_approval',
            updated_at: '2026-01-02T00:00:00Z' }
        ]
      },
      counts: { ready_for_approval: 1 }
    })
    render(<MemoryRouter><ReviewQueue /></MemoryRouter>)
    expect(await screen.findByText('ACME')).toBeInTheDocument()
    expect(screen.getByText(/INV-1/)).toBeInTheDocument()
    expect(screen.getByText('Open')).toBeInTheDocument()
  })

  it('shows an empty state when no invoices', async () => {
    api.reviewQueue.mockResolvedValueOnce({ by_status: {}, counts: {} })
    render(<MemoryRouter><ReviewQueue /></MemoryRouter>)
    expect(await screen.findByText(/No invoices match/)).toBeInTheDocument()
  })

  it('groups by status and shows duplicate links', async () => {
    api.reviewQueue.mockResolvedValueOnce({
      by_status: {
        ready_for_approval: [
          { id: 1, vendor_name: 'ACME', invoice_number: 'INV-1', invoice_date: '2026-01-01',
            total_amount: 10, currency: 'USD', confidence_score: 0.9,
            status: 'ready_for_approval', updated_at: '2026-01-02T00:00:00Z' }
        ],
        duplicate: [
          { id: 2, vendor_name: 'ACME', invoice_number: 'INV-1', invoice_date: '2026-01-01',
            total_amount: 10, currency: 'USD', confidence_score: 0.9,
            status: 'duplicate', updated_at: '2026-01-02T00:00:00Z',
            duplicate_of_invoice_id: 1 }
        ]
      },
      counts: { ready_for_approval: 1, duplicate: 1 }
    })
    render(<MemoryRouter><ReviewQueue /></MemoryRouter>)
    // Wait for the table to populate (vendors are ACME for both rows).
    await waitFor(() => {
      expect(screen.getAllByText('ACME').length).toBeGreaterThan(0)
    })
    // Switch to the duplicate filter
    const dupButton = screen.getByRole('button', { name: /Duplicate \(1\)/ })
    fireEvent.click(dupButton)
    expect(await screen.findByText(/dup of/)).toBeInTheDocument()
  })
})
