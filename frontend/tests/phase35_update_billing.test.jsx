import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import UpdateBanner from '../src/components/billing/UpdateBanner.jsx'
import BillingStatusCard from '../src/components/billing/BillingStatusCard.jsx'
import BillingPage from '../src/pages/BillingPage.jsx'
import NotificationCenter from '../src/components/billing/NotificationCenter.jsx'

// Mock api
vi.mock('../src/api.js', () => ({
  api: {
    checkUpdate: vi.fn(),
    getLicense: vi.fn(),
    getPlans: vi.fn(),
    getNotifications: vi.fn(),
    markNotificationSeen: vi.fn(),
    startCheckout: vi.fn(),
    manageBilling: vi.fn(),
    getLocalStatus: vi.fn(),
    getSafetyPolicies: vi.fn(),
  },
  setAuthToken: vi.fn(),
}))

// ── UpdateBanner ─────────────────────────────────────────────────────

describe('UpdateBanner', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders update available', async () => {
    const { api } = await import('../src/api.js')
    api.checkUpdate.mockResolvedValue({
      update_available: true,
      latest_version: '0.36.0',
      critical: false,
      download_url: 'https://example.com/update.exe',
      release_notes: 'Bug fixes',
    })

    render(<MemoryRouter><UpdateBanner /></MemoryRouter>)
    vi.advanceTimersByTime(2000)
    await vi.waitFor(() => {
      expect(screen.getByText(/Update available/i)).toBeTruthy()
      expect(screen.getByText(/v0\.36\.0/i)).toBeTruthy()
      expect(screen.getByText(/Download/i)).toBeTruthy()
    })
  })

  it('renders critical update with blocked message', async () => {
    const { api } = await import('../src/api.js')
    api.checkUpdate.mockResolvedValue({
      update_available: true,
      latest_version: '0.37.0',
      critical: true,
      blocked: true,
      message: 'A required security update is available.',
      download_url: 'https://example.com/security-update.exe',
      release_notes: 'Security fix',
    })

    render(<MemoryRouter><UpdateBanner /></MemoryRouter>)
    vi.advanceTimersByTime(2000)
    await vi.waitFor(() => {
      expect(screen.getByText(/Critical update required/i)).toBeTruthy()
      expect(screen.getByText(/Update Now/i)).toBeTruthy()
    })
  })
})

// ── BillingStatusCard ────────────────────────────────────────────────

describe('BillingStatusCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders trial active', async () => {
    const { api } = await import('../src/api.js')
    api.getLicense.mockResolvedValue({
      plan: 'trial',
      status: 'active',
      trial_ends_at: new Date(Date.now() + 86400000 * 14).toISOString(),
      features: {
        excel_automation: true,
        browser_export: true,
        gmail_readonly: true,
        workflow_recorder: true,
        skills_limit: 20,
        monthly_runs_limit: 100,
      },
    })

    render(<MemoryRouter><BillingStatusCard /></MemoryRouter>)
    await vi.waitFor(() => {
      expect(screen.getByText(/Trial Plan/i)).toBeTruthy()
      expect(screen.getByText(/Active/i)).toBeTruthy()
      expect(screen.getByText(/Upgrade to Pro/i)).toBeTruthy()
    })
  })

  it('renders expired status', async () => {
    const { api } = await import('../src/api.js')
    api.getLicense.mockResolvedValue({
      plan: 'trial',
      status: 'expired',
      features: {
        excel_automation: true,
        browser_export: false,
        gmail_readonly: false,
        workflow_recorder: false,
      },
      upgrade_required: true,
    })

    render(<MemoryRouter><BillingStatusCard /></MemoryRouter>)
    await vi.waitFor(() => {
      const expiredElements = screen.getAllByText(/Expired/i)
      expect(expiredElements.length).toBeGreaterThanOrEqual(1)
      expect(screen.getByText(/trial has expired/i)).toBeTruthy()
    })
  })

  it('renders compact plan badge', async () => {
    const { api } = await import('../src/api.js')
    api.getLicense.mockResolvedValue({
      plan: 'trial',
      status: 'active',
      features: { excel_automation: true },
    })

    const { container } = render(<MemoryRouter><BillingStatusCard compact /></MemoryRouter>)
    await vi.waitFor(() => {
      const badge = container.querySelector('.plan-badge')
      expect(badge).toBeTruthy()
    })
  })
})

// ── BillingPage ──────────────────────────────────────────────────────

describe('BillingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders plans', async () => {
    const { api } = await import('../src/api.js')
    api.getLicense.mockResolvedValue({
      plan: 'trial',
      status: 'active',
      trial_ends_at: new Date(Date.now() + 86400000 * 14).toISOString(),
      features: { excel_automation: true },
    })
    api.getPlans.mockResolvedValue({
      plans: [
        { id: 'free', name: 'Free', price: 0, features: { excel_automation: true } },
        { id: 'pro', name: 'Pro', price: 29, features: { excel_automation: true } },
      ],
    })

    render(<MemoryRouter><BillingPage /></MemoryRouter>)
    await vi.waitFor(() => {
      expect(screen.getByText(/Available Plans/i)).toBeTruthy()
      const freeElements = screen.getAllByText(/Free/i)
      expect(freeElements.length).toBeGreaterThanOrEqual(1)
      const proElements = screen.getAllByText(/Pro/i)
      expect(proElements.length).toBeGreaterThanOrEqual(1)
    })
  })
})

// ── NotificationCenter ───────────────────────────────────────────────

describe('NotificationCenter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders notifications', async () => {
    const { api } = await import('../src/api.js')
    api.getNotifications.mockResolvedValue({
      notifications: [
        {
          id: 1,
          title: 'Update Available',
          message: 'v0.36.0 is ready',
          type: 'info',
          seen: false,
          created_at: new Date().toISOString(),
        },
      ],
    })

    render(<MemoryRouter><NotificationCenter /></MemoryRouter>)
    await vi.waitFor(() => {
      expect(screen.getByText(/Notifications/i)).toBeTruthy()
      expect(screen.getByText(/Update Available/i)).toBeTruthy()
      expect(screen.getByText(/Mark as read/i)).toBeTruthy()
    })
  })
})
