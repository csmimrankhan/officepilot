import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import Landing from '../src/pages/Landing.jsx'
import FAQPage from '../src/pages/FAQPage.jsx'

describe('Landing v1.0.0 copy', () => {
  it('renders the new hero subtitle', () => {
    render(<Landing />)
    expect(screen.getByText(/Autonomous AI Accounting Firm/i)).toBeTruthy()
  })

  it('renders the Live Voice Editing step', () => {
    render(<Landing />)
    expect(screen.getByText(/Live Voice Editing/i)).toBeTruthy()
  })

  it('renders Multi-Agent Swarm badge', () => {
    render(<Landing />)
    expect(screen.getByText(/Multi-Agent Swarm/i)).toBeTruthy()
  })

  it('renders Semantic Bank Recon badge', () => {
    render(<Landing />)
    expect(screen.getByText(/Semantic Bank Recon/i)).toBeTruthy()
  })

  it('renders the Live Voice Editing description in steps', () => {
    render(<Landing />)
    expect(screen.getByText(/toggle Live Mode/i)).toBeTruthy()
  })
})

describe('FAQPage v1.0.0 copy', () => {
  it('renders the new Excel files FAQ', () => {
    render(<FAQPage />)
    expect(screen.getByText(/Does OfficePilot work with my existing Excel files/i)).toBeTruthy()
  })

  it('renders the new Bank Reconciliation FAQ', () => {
    render(<FAQPage />)
    expect(screen.getByText(/How does the Bank Reconciliation work/i)).toBeTruthy()
  })

  it('renders the Bank Reconciliation answer mentioning Semantic Memory', () => {
    render(<FAQPage />)
    expect(screen.getByText(/Semantic Memory/i)).toBeTruthy()
  })
})
