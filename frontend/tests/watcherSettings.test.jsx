import { vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import WatcherSettings from '../src/pages/WatcherSettings.jsx'

const mockApi = vi.hoisted(() => ({
  listWatchers: vi.fn(),
  createWatcher: vi.fn(),
  updateWatcher: vi.fn(),
  deleteWatcher: vi.fn(),
  runWatcherNow: vi.fn(),
}))
vi.mock('../src/api.js', () => ({ api: mockApi }))

const SAMPLE_WATCHERS = [
  {
    id: 1,
    user_id: 1,
    name: 'Gmail Invoice Watcher',
    source_type: 'gmail',
    config_json: { keywords: ['invoice', 'receipt'], days_back: 1 },
    schedule_minutes: 60,
    last_run_at: '2026-06-28T10:00:00Z',
    status: 'active',
    created_at: '2026-06-27T00:00:00Z',
    updated_at: '2026-06-28T10:00:00Z',
  },
  {
    id: 2,
    user_id: 1,
    name: 'Drive Reports Watcher',
    source_type: 'drive',
    config_json: { keywords: ['report'], days_back: 7 },
    schedule_minutes: 120,
    last_run_at: null,
    status: 'paused',
    created_at: '2026-06-26T00:00:00Z',
    updated_at: '2026-06-26T00:00:00Z',
  },
]

beforeEach(() => { vi.clearAllMocks() })

describe('WatcherSettings', () => {
  it('shows loading state initially', () => {
    mockApi.listWatchers.mockReturnValue(new Promise(() => {}))
    render(<MemoryRouter><WatcherSettings /></MemoryRouter>)
    expect(screen.getByText(/Loading watchers/)).toBeTruthy()
  })

  it('renders page header with Eye icon', async () => {
    mockApi.listWatchers.mockResolvedValue({ watchers: [] })
    render(<MemoryRouter><WatcherSettings /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Background Watchers')).toBeTruthy()
    })
    expect(screen.getByText(/Always-on invoice monitoring/)).toBeTruthy()
  })

  it('shows empty state when no watchers', async () => {
    mockApi.listWatchers.mockResolvedValue({ watchers: [] })
    render(<MemoryRouter><WatcherSettings /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText(/No background watchers yet/)).toBeTruthy()
    })
  })

  it('renders watcher list with status badges', async () => {
    mockApi.listWatchers.mockResolvedValue({ watchers: SAMPLE_WATCHERS })
    render(<MemoryRouter><WatcherSettings /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Gmail Invoice Watcher')).toBeTruthy()
    })
    expect(screen.getByText('Drive Reports Watcher')).toBeTruthy()
    expect(screen.getByText('active')).toBeTruthy()
    expect(screen.getByText('paused')).toBeTruthy()
  })

  it('shows schedule interval and last run time', async () => {
    mockApi.listWatchers.mockResolvedValue({ watchers: SAMPLE_WATCHERS })
    render(<MemoryRouter><WatcherSettings /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText(/Every 60 min/)).toBeTruthy()
    })
    expect(screen.getByText(/Every 120 min/)).toBeTruthy()
    expect(screen.getByText(/Never run/)).toBeTruthy()
  })

  it('toggles watcher pause/resume on button click', async () => {
    mockApi.listWatchers.mockResolvedValue({ watchers: [SAMPLE_WATCHERS[0]] })
    mockApi.updateWatcher.mockResolvedValue({})
    render(<MemoryRouter><WatcherSettings /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Gmail Invoice Watcher')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Pause'))
    await waitFor(() => {
      expect(mockApi.updateWatcher).toHaveBeenCalledWith(1, { status: 'paused' })
    })
  })

  it('calls runWatcherNow on Run Now click', async () => {
    mockApi.listWatchers.mockResolvedValue({ watchers: [SAMPLE_WATCHERS[0]] })
    mockApi.runWatcherNow.mockResolvedValue({ message: 'Triggered' })
    render(<MemoryRouter><WatcherSettings /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Gmail Invoice Watcher')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Run Now'))
    await waitFor(() => {
      expect(mockApi.runWatcherNow).toHaveBeenCalledWith(1)
    })
  })

  it('deletes watcher on Delete click with confirm', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockApi.listWatchers.mockResolvedValue({ watchers: [SAMPLE_WATCHERS[0]] })
    mockApi.deleteWatcher.mockResolvedValue({ deleted: true })
    render(<MemoryRouter><WatcherSettings /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Gmail Invoice Watcher')).toBeTruthy()
    })
    fireEvent.click(screen.getByText('Delete'))
    await waitFor(() => {
      expect(mockApi.deleteWatcher).toHaveBeenCalledWith(1)
    })
    confirmSpy.mockRestore()
  })

  it('shows create watcher form and submits', async () => {
    mockApi.listWatchers.mockResolvedValue({ watchers: [] })
    mockApi.createWatcher.mockResolvedValue({ id: 3, name: 'New Watcher', source_type: 'folder', status: 'active', schedule_minutes: 30, config_json: {}, last_run_at: null, created_at: null, updated_at: null })
    render(<MemoryRouter><WatcherSettings /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText(/No background watchers yet/)).toBeTruthy()
    })
    // Open form
    fireEvent.click(screen.getByText('New Watcher'))
    expect(screen.getByPlaceholderText('e.g. Gmail Invoice Watcher')).toBeTruthy()
    // Fill form
    fireEvent.change(screen.getByPlaceholderText('e.g. Gmail Invoice Watcher'), { target: { value: 'Folder Invoice Watcher' } })
    // Select source type
    fireEvent.click(screen.getByText('Local Folder'))
    fireEvent.change(screen.getByDisplayValue('60'), { target: { value: '30' } })
    // Submit
    fireEvent.click(screen.getByText('Create Watcher'))
    await waitFor(() => {
      expect(mockApi.createWatcher).toHaveBeenCalledWith({
        name: 'Folder Invoice Watcher',
        source_type: 'folder',
        config_json: { days_back: 1 },
        schedule_minutes: 30,
      })
    })
  })

  it('shows error message on API failure', async () => {
    mockApi.listWatchers.mockRejectedValue(new Error('Network error'))
    render(<MemoryRouter><WatcherSettings /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeTruthy()
    })
  })
})
