import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import ReleaseNotesModal from '../src/components/ReleaseNotesModal.jsx'

beforeEach(() => {
  localStorage.clear()
  cleanup()
})

describe('ReleaseNotesModal', () => {
  it('renders when last_seen_version is missing', () => {
    render(<ReleaseNotesModal />)
    expect(screen.getByText(/Welcome to OfficePilot v1.0.0/i)).toBeTruthy()
    expect(screen.getByText(/Got it!/i)).toBeTruthy()
  })

  it('renders all 5 highlights with text', () => {
    render(<ReleaseNotesModal />)
    expect(screen.getByText(/Multi-Agent Swarm Architecture/i)).toBeTruthy()
    expect(screen.getByText(/Semantic Bank Reconciliation/i)).toBeTruthy()
    expect(screen.getByText(/Live Voice-Driven Excel Editing/i)).toBeTruthy()
    expect(screen.getByText(/Autonomous Background Watchers/i)).toBeTruthy()
    expect(screen.getByText(/Ollama Local LLM Brain/i)).toBeTruthy()
  })

  it('does not render when last_seen_version equals current version', () => {
    localStorage.setItem('last_seen_version', '1.0.0')
    render(<ReleaseNotesModal />)
    expect(screen.queryByText(/Welcome to OfficePilot v1.0.0/i)).toBeNull()
  })

  it('does not render when last_seen_version is greater than current version', () => {
    localStorage.setItem('last_seen_version', '2.0.0')
    render(<ReleaseNotesModal />)
    expect(screen.queryByText(/Welcome to OfficePilot v1.0.0/i)).toBeNull()
  })

  it('renders when last_seen_version is an older version', () => {
    localStorage.setItem('last_seen_version', '0.36.0')
    render(<ReleaseNotesModal />)
    expect(screen.getByText(/Welcome to OfficePilot v1.0.0/i)).toBeTruthy()
  })

  it('clicking Got it! updates localStorage and calls onClose', () => {
    const onClose = vi.fn()
    render(<ReleaseNotesModal onClose={onClose} />)
    fireEvent.click(screen.getByText(/Got it!/i))
    expect(localStorage.getItem('last_seen_version')).toBe('1.0.0')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it('clicking Got it! unmounts the modal', () => {
    const { container, unmount } = render(<ReleaseNotesModal />)
    expect(screen.getByText(/Got it!/i)).toBeTruthy()
    fireEvent.click(screen.getByText(/Got it!/i))
    expect(screen.queryByText(/Welcome to OfficePilot v1.0.0/i)).toBeNull()
  })
})
