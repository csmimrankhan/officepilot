import { vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import BackgroundTaskWidget from '../src/components/agent/BackgroundTaskWidget.jsx'
import BackgroundResultCard from '../src/components/agent/BackgroundResultCard.jsx'

const mockApi = vi.hoisted(() => ({
  getBackgroundTasks: vi.fn(),
  cancelBackgroundTask: vi.fn(),
}))
vi.mock('../src/api.js', () => ({ api: mockApi }))

beforeEach(() => { vi.clearAllMocks() })

describe('BackgroundTaskWidget', () => {
  it('renders nothing when no tasks exist', () => {
    mockApi.getBackgroundTasks.mockResolvedValue([])
    const { container } = render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    expect(container.innerHTML).toBe('')
  })

  it('renders pulsing icon with count when tasks are running', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 1, command: 'analyze invoices', status: 'running', progress_percent: 45, current_step_description: 'Processing file 3 of 10' },
      { id: 2, command: 'download from drive', status: 'queued', progress_percent: 0, current_step_description: 'Waiting...' },
    ])
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('2')).toBeTruthy()
    })
    expect(screen.getByTitle('2 background tasks running')).toBeTruthy()
  })

  it('shows dropdown on click with task details', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 1, command: 'analyze invoice dataset', status: 'running', progress_percent: 60, current_step_description: 'Analyzing row 50 of 100' },
    ])
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('1')).toBeTruthy()
    })
    fireEvent.click(screen.getByTitle('1 background task running'))
    expect(screen.getByText(/analyze invoice dataset/)).toBeTruthy()
    expect(screen.getByText('Analyzing row 50 of 100')).toBeTruthy()
    expect(screen.getByText('60%')).toBeTruthy()
    expect(screen.getByText('Cancel')).toBeTruthy()
  })

  it('calls cancelBackgroundTask when Cancel clicked', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 42, command: 'background analysis', status: 'running', progress_percent: 30 },
    ])
    mockApi.cancelBackgroundTask.mockResolvedValue({})
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('1')).toBeTruthy() })
    fireEvent.click(screen.getByTitle('1 background task running'))
    fireEvent.click(screen.getByText('Cancel'))
    await waitFor(() => {
      expect(mockApi.cancelBackgroundTask).toHaveBeenCalledWith(42)
    })
  })

  it('shows completed tasks in dropdown', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 1, command: 'completed analysis', status: 'completed', progress_percent: 100 },
    ])
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByTitle('Background tasks')).toBeTruthy()
    })
    fireEvent.click(screen.getByTitle('Background tasks'))
    expect(screen.getByText(/Background Tasks/)).toBeTruthy()
    expect(screen.getByText(/completed analysis/)).toBeTruthy()
  })
})

describe('BackgroundResultCard', () => {
  const completedResult = {
    id: 1,
    command: 'analyze invoice dataset',
    status: 'completed',
    completed_at: '2026-06-28T10:30:00Z',
    result_summary_json: {
      total_sum: 15250.75,
      invoice_count: 12,
      average_amount: 1270.90,
      largest_amount: 3200.00,
      largest_vendor: 'TechCorp Inc.',
      smallest_amount: 150.25,
      smallest_vendor: 'Local Shop',
      excel_file_path: 'C:\\invoices\\summary.xlsx',
    },
  }

  const failedResult = {
    id: 2,
    command: 'analyze bad data',
    status: 'failed',
    error_message: 'Invalid invoice format in row 5: missing vendor column',
  }

  it('renders success icon and status', () => {
    render(<MemoryRouter><BackgroundResultCard task={completedResult} /></MemoryRouter>)
    expect(screen.getByText('Background Task Complete')).toBeTruthy()
    expect(screen.getByText('completed')).toBeTruthy()
  })

  it('formats min/max amounts correctly', () => {
    render(<MemoryRouter><BackgroundResultCard task={completedResult} /></MemoryRouter>)
    expect(screen.getByText(/12/)).toBeTruthy()
    expect(screen.getByText(/\$15,250\.75/)).toBeTruthy()
    expect(screen.getByText(/\$3,200\.00/)).toBeTruthy()
    expect(screen.getByText(/TechCorp Inc\./)).toBeTruthy()
    expect(screen.getByText(/\$150\.25/)).toBeTruthy()
    expect(screen.getByText(/Local Shop/)).toBeTruthy()
    expect(screen.getByText(/\$1,270\.90/)).toBeTruthy()
  })

  it('renders Open Excel File button when excel_file_path exists', () => {
    render(<MemoryRouter><BackgroundResultCard task={completedResult} /></MemoryRouter>)
    expect(screen.getByText('Open Excel File')).toBeTruthy()
  })

  it('calls onOpenFile when Open Excel File clicked', () => {
    const onOpenFile = vi.fn()
    render(<MemoryRouter><BackgroundResultCard task={completedResult} onOpenFile={onOpenFile} /></MemoryRouter>)
    fireEvent.click(screen.getByText('Open Excel File'))
    expect(onOpenFile).toHaveBeenCalledWith('C:\\invoices\\summary.xlsx')
  })

  it('renders failed status and error message', () => {
    render(<MemoryRouter><BackgroundResultCard task={failedResult} /></MemoryRouter>)
    expect(screen.getByText('Background Task Failed')).toBeTruthy()
    expect(screen.getByText(/Invalid invoice format/)).toBeTruthy()
  })

  it('renders completed time', () => {
    render(<MemoryRouter><BackgroundResultCard task={completedResult} /></MemoryRouter>)
    expect(screen.getByText(/2026/)).toBeTruthy()
  })

  it('returns null when task is null', () => {
    const { container } = render(<MemoryRouter><BackgroundResultCard task={null} /></MemoryRouter>)
    expect(container.innerHTML).toBe('')
  })

  it('renders without result_summary_json if missing', () => {
    const minimal = { id: 3, command: 'minimal task', status: 'completed' }
    render(<MemoryRouter><BackgroundResultCard task={minimal} /></MemoryRouter>)
    expect(screen.getByText('Background Task Complete')).toBeTruthy()
  })
})
