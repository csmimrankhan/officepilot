import { vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import BackgroundResultCard from '../src/components/agent/BackgroundResultCard.jsx'

const mockApi = vi.hoisted(() => ({
  createCorrection: vi.fn(),
}))
vi.mock('../src/api.js', () => ({ api: mockApi }))

const completedTask = (overrides = {}) => ({
  id: 1,
  command: 'analyze invoices',
  status: 'completed',
  result_summary_json: {
    invoice_count: 5,
    total_sum: 15000.00,
    total_amount: 15000.00,
    average_amount: 3000.00,
    largest_amount: 8000.00,
    largest_vendor: 'Acme Corp',
    smallest_amount: 500.00,
    smallest_vendor: 'OfficeMart',
    ...overrides,
  },
  completed_at: '2026-06-28T04:00:00Z',
})

describe('BackgroundResultCard — PushToQuickBooks', () => {

  it('renders Push to QuickBooks button for completed tasks with totals', () => {
    render(<BackgroundResultCard task={completedTask()} />)
    expect(screen.getByText('Push to QuickBooks')).toBeTruthy()
  })

  it('does not render button when total_sum and total_amount are null', () => {
    const task = completedTask({ total_sum: null, total_amount: null })
    render(<BackgroundResultCard task={task} />)
    expect(screen.queryByText('Push to QuickBooks')).toBeNull()
  })

  it('calls onPushToQuickBooks with correct params when clicked', async () => {
    const onPush = vi.fn().mockResolvedValue({ success: true })
    render(<BackgroundResultCard task={completedTask()} onPushToQuickBooks={onPush} />)
    fireEvent.click(screen.getByText('Push to QuickBooks'))
    await waitFor(() => {
      expect(onPush).toHaveBeenCalledWith({
        vendor_name: 'Acme Corp',
        total_amount: 15000.00,
        line_items: [{ description: 'Invoice processing', amount: 15000.00 }],
        due_date: expect.any(String),
      })
    })
  })

  it('shows Pushing... while sending', async () => {
    const onPush = vi.fn().mockImplementation(() => new Promise(() => {}))
    render(<BackgroundResultCard task={completedTask()} onPushToQuickBooks={onPush} />)
    fireEvent.click(screen.getByText('Push to QuickBooks'))
    await waitFor(() => {
      expect(screen.getByText('Pushing...')).toBeTruthy()
    })
  })

  it('returns to Push to QuickBooks text after completion', async () => {
    const onPush = vi.fn().mockResolvedValue({ success: true })
    render(<BackgroundResultCard task={completedTask()} onPushToQuickBooks={onPush} />)
    fireEvent.click(screen.getByText('Push to QuickBooks'))
    await waitFor(() => {
      expect(screen.getByText('Push to QuickBooks')).toBeTruthy()
    })
  })
})
