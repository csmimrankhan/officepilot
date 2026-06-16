import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import VoiceRecorder from '../src/pages/VoiceRecorder.jsx'
import { api } from '../src/api.js'

vi.mock('../src/api.js', () => ({
  api: {
    recorderStart: vi.fn(),
    recorderStop: vi.fn(),
    recorderListEvents: vi.fn(),
    recorderRecordEvent: vi.fn(),
    recorderConvertToSkill: vi.fn(),
    recorderApproveDraft: vi.fn(),
    recorderRejectDraft: vi.fn(),
    recorderSaveAsSkill: vi.fn(),
    recorderCurrent: vi.fn(),
    recorderCancel: vi.fn(),
  }
}))

// Mock MediaRecorder and getUserMedia
beforeEach(() => {
  vi.clearAllMocks()
  global.navigator.mediaDevices = {
    getUserMedia: vi.fn().mockResolvedValue({
      getTracks: () => [{ stop: vi.fn() }],
    }),
  }
  global.MediaRecorder = vi.fn().mockImplementation(() => ({
    start: vi.fn(),
    stop: vi.fn(() => {
      if (global.MediaRecorder.instance?.onstop) global.MediaRecorder.instance.onstop()
    }),
    state: 'inactive',
  }))
  global.MediaRecorder.instance = null
  global.MediaRecorder.mockImplementation(function () {
    const instance = {
      start: vi.fn(function () { this.state = 'recording'; global.MediaRecorder.instance = this }),
      stop: vi.fn(function () {
        this.state = 'inactive'
        if (this.onstop) this.onstop()
      }),
      state: 'inactive',
      ondataavailable: null,
      onstop: null,
    }
    return instance
  })
  delete global.MediaRecorder.isTypeSupported
  global.MediaRecorder.isTypeSupported = () => true
  global.fetch = vi.fn()
  global.localStorage.setItem('auth_token', 'test-token')
})

function renderVR() {
  return render(
    <MemoryRouter>
      <VoiceRecorder />
    </MemoryRouter>
  )
}

describe('VoiceRecorder', () => {
  it('renders idle state with microphone button', () => {
    renderVR()
    expect(screen.getByText('Voice Recorder')).toBeInTheDocument()
    expect(screen.getByText('Tap the microphone to start')).toBeInTheDocument()
    expect(screen.getByLabelText('Start recording')).toBeInTheDocument()
  })

  it('starts recording when mic is clicked', async () => {
    api.recorderStart.mockResolvedValue({ session_id: 1, status: 'recording', title: 'Voice Recording', started_at: new Date().toISOString() })
    renderVR()
    fireEvent.click(screen.getByLabelText('Start recording'))
    await waitFor(() => {
      expect(api.recorderStart).toHaveBeenCalled()
    })
    await waitFor(() => {
      expect(screen.getByText(/RECORDING/)).toBeInTheDocument()
    })
  })

  it('stops recording on second click', async () => {
    api.recorderStart.mockResolvedValue({ session_id: 1, status: 'recording', title: 'VR' })
    api.recorderStop.mockResolvedValue({ session_id: 1, status: 'stopped', event_count: 3 })
    api.recorderListEvents.mockResolvedValue([
      { event_order: 1, event_type: 'click', target_description: 'Clicked Approve', redacted: false },
      { event_order: 2, event_type: 'type_text', target_description: 'Typed vendor', redacted: false },
    ])
    renderVR()
    fireEvent.click(screen.getByLabelText('Start recording'))
    await waitFor(() => expect(screen.getByLabelText('Stop recording')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Stop recording'))
    await waitFor(() => {
      expect(api.recorderStop).toHaveBeenCalledWith(1)
    })
    await waitFor(() => {
      expect(screen.getByText(/Recording complete/)).toBeInTheDocument()
    })
  })

  it('shows events after stop', async () => {
    api.recorderStart.mockResolvedValue({ session_id: 1, status: 'recording', title: 'VR' })
    api.recorderStop.mockResolvedValue({ session_id: 1, status: 'stopped', event_count: 2 })
    api.recorderListEvents.mockResolvedValue([
      { event_order: 1, event_type: 'click', target_description: 'Clicked Approve', redacted: false },
    ])
    renderVR()
    fireEvent.click(screen.getByLabelText('Start recording'))
    await waitFor(() => expect(screen.getByLabelText('Stop recording')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Stop recording'))
    await waitFor(() => {
      expect(screen.getByText('Clicked Approve')).toBeInTheDocument()
    })
  })

  it('convert to skill button appears after stop', async () => {
    api.recorderStart.mockResolvedValue({ session_id: 1, status: 'recording', title: 'VR' })
    api.recorderStop.mockResolvedValue({ session_id: 1, status: 'stopped', event_count: 1 })
    api.recorderListEvents.mockResolvedValue([])
    renderVR()
    fireEvent.click(screen.getByLabelText('Start recording'))
    await waitFor(() => expect(screen.getByLabelText('Stop recording')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Stop recording'))
    await waitFor(() => {
      expect(screen.getByText('Convert to Skill')).toBeInTheDocument()
    })
  })

  it('convert to skill calls API and shows draft', async () => {
    api.recorderStart.mockResolvedValue({ session_id: 1, status: 'recording', title: 'VR' })
    api.recorderStop.mockResolvedValue({ session_id: 1, status: 'stopped', event_count: 1 })
    api.recorderListEvents.mockResolvedValue([])
    api.recorderConvertToSkill.mockResolvedValue({
      draft_id: 1, name: 'My Skill', trigger_phrases: ['run my skill'], steps: [{ tool_name: 'approval', description: 'Ask approval' }], status: 'draft'
    })
    renderVR()
    fireEvent.click(screen.getByLabelText('Start recording'))
    await waitFor(() => expect(screen.getByLabelText('Stop recording')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Stop recording'))
    await waitFor(() => expect(screen.getByText('Convert to Skill')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Convert to Skill'))
    await waitFor(() => {
      expect(api.recorderConvertToSkill).toHaveBeenCalled()
    })
    await waitFor(() => {
      expect(screen.getByText(/Skill Draft: My Skill/)).toBeInTheDocument()
    })
  })

  it('approve and save skill works', async () => {
    api.recorderStart.mockResolvedValue({ session_id: 1, status: 'recording', title: 'VR' })
    api.recorderStop.mockResolvedValue({ session_id: 1, status: 'stopped', event_count: 1 })
    api.recorderListEvents.mockResolvedValue([])
    api.recorderConvertToSkill.mockResolvedValue({
      draft_id: 1, name: 'My Skill', trigger_phrases: ['run'], steps: [], status: 'draft'
    })
    api.recorderApproveDraft.mockResolvedValue({ status: 'approved' })
    api.recorderSaveAsSkill.mockResolvedValue({ skill_id: 42, name: 'My Skill' })
    renderVR()
    fireEvent.click(screen.getByLabelText('Start recording'))
    await waitFor(() => expect(screen.getByLabelText('Stop recording')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Stop recording'))
    await waitFor(() => expect(screen.getByText('Convert to Skill')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Convert to Skill'))
    await waitFor(() => expect(screen.getByText('Approve & Save Skill')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Approve & Save Skill'))
    await waitFor(() => {
      expect(api.recorderSaveAsSkill).toHaveBeenCalledWith(1)
    })
    await waitFor(() => {
      expect(screen.getByText(/Record Another/)).toBeInTheDocument()
    })
  })

  it('discard button resets state', async () => {
    api.recorderStart.mockResolvedValue({ session_id: 1, status: 'recording', title: 'VR' })
    api.recorderStop.mockResolvedValue({ session_id: 1, status: 'stopped', event_count: 1 })
    api.recorderListEvents.mockResolvedValue([])
    renderVR()
    fireEvent.click(screen.getByLabelText('Start recording'))
    await waitFor(() => expect(screen.getByLabelText('Stop recording')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Stop recording'))
    await waitFor(() => expect(screen.getByText('Discard')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Discard'))
    await waitFor(() => {
      expect(screen.getByText('Tap the microphone to start')).toBeInTheDocument()
    })
  })

  it('shows error state on failure', async () => {
    api.recorderStart.mockRejectedValue(new Error('Microphone access denied'))
    renderVR()
    fireEvent.click(screen.getByLabelText('Start recording'))
    await waitFor(() => {
      expect(screen.getByText(/Microphone/)).toBeInTheDocument()
    })
  })
})
