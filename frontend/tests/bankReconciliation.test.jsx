import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import BankReconciliation from '../src/pages/BankReconciliation.jsx'

vi.mock('../src/api.js', () => ({
  bankParseFeed: vi.fn(),
  bankReconcile: vi.fn(),
}))

import * as api from '../src/api.js'

function renderPage() {
  return render(<MemoryRouter><BankReconciliation /></MemoryRouter>)
}

describe('BankReconciliation Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders upload prompt', () => {
    renderPage()
    expect(screen.getByText('Bank Reconciliation')).toBeTruthy()
    expect(screen.getByText('Upload Bank Feed')).toBeTruthy()
  })

  it('shows file upload button', () => {
    renderPage()
    const btn = screen.getByText('Choose File')
    expect(btn).toBeTruthy()
  })

  it('parses CSV file on upload', async () => {
    api.bankParseFeed.mockResolvedValue({
      ok: true,
      transactions: [
        { date: '2026-01-15', description: 'Payment Acme', amount: 5000, type: 'credit' },
        { date: '2026-01-20', description: 'OfficeMart', amount: 1200, type: 'debit' },
      ],
      count: 2,
    })

    renderPage()
    const input = document.querySelector('input[type="file"]')
    const file = new File(['dummy'], 'feed.csv', { type: 'text/csv' })
    Object.defineProperty(input, 'files', { value: [file] })
    fireEvent.change(input)

    await waitFor(() => {
      expect(screen.getByText('Parsed Transactions (2)')).toBeTruthy()
    })
    expect(screen.getByText('Payment Acme')).toBeTruthy()
    expect(screen.getByText('OfficeMart')).toBeTruthy()
    expect(screen.getByText('credit')).toBeTruthy()
    expect(screen.getByText('debit')).toBeTruthy()
  })

  it('shows error on parse failure', async () => {
    api.bankParseFeed.mockRejectedValue(new Error('Parse error'))

    renderPage()
    const input = document.querySelector('input[type="file"]')
    const file = new File(['bad'], 'bad.csv', { type: 'text/csv' })
    Object.defineProperty(input, 'files', { value: [file] })
    fireEvent.change(input)

    await waitFor(() => {
      expect(screen.getByText('Parse error')).toBeTruthy()
    })
  })

  it('runs reconciliation and shows summary', async () => {
    api.bankParseFeed.mockResolvedValue({
      ok: true,
      transactions: [
        { date: '2026-01-15', description: 'Payment Acme', amount: 5000, type: 'credit' },
      ],
      count: 1,
    })
    api.bankReconcile.mockResolvedValue({
      ok: true,
      summary: { total: 1, matched: 1, fuzzy: 0, unmatched: 0 },
      filepath: '/exports/reconciliation/test.xlsx',
    })

    renderPage()
    const input = document.querySelector('input[type="file"]')
    const file = new File(['dummy'], 'feed.csv', { type: 'text/csv' })
    Object.defineProperty(input, 'files', { value: [file] })
    fireEvent.change(input)

    await waitFor(() => {
      expect(screen.getByText('Reconcile & Generate Report')).toBeTruthy()
    })

    fireEvent.click(screen.getByText('Reconcile & Generate Report'))

    await waitFor(() => {
      expect(screen.getByText('Reconciliation Complete')).toBeTruthy()
    })
    expect(screen.getAllByText('1').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('Total Transactions')).toBeTruthy()
    expect(screen.getByText('Matched')).toBeTruthy()
  })

  it('shows error on reconcile failure', async () => {
    api.bankParseFeed.mockResolvedValue({
      ok: true,
      transactions: [
        { date: '2026-01-15', description: 'Test', amount: 100, type: 'credit' },
      ],
      count: 1,
    })
    api.bankReconcile.mockResolvedValue({ ok: false, error: 'Reconcile failed' })

    renderPage()
    const input = document.querySelector('input[type="file"]')
    const file = new File(['dummy'], 'feed.csv', { type: 'text/csv' })
    Object.defineProperty(input, 'files', { value: [file] })
    fireEvent.change(input)

    await waitFor(() => {
      expect(screen.getByText('Reconcile & Generate Report')).toBeTruthy()
    })

    fireEvent.click(screen.getByText('Reconcile & Generate Report'))

    await waitFor(() => {
      expect(screen.getByText('Reconcile failed')).toBeTruthy()
    })
  })

  it('shows download button after reconciliation', async () => {
    api.bankParseFeed.mockResolvedValue({
      ok: true,
      transactions: [
        { date: '2026-01-15', description: 'Payment Acme', amount: 5000, type: 'credit' },
      ],
      count: 1,
    })
    api.bankReconcile.mockResolvedValue({
      ok: true,
      summary: { total: 1, matched: 1, fuzzy: 0, unmatched: 0 },
      filepath: '/exports/reconciliation/test.xlsx',
    })

    renderPage()
    const input = document.querySelector('input[type="file"]')
    const file = new File(['dummy'], 'feed.csv', { type: 'text/csv' })
    Object.defineProperty(input, 'files', { value: [file] })
    fireEvent.change(input)

    await waitFor(() => {
      expect(screen.getByText('Reconcile & Generate Report')).toBeTruthy()
    })

    fireEvent.click(screen.getByText('Reconcile & Generate Report'))

    await waitFor(() => {
      expect(screen.getByText('Download Excel Report')).toBeTruthy()
    })
  })

  it('start over resets state', async () => {
    api.bankParseFeed.mockResolvedValue({
      ok: true,
      transactions: [
        { date: '2026-01-15', description: 'Payment Acme', amount: 5000, type: 'credit' },
      ],
      count: 1,
    })
    api.bankReconcile.mockResolvedValue({
      ok: true,
      summary: { total: 1, matched: 1, fuzzy: 0, unmatched: 0 },
      filepath: '/exports/reconciliation/test.xlsx',
    })

    renderPage()
    const input = document.querySelector('input[type="file"]')
    const file = new File(['dummy'], 'feed.csv', { type: 'text/csv' })
    Object.defineProperty(input, 'files', { value: [file] })
    fireEvent.change(input)

    await waitFor(() => {
      expect(screen.getByText('Reconcile & Generate Report')).toBeTruthy()
    })

    fireEvent.click(screen.getByText('Reconcile & Generate Report'))

    await waitFor(() => {
      expect(screen.getByText('Download Excel Report')).toBeTruthy()
    })

    fireEvent.click(screen.getByText('Start Over'))

    await waitFor(() => {
      expect(screen.getByText('Upload Bank Feed')).toBeTruthy()
    })
  })

  it('cancel button resets state during transaction review', async () => {
    api.bankParseFeed.mockResolvedValue({
      ok: true,
      transactions: [
        { date: '2026-01-15', description: 'Payment Acme', amount: 5000, type: 'credit' },
      ],
      count: 1,
    })

    renderPage()
    const input = document.querySelector('input[type="file"]')
    const file = new File(['dummy'], 'feed.csv', { type: 'text/csv' })
    Object.defineProperty(input, 'files', { value: [file] })
    fireEvent.change(input)

    await waitFor(() => {
      expect(screen.getByText('Parsed Transactions (1)')).toBeTruthy()
    })

    fireEvent.click(screen.getByText('Cancel'))

    await waitFor(() => {
      expect(screen.getByText('Upload Bank Feed')).toBeTruthy()
    })
  })
})
