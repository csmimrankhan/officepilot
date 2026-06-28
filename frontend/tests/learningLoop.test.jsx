import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import BackgroundResultCard from '../src/components/agent/BackgroundResultCard.jsx'
import { api } from '../src/api.js'

vi.mock('../src/api.js', () => ({
  api: {
    createCorrection: vi.fn(),
    listCorrections: vi.fn(),
    deleteCorrection: vi.fn(),
  }
}))

const mockTask = {
  id: 1,
  command: 'analyze invoice data',
  status: 'completed',
  completed_at: '2026-06-28T10:00:00Z',
  result_summary_json: {
    invoice_count: 10,
    total_sum: 50000,
    largest_amount: 12000,
    largest_vendor: 'Adobe Inc',
    smallest_amount: 500,
    smallest_vendor: 'OfficeMart',
    summary_english: 'All invoices processed successfully.',
  },
}

describe('Correct This button in BackgroundResultCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders Correct This buttons for largest vendor', () => {
    render(<BackgroundResultCard task={mockTask} />)
    const buttons = screen.getAllByText('Correct This')
    expect(buttons.length).toBeGreaterThanOrEqual(1)
  })

  it('renders Correct This buttons for smallest vendor', () => {
    render(<BackgroundResultCard task={mockTask} />)
    expect(screen.getByText(/OfficeMart/)).toBeTruthy()
    expect(screen.getByText(/Adobe Inc/)).toBeTruthy()
  })

  it('shows inline form when Correct This is clicked', () => {
    render(<BackgroundResultCard task={mockTask} />)
    const correctButtons = screen.getAllByText('Correct This')
    fireEvent.click(correctButtons[0])
    expect(screen.getByPlaceholderText('e.g. Software')).toBeTruthy()
    expect(screen.getByText('Save')).toBeTruthy()
    expect(screen.getByText('Cancel')).toBeTruthy()
  })

  it('submits correction on Save click', async () => {
    api.createCorrection.mockResolvedValue({ status: 'ok', rule_id: 1, message: 'Saved' })
    render(<BackgroundResultCard task={mockTask} />)
    const correctButtons = screen.getAllByText('Correct This')
    fireEvent.click(correctButtons[0])
    const input = screen.getByPlaceholderText('e.g. Software')
    fireEvent.change(input, { target: { value: 'Software' } })
    const saveBtn = screen.getByText('Save')
    fireEvent.click(saveBtn)
    await waitFor(() => {
      expect(api.createCorrection).toHaveBeenCalledWith({
        trigger_vendor: 'Adobe Inc',
        correct_category: 'Software',
        notes: expect.stringContaining('Largest vendor'),
      })
    })
  })

  it('submits correction on Enter key', async () => {
    api.createCorrection.mockResolvedValue({ status: 'ok', rule_id: 1, message: 'Saved' })
    render(<BackgroundResultCard task={mockTask} />)
    const correctButtons = screen.getAllByText('Correct This')
    fireEvent.click(correctButtons[0])
    const input = screen.getByPlaceholderText('e.g. Software')
    fireEvent.change(input, { target: { value: 'Meals' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => {
      expect(api.createCorrection).toHaveBeenCalledWith({
        trigger_vendor: 'Adobe Inc',
        correct_category: 'Meals',
        notes: expect.stringContaining('vendor'),
      })
    })
  })

  it('shows "Rule saved" after successful submission', async () => {
    api.createCorrection.mockResolvedValue({ status: 'ok', rule_id: 1, message: 'Saved' })
    render(<BackgroundResultCard task={mockTask} />)
    const correctButtons = screen.getAllByText('Correct This')
    fireEvent.click(correctButtons[0])
    const input = screen.getByPlaceholderText('e.g. Software')
    fireEvent.change(input, { target: { value: 'Software' } })
    fireEvent.click(screen.getByText('Save'))
    await waitFor(() => {
      expect(screen.getByText(/Rule saved/)).toBeTruthy()
    })
  })

  it('hides form on Cancel click', () => {
    render(<BackgroundResultCard task={mockTask} />)
    const correctButtons = screen.getAllByText('Correct This')
    fireEvent.click(correctButtons[0])
    expect(screen.getByPlaceholderText('e.g. Software')).toBeTruthy()
    fireEvent.click(screen.getByText('Cancel'))
    expect(screen.queryByPlaceholderText('e.g. Software')).toBeNull()
  })
})
