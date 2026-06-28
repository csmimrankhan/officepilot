import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import ResourceMonitor from '../src/pages/ResourceMonitor.jsx'

const mockResources = {
  python_memory_mb: 256.5,
  vector_store_mb: 42.3,
  orphaned_excel_count: 2,
  orphaned_excel_pids: [1234, 5678],
}

vi.mock('../src/api.js', () => ({
  getSystemResources: vi.fn(),
  optimizeClearMemory: vi.fn(),
  optimizeKillExcel: vi.fn(),
}))

import { getSystemResources, optimizeClearMemory, optimizeKillExcel } from '../src/api.js'

beforeEach(() => {
  cleanup()
  vi.clearAllMocks()
  getSystemResources.mockResolvedValue(mockResources)
  window.confirm = vi.fn(() => true)
})

describe('ResourceMonitor', () => {
  it('renders loading state initially', () => {
    getSystemResources.mockImplementation(() => new Promise(() => {}))
    render(<ResourceMonitor />)
    expect(screen.getByText(/Loading system resources/i)).toBeTruthy()
  })

  it('renders error state on fetch failure', async () => {
    getSystemResources.mockRejectedValue(new Error('Network error'))
    render(<ResourceMonitor />)
    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeTruthy()
    })
  })

  it('renders three stat cards with data', async () => {
    render(<ResourceMonitor />)
    await waitFor(() => {
      expect(screen.getByText('256.5')).toBeTruthy()
      expect(screen.getByText(/Vector DB Size/i)).toBeTruthy()
      expect(screen.getAllByText(/Orphaned Excel/i).length).toBeGreaterThanOrEqual(1)
    })
    expect(screen.getByText('42.3')).toBeTruthy()
    expect(screen.getByText('2')).toBeTruthy()
  })

  it('renders Clear Vector Memory button', async () => {
    render(<ResourceMonitor />)
    await waitFor(() => {
      expect(screen.getByText(/Clear Vector Memory/i)).toBeTruthy()
    })
  })

  it('renders Kill Orphaned Excel button', async () => {
    render(<ResourceMonitor />)
    await waitFor(() => {
      const btn = screen.getByText(/Kill Orphaned Excel/i)
      expect(btn).toBeTruthy()
      expect(btn.disabled).toBe(false)
    })
  })

  it('calls optimizeClearMemory when Clear Vector Memory is clicked', async () => {
    optimizeClearMemory.mockResolvedValue({ status: 'ok' })
    render(<ResourceMonitor />)
    await waitFor(() => {
      fireEvent.click(screen.getByText(/Clear Vector Memory/i))
    })
    expect(window.confirm).toHaveBeenCalled()
    expect(optimizeClearMemory).toHaveBeenCalled()
  })

  it('calls optimizeKillExcel when Kill Orphaned Excel is clicked', async () => {
    optimizeKillExcel.mockResolvedValue({ status: 'ok', detail: 'Terminated 2 orphaned Excel process(es)' })
    render(<ResourceMonitor />)
    await waitFor(() => {
      fireEvent.click(screen.getByText(/Kill Orphaned Excel/i))
    })
    expect(window.confirm).toHaveBeenCalled()
    expect(optimizeKillExcel).toHaveBeenCalled()
  })

  it('disables Kill Excel button when count is zero', async () => {
    getSystemResources.mockResolvedValue({ ...mockResources, orphaned_excel_count: 0, orphaned_excel_pids: [] })
    render(<ResourceMonitor />)
    await waitFor(() => {
      const btn = screen.getByText(/Kill Orphaned Excel/i)
      expect(btn.disabled).toBe(true)
    })
  })
})
