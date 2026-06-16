import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Sidebar from '../src/components/layout/Sidebar.jsx'

function renderSidebar(user = null, isOwnerOrAdmin = false, mobileOpen = false) {
  return render(
    <MemoryRouter initialEntries={['/app/agent']}>
      <Sidebar user={user || { email: 'test@test.com', role: 'user' }} isOwnerOrAdmin={isOwnerOrAdmin} mobileOpen={mobileOpen} onMobileClose={vi.fn()} />
    </MemoryRouter>
  )
}

const EMOJI_PATTERN = /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{200D}\u{20E3}\u{231A}\u{231B}\u{23E9}-\u{23F3}\u{23F8}-\u{23FA}\u{25AA}\u{25AB}\u{25B6}\u{25C0}\u{25FB}-\u{25FE}]/u

describe('Sidebar Visual Consistency', () => {
  it('does not contain emoji characters', () => {
    const { container } = renderSidebar(null, true)
    const text = container.textContent
    expect(EMOJI_PATTERN.test(text)).toBe(false)
  })

  it('renders New Task button once', () => {
    renderSidebar(null, true)
    const buttons = screen.getAllByText('New Task')
    expect(buttons.length).toBe(1)
  })

  it('New Task button contains Plus icon', () => {
    const { container } = renderSidebar(null, true)
    const newTaskBtn = container.querySelector('.new-task-button')
    expect(newTaskBtn).toBeTruthy()
    expect(newTaskBtn.querySelector('svg')).toBeTruthy()
  })

  it('all nav rows use nav-item class', () => {
    const { container } = renderSidebar(null, true)
    const navItems = container.querySelectorAll('.nav-item')
    expect(navItems.length).toBeGreaterThanOrEqual(4)
  })

  it('all icons render inside nav-icon wrapper', () => {
    const { container } = renderSidebar(null, true)
    const navIcons = container.querySelectorAll('.nav-icon')
    navIcons.forEach(icon => {
      expect(icon.querySelector('svg')).toBeTruthy()
    })
  })

  it('renders section titles (MAIN, WORKSPACE, ADMIN, ADVANCED)', () => {
    renderSidebar(null, true)
    expect(screen.getByText('MAIN')).toBeTruthy()
    expect(screen.getByText('WORKSPACE')).toBeTruthy()
    expect(screen.getByText('ADMIN')).toBeTruthy()
    expect(screen.getByText('ADVANCED')).toBeTruthy()
  })

  it('shows admin nav for admin/owner user', () => {
    renderSidebar({ email: 'admin@test.com', role: 'owner' }, true)
    expect(screen.getByText('Dashboard')).toBeTruthy()
    expect(screen.getByText('Users')).toBeTruthy()
    expect(screen.getByText('Audit Logs')).toBeTruthy()
  })

  it('does not show admin nav for normal user', () => {
    renderSidebar({ email: 'user@test.com', role: 'user' }, false)
    expect(screen.queryByText('Dashboard')).toBeNull()
    expect(screen.queryByText('Users')).toBeNull()
    expect(screen.queryByText('Audit Logs')).toBeNull()
  })

  it('shows main navigation items for all users', () => {
    renderSidebar(null, false)
    expect(screen.getByText('Agent')).toBeTruthy()
    expect(screen.getByText('Skills')).toBeTruthy()
    expect(screen.getByText('Workflow Memory')).toBeTruthy()
    expect(screen.getByText('Version History')).toBeTruthy()
  })

  it('shows workspace items for all users', () => {
    renderSidebar(null, false)
    expect(screen.getByText('Settings')).toBeTruthy()
    expect(screen.getByText('Safety')).toBeTruthy()
  })

  it('renders Agent Ready status', () => {
    renderSidebar(null, false)
    expect(screen.getByText('Agent Ready')).toBeTruthy()
  })

  // ── Route link regression tests ─────────────────────────────────

  it('sidebar Agent link points to /app/agent', () => {
    renderSidebar(null, false)
    const link = screen.getByText('Agent').closest('a')
    expect(link).toBeTruthy()
    expect(link.getAttribute('href')).toBe('/app/agent')
  })

  it('sidebar Skills link points to /app/skills', () => {
    renderSidebar(null, false)
    const link = screen.getByText('Skills').closest('a')
    expect(link.getAttribute('href')).toBe('/app/skills')
  })

  it('sidebar Version History link points to /app/version-history', () => {
    renderSidebar(null, false)
    const link = screen.getByText('Version History').closest('a')
    expect(link.getAttribute('href')).toBe('/app/version-history')
  })

  it('sidebar Safety link points to /app/safety', () => {
    renderSidebar(null, false)
    const link = screen.getByText('Safety').closest('a')
    expect(link.getAttribute('href')).toBe('/app/safety')
  })

  it('sidebar Settings link points to /app/settings', () => {
    renderSidebar(null, false)
    const link = screen.getByText('Settings').closest('a')
    expect(link.getAttribute('href')).toBe('/app/settings')
  })

  it('sidebar Screen Control link points to /app/screen-control', () => {
    renderSidebar(null, true)
    fireEvent.click(screen.getByText('ADVANCED'))
    const link = screen.getByText('Screen Control').closest('a')
    expect(link.getAttribute('href')).toBe('/app/screen-control')
  })

  it('sidebar Local Agent link points to /app/local-agent', () => {
    renderSidebar(null, true)
    fireEvent.click(screen.getByText('ADVANCED'))
    const link = screen.getByText('Local Agent').closest('a')
    expect(link.getAttribute('href')).toBe('/app/local-agent')
  })

  it('sidebar Storage link points to /app/storage', () => {
    renderSidebar(null, true)
    fireEvent.click(screen.getByText('ADVANCED'))
    const link = screen.getByText('Storage').closest('a')
    expect(link.getAttribute('href')).toBe('/app/storage')
  })

  it('sidebar admin links point to correct routes', () => {
    renderSidebar({ email: 'admin@test.com', role: 'owner' }, true)
    expect(screen.getByText('Dashboard').closest('a').getAttribute('href')).toBe('/admin/dashboard')
    expect(screen.getByText('Users').closest('a').getAttribute('href')).toBe('/admin/users')
    expect(screen.getByText('Audit Logs').closest('a').getAttribute('href')).toBe('/admin/audit-logs')
    expect(screen.getByText('Waitlist').closest('a').getAttribute('href')).toBe('/admin/waitlist')
    expect(screen.getByText('System Health').closest('a').getAttribute('href')).toBe('/admin/system-health')
    expect(screen.getByText('AI Status').closest('a').getAttribute('href')).toBe('/admin/ai-status')
  })
})
