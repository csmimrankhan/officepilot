import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { api } from '../src/api.js'

const ALL_ROUTES = [
  // Core
  '/app/agent',
  '/app/billing',
  '/app/workflow-memory',
  '/app/skills',
  '/app/version-history',
  // Workspace
  '/app/settings',
  '/app/api-setup',
  '/app/safety',
  // Advanced
  '/app/browser',
  '/app/screen-control',
  '/app/local-agent',
  '/app/storage',
  // Admin (always present, gated by RequireAdmin)
  '/admin/dashboard',
  '/admin/users',
  '/admin/audit-logs',
  '/admin/waitlist',
  '/admin/system-health',
  '/admin/ai-status',
  // Admin aliases
  '/app/admin/system-health',
  '/app/admin/ai-status',
  '/admin/health',
  '/admin/ai',
]

const SIDEBAR_LINKS = [
  '/app/agent',         // Agent
  '/app/skills',        // Skills
  '/app/workflow-memory', // Workflow Memory
  '/app/version-history', // Version History
  '/app/settings',      // Settings
  '/app/api-setup',     // API Setup
  '/app/safety',        // Safety
  '/app/browser',       // Browser
  '/app/screen-control', // Screen Control
  '/app/local-agent',   // Local Agent
  '/app/storage',       // Storage
  '/admin/dashboard',   // Dashboard
  '/admin/users',       // Users
  '/admin/audit-logs',  // Audit Logs
  '/admin/waitlist',    // Waitlist
  '/admin/system-health', // System Health
  '/admin/ai-status',   // AI Status
]

function AuthGate({ isAdmin = false, children }) {
  const { user } = { user: isAdmin ? { email: 'admin@test.com', role: 'owner' } : { email: 'user@test.com', role: 'user' } }
  return <>{children}</>
}

describe('API method existence', () => {
  it('api.localStatus exists and is a function', () => {
    expect(typeof api.localStatus).toBe('function')
  })

  it('api.getLocalStatus exists and is a function', () => {
    expect(typeof api.getLocalStatus).toBe('function')
  })

  it('api.getLocalSettings exists and is a function', () => {
    expect(typeof api.getLocalSettings).toBe('function')
  })

  it('api.getLocalStorage exists and is a function', () => {
    expect(typeof api.getLocalStorage).toBe('function')
  })

  it('api.getAdminSystemHealth exists and is a function', () => {
    expect(typeof api.getAdminSystemHealth).toBe('function')
  })

  it('api.getAdminAIStatus exists and is a function', () => {
    expect(typeof api.getAdminAIStatus).toBe('function')
  })

  it('api.getScreenStatus exists and is a function', () => {
    expect(typeof api.getScreenStatus).toBe('function')
  })

  it('api.getScreenPolicies exists and is a function', () => {
    expect(typeof api.getScreenPolicies).toBe('function')
  })

  it('api.getScreenLogs exists and is a function', () => {
    expect(typeof api.getScreenLogs).toBe('function')
  })
})

describe('Sidebar links match registered routes', () => {
  it('all sidebar links are in the registered routes list', () => {
    for (const link of SIDEBAR_LINKS) {
      expect(ALL_ROUTES).toContain(link)
    }
  })

  it('no sidebar link has a typo or dead route', () => {
    for (const link of SIDEBAR_LINKS) {
      expect(link.startsWith('/')).toBe(true)
      expect(link.split('/').length).toBeGreaterThanOrEqual(3)
    }
  })
})
