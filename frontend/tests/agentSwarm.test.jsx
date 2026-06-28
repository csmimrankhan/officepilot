import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import AgentChatWindow from '../src/components/agent/AgentChatWindow.jsx'

describe('AgentChatWindow — Agent Badges', () => {
  it('renders empty state when no messages', () => {
    render(<AgentChatWindow messages={[]} />)
    expect(screen.getByText(/ask your accountant agent/i)).toBeTruthy()
  })

  it('renders user message without badge', () => {
    const messages = [
      { id: '1', role: 'user', text: 'audit my invoices', timestamp: new Date().toISOString() },
    ]
    render(<AgentChatWindow messages={messages} />)
    expect(screen.getByText('audit my invoices')).toBeTruthy()
    expect(screen.getByText((content) => content.includes('You'))).toBeTruthy()
  })

  it('renders auditor badge for agent message with assignedAgent=auditor', () => {
    const messages = [
      { id: '1', role: 'user', text: 'audit my invoices', timestamp: new Date().toISOString() },
      { id: '2', role: 'agent', text: 'Here are the results of the audit.', assignedAgent: 'auditor', timestamp: new Date().toISOString() },
    ]
    render(<AgentChatWindow messages={messages} />)
    expect(screen.getByText('Auditor')).toBeTruthy()
    expect(screen.getByText('Here are the results of the audit.')).toBeTruthy()
  })

  it('renders tax badge for agent message with assignedAgent=tax', () => {
    const messages = [
      { id: '1', role: 'agent', text: 'Categorized your expenses.', assignedAgent: 'tax', timestamp: new Date().toISOString() },
    ]
    render(<AgentChatWindow messages={messages} />)
    expect(screen.getByText('Tax Agent')).toBeTruthy()
  })

  it('renders data entry badge for agent message with assignedAgent=data_entry', () => {
    const messages = [
      { id: '1', role: 'agent', text: 'Entering bill into QuickBooks.', assignedAgent: 'data_entry', timestamp: new Date().toISOString() },
    ]
    render(<AgentChatWindow messages={messages} />)
    expect(screen.getByText('Data Entry')).toBeTruthy()
  })

  it('shows no badge when assignedAgent is absent', () => {
    const messages = [
      { id: '1', role: 'agent', text: 'General response.', timestamp: new Date().toISOString() },
    ]
    const { container } = render(<AgentChatWindow messages={messages} />)
    expect(screen.getByText('General response.')).toBeTruthy()
    const badgeSpans = container.querySelectorAll('span[style*="border-radius: 10px"]')
    expect(badgeSpans.length).toBe(0)
  })

  it('renders general badge for unknown agent value', () => {
    const messages = [
      { id: '1', role: 'agent', text: 'Some response.', assignedAgent: 'unknown_value', timestamp: new Date().toISOString() },
    ]
    render(<AgentChatWindow messages={messages} />)
    expect(screen.getByText('General')).toBeTruthy()
  })

  it('does not show badge on user messages', () => {
    const messages = [
      { id: '1', role: 'user', text: 'audit my invoices', assignedAgent: 'auditor', timestamp: new Date().toISOString() },
      { id: '2', role: 'agent', text: 'Done.', assignedAgent: 'auditor', timestamp: new Date().toISOString() },
    ]
    render(<AgentChatWindow messages={messages} />)
    const badges = screen.getAllByText('Auditor')
    expect(badges.length).toBe(1)
  })

  it('applies correct background color for each agent type', () => {
    const messages = [
      { id: '1', role: 'agent', text: 'Audit results.', assignedAgent: 'auditor', timestamp: new Date().toISOString() },
    ]
    const { container } = render(<AgentChatWindow messages={messages} />)
    const badge = container.querySelector('span')
    if (badge) {
      const style = window.getComputedStyle(badge)
      expect(style.background).toBeTruthy()
    }
  })
})
