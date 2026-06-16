import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import StatusBadge from '../src/components/StatusBadge.jsx'
import ConfidenceBar from '../src/components/ConfidenceBar.jsx'

describe('StatusBadge', () => {
  it('renders the human label', () => {
    render(<StatusBadge status="needs_review" />)
    expect(screen.getByText('Needs Review')).toBeInTheDocument()
  })
  it('falls back to raw value', () => {
    render(<StatusBadge status="mystery" />)
    expect(screen.getByText('mystery')).toBeInTheDocument()
  })
})

describe('ConfidenceBar', () => {
  it('clamps to 0-100%', () => {
    const { container } = render(<ConfidenceBar value={1.5} />)
    const inner = container.querySelector('.confidence-bar > span')
    expect(inner.style.width).toBe('100%')
  })
  it('renders 0% for missing values', () => {
    const { container } = render(<ConfidenceBar value={null} />)
    const inner = container.querySelector('.confidence-bar > span')
    expect(inner.style.width).toBe('0%')
  })
})
