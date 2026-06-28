import { vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import BackgroundTaskWidget from '../src/components/agent/BackgroundTaskWidget.jsx'

const mockApi = vi.hoisted(() => ({
  getBackgroundTasks: vi.fn(),
  cancelBackgroundTask: vi.fn(),
  answerBackgroundTask: vi.fn(),
}))
vi.mock('../src/api.js', () => ({ api: mockApi }))

beforeEach(() => { vi.clearAllMocks() })

describe('BackgroundTaskWidget — Needs Attention / Recovery', () => {

  it('shows Needs Attention badge with AlertTriangle icon for paused_for_input tasks', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 1, command: 'extract invoice', status: 'paused_for_input', clarification_question: 'What is the total amount?', current_step_description: 'Paused: need input to proceed' },
    ])
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('1')).toBeTruthy()
    })
    expect(screen.getByTitle('1 task(s) need attention')).toBeTruthy()
  })

  it('shows clarification question and text input when dropdown opened', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 1, command: 'extract invoice', status: 'paused_for_input', clarification_question: 'I could not read the total on invoice.pdf. Can you tell me the amount?', current_step_description: 'Paused: need input' },
    ])
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('1')).toBeTruthy()
    })
    fireEvent.click(screen.getByTitle('1 task(s) need attention'))
    expect(screen.getByText(/I could not read the total/i)).toBeTruthy()
    expect(screen.getByPlaceholderText('Type your answer...')).toBeTruthy()
    expect(screen.getByText('Send')).toBeTruthy()
  })

  it('shows "Needs Attention" badge text instead of raw status', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 1, command: 'test', status: 'paused_for_input', clarification_question: 'What is the total?' },
    ])
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('1')).toBeTruthy() })
    fireEvent.click(screen.getByTitle('1 task(s) need attention'))
    expect(screen.getByText('Needs Attention')).toBeTruthy()
  })

  it('calls answerBackgroundTask when Send button clicked', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 5, command: 'test answer', status: 'paused_for_input', clarification_question: 'What is the total?', current_step_description: 'Paused' },
    ])
    mockApi.answerBackgroundTask.mockResolvedValue({ task_id: 5, status: 'running' })
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('1')).toBeTruthy() })
    fireEvent.click(screen.getByTitle('1 task(s) need attention'))
    const input = screen.getByPlaceholderText('Type your answer...')
    fireEvent.change(input, { target: { value: 'The total is $500' } })
    fireEvent.click(screen.getByText('Send'))
    await waitFor(() => {
      expect(mockApi.answerBackgroundTask).toHaveBeenCalledWith(5, 'The total is $500')
    })
  })

  it('disables Send button when input is empty', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 6, command: 'test', status: 'paused_for_input', clarification_question: 'What?', current_step_description: 'Paused' },
    ])
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('1')).toBeTruthy() })
    fireEvent.click(screen.getByTitle('1 task(s) need attention'))
    expect(screen.getByText('Send').disabled).toBe(true)
  })

  it('shows Sending... while answer is being submitted', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 7, command: 'test', status: 'paused_for_input', clarification_question: 'What?', current_step_description: 'Paused' },
    ])
    mockApi.answerBackgroundTask.mockImplementation(() => new Promise(() => {}))
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('1')).toBeTruthy() })
    fireEvent.click(screen.getByTitle('1 task(s) need attention'))
    const input = screen.getByPlaceholderText('Type your answer...')
    fireEvent.change(input, { target: { value: 'answer' } })
    fireEvent.click(screen.getByText('Send'))
    await waitFor(() => {
      expect(screen.getByText('Sending...')).toBeTruthy()
    })
  })

  it('submits answer on Enter key press', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 8, command: 'test', status: 'paused_for_input', clarification_question: 'What?', current_step_description: 'Paused' },
    ])
    mockApi.answerBackgroundTask.mockResolvedValue({ task_id: 8, status: 'running' })
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('1')).toBeTruthy() })
    fireEvent.click(screen.getByTitle('1 task(s) need attention'))
    const input = screen.getByPlaceholderText('Type your answer...')
    fireEvent.change(input, { target: { value: 'my answer' } })
    fireEvent.keyDown(input, { key: 'Enter' })
    await waitFor(() => {
      expect(mockApi.answerBackgroundTask).toHaveBeenCalledWith(8, 'my answer')
    })
  })

  it('shows Cancel button for paused_for_input tasks', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 9, command: 'test', status: 'paused_for_input', clarification_question: 'What?', current_step_description: 'Paused' },
    ])
    mockApi.cancelBackgroundTask.mockResolvedValue({})
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => { expect(screen.getByText('1')).toBeTruthy() })
    fireEvent.click(screen.getByTitle('1 task(s) need attention'))
    expect(screen.getByText('Cancel')).toBeTruthy()
    fireEvent.click(screen.getByText('Cancel'))
    await waitFor(() => {
      expect(mockApi.cancelBackgroundTask).toHaveBeenCalledWith(9)
    })
  })

  it('counts paused_for_input tasks in Needs Attention badge', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 10, command: 'task A', status: 'paused_for_input', clarification_question: 'Q1', current_step_description: 'Paused' },
      { id: 11, command: 'task B', status: 'paused_for_input', clarification_question: 'Q2', current_step_description: 'Paused' },
      { id: 12, command: 'task C', status: 'running', progress_percent: 50, current_step_description: 'Working' },
    ])
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('2')).toBeTruthy()
    })
    expect(screen.getByTitle('2 task(s) need attention')).toBeTruthy()
  })

  it('shows normal task count when no paused tasks exist', async () => {
    mockApi.getBackgroundTasks.mockResolvedValue([
      { id: 13, command: 'running task', status: 'running', progress_percent: 50, current_step_description: 'Processing' },
    ])
    render(<MemoryRouter><BackgroundTaskWidget /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('1')).toBeTruthy()
    })
    expect(screen.getByTitle('1 background task running')).toBeTruthy()
  })

})
