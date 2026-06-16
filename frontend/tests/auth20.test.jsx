import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Login from '../src/pages/Login.jsx'
import Register from '../src/pages/Register.jsx'
import ForgotPassword from '../src/pages/ForgotPassword.jsx'
import AdminUsers from '../src/pages/AdminUsers.jsx'
import AdminDashboard from '../src/pages/AdminDashboard.jsx'
import { api } from '../src/api.js'

// ── Mocks ────────────────────────────────────────────────────────────────

vi.mock('../src/api.js', () => ({
  api: {
    login: vi.fn(),
    register: vi.fn(),
    googleAuthStart: vi.fn(),
    logout: vi.fn(),
    adminListUsers: vi.fn(),
    adminGetUser: vi.fn(),
    adminUpdateUser: vi.fn(),
    adminSuspendUser: vi.fn(),
    adminActivateUser: vi.fn(),
    adminForceLogout: vi.fn(),
    adminResetPasswordLink: vi.fn(),
    adminUserAudit: vi.fn(),
    forgotPassword: vi.fn(),
    getAdminSystemHealth: vi.fn(),
    getAdminAIStatus: vi.fn(),
    setAuthToken: vi.fn(),
    getMe: vi.fn(),
  }
}))

vi.mock('../src/auth.jsx', () => ({
  useAuth: () => ({
    user: null,
    login: vi.fn(),
    isOwnerOrAdmin: false,
  }),
  AuthProvider: ({ children }) => children,
}))

// ── Login page tests ─────────────────────────────────────────────────────

describe('Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.googleAuthStart.mockResolvedValue({ url: '', configured: false })
  })

  it('renders the login form', () => {
    render(<MemoryRouter><Login /></MemoryRouter>)
    expect(screen.getByRole('button', { name: /sign in/i })).toBeTruthy()
    expect(screen.getByPlaceholderText('you@example.com')).toBeTruthy()
    expect(screen.getByPlaceholderText(/enter your password/i)).toBeTruthy()
  })

  it('shows validation error on empty submit', async () => {
    render(<MemoryRouter><Login /></MemoryRouter>)
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => {
      expect(api.login).not.toHaveBeenCalled()
    })
  })

  it('shows forgot password link', () => {
    render(<MemoryRouter><Login /></MemoryRouter>)
    expect(screen.getByText(/forgot password/i)).toBeTruthy()
  })

  it('shows create account link', () => {
    render(<MemoryRouter><Login /></MemoryRouter>)
    expect(screen.getByText(/create one/i)).toBeTruthy()
  })

  it('has email input with proper label', () => {
    render(<MemoryRouter><Login /></MemoryRouter>)
    expect(screen.getByLabelText('Email')).toBeTruthy()
  })

  it('has password input with proper label', () => {
    render(<MemoryRouter><Login /></MemoryRouter>)
    expect(screen.getByLabelText('Password')).toBeTruthy()
  })

  it('has remember me checkbox', () => {
    render(<MemoryRouter><Login /></MemoryRouter>)
    expect(screen.getByText('Remember me')).toBeTruthy()
  })

  it('hides Google button when not configured', () => {
    render(<MemoryRouter><Login /></MemoryRouter>)
    expect(screen.queryByText(/continue with google/i)).toBeNull()
  })

  it('shows Google button when configured', async () => {
    api.googleAuthStart.mockResolvedValue({ url: 'https://accounts.google.com/o/oauth2/auth', configured: true })
    render(<MemoryRouter><Login /></MemoryRouter>)
    expect(await screen.findByRole('button', { name: /continue with google/i })).toBeTruthy()
  })

  it('renders on mobile width', () => {
    global.innerWidth = 360
    global.dispatchEvent(new Event('resize'))
    render(<MemoryRouter><Login /></MemoryRouter>)
    expect(screen.getByRole('button', { name: /sign in/i })).toBeTruthy()
  })
})

// ── Register page tests ──────────────────────────────────────────────────

describe('Register Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.googleAuthStart.mockResolvedValue({ url: '', configured: false })
  })

  it('renders the register form', () => {
    render(<MemoryRouter><Register /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: /create account/i })).toBeTruthy()
    expect(screen.getByPlaceholderText(/your full name/i)).toBeTruthy()
    expect(screen.getByPlaceholderText('you@example.com')).toBeTruthy()
  })

  it('shows confirm password field', () => {
    render(<MemoryRouter><Register /></MemoryRouter>)
    expect(screen.getByPlaceholderText(/repeat your password/i)).toBeTruthy()
  })

  it('has link to login page', () => {
    render(<MemoryRouter><Register /></MemoryRouter>)
    expect(screen.getByText(/already have an account/i)).toBeTruthy()
  })

  it('has full name input with proper label', () => {
    render(<MemoryRouter><Register /></MemoryRouter>)
    expect(screen.getByLabelText('Full name')).toBeTruthy()
  })

  it('hides Google button when not configured', () => {
    render(<MemoryRouter><Register /></MemoryRouter>)
    expect(screen.queryByText(/continue with google/i)).toBeNull()
  })

  it('renders on mobile width', () => {
    global.innerWidth = 360
    global.dispatchEvent(new Event('resize'))
    render(<MemoryRouter><Register /></MemoryRouter>)
    expect(screen.getByRole('heading', { name: /create account/i })).toBeTruthy()
  })

  it('shows password requirements hint', () => {
    render(<MemoryRouter><Register /></MemoryRouter>)
    expect(screen.getByText(/min 8 characters/i)).toBeTruthy()
  })
})

// ── Forgot Password page tests ───────────────────────────────────────────

describe('Forgot Password Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the forgot password form', () => {
    render(<MemoryRouter><ForgotPassword /></MemoryRouter>)
    expect(screen.getByText(/reset password/i)).toBeTruthy()
    expect(screen.getByPlaceholderText('you@example.com')).toBeTruthy()
  })

  it('has email input with proper label', () => {
    render(<MemoryRouter><ForgotPassword /></MemoryRouter>)
    expect(screen.getByLabelText('Email address')).toBeTruthy()
  })

  it('has back to sign in link', () => {
    render(<MemoryRouter><ForgotPassword /></MemoryRouter>)
    expect(screen.getByText(/sign in/i)).toBeTruthy()
  })

  it('renders on mobile width', () => {
    global.innerWidth = 360
    global.dispatchEvent(new Event('resize'))
    render(<MemoryRouter><ForgotPassword /></MemoryRouter>)
    expect(screen.getByText(/reset password/i)).toBeTruthy()
  })
})

// ── Admin Dashboard page tests ───────────────────────────────────────────

describe('Admin Dashboard Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.adminListUsers.mockResolvedValue({
      items: [
        { id: 1, full_name: 'Alice Admin', email: 'alice@test.com', role: 'owner', status: 'active', email_verified: true, auth_provider: 'email', last_login_at: '2026-06-10T00:00:00', created_at: '2026-01-01T00:00:00', login_count: 10 },
        { id: 2, full_name: 'Bob User', email: 'bob@test.com', role: 'user', status: 'active', email_verified: false, auth_provider: 'google', last_login_at: '2026-06-01T00:00:00', created_at: '2026-02-01T00:00:00', login_count: 3 },
        { id: 3, full_name: 'Charlie Suspended', email: 'charlie@test.com', role: 'user', status: 'suspended', email_verified: true, auth_provider: 'email', last_login_at: null, created_at: '2026-03-01T00:00:00', login_count: 0 },
      ],
      total: 3,
    })
    api.getAdminSystemHealth.mockResolvedValue({ version: '0.36.1', phase: '37', timestamp: new Date().toISOString(), backend: { status: 'ok' } })
    api.getAdminAIStatus.mockResolvedValue({ agent_provider: 'mock', zero_cloud_by_default: true })
  })

  it('renders admin dashboard metric cards', async () => {
    render(<MemoryRouter><AdminDashboard /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Total Users')).toBeTruthy()
      expect(screen.getByText('Active Users')).toBeTruthy()
      expect(screen.getByText('Suspended Users')).toBeTruthy()
      expect(screen.getByText('Admin Users')).toBeTruthy()
      expect(screen.getAllByText('System Health').length).toBeGreaterThanOrEqual(2)
    })
    expect(screen.getByText(/operational/i)).toBeTruthy()
    expect(screen.getByText(/local only/i)).toBeTruthy()
  })

  it('shows correct user counts', async () => {
    render(<MemoryRouter><AdminDashboard /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Total Users')).toBeTruthy()
      expect(screen.getByText('Active Users')).toBeTruthy()
      expect(screen.getByText('Suspended Users')).toBeTruthy()
      expect(screen.getByText('Admin Users')).toBeTruthy()
    })
  })

  it('has navigation links to admin pages', async () => {
    render(<MemoryRouter><AdminDashboard /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Manage Users')).toBeTruthy()
      expect(screen.getByText('Audit Logs')).toBeTruthy()
    })
  })
})

// ── Admin Users page tests ───────────────────────────────────────────────

describe('Admin Users Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.innerWidth = 1024
    global.dispatchEvent(new Event('resize'))
    api.adminListUsers.mockResolvedValue({
      items: [
        { id: 1, full_name: 'Alice Admin', email: 'alice@test.com', role: 'owner', status: 'active', email_verified: true, auth_provider: 'email', last_login_at: null, created_at: '2026-01-01T00:00:00', login_count: 5 },
        { id: 2, full_name: 'Bob User', email: 'bob@test.com', role: 'user', status: 'active', email_verified: false, auth_provider: 'google', last_login_at: '2026-06-01T00:00:00', created_at: '2026-02-01T00:00:00', login_count: 3 },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    })
  })

  it('renders user table with correct columns (desktop)', async () => {
    render(<MemoryRouter><AdminUsers /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('Alice Admin')).toBeTruthy()
      expect(screen.getByText('Bob User')).toBeTruthy()
      expect(screen.getByText('alice@test.com')).toBeTruthy()
      expect(screen.getByText('bob@test.com')).toBeTruthy()
    })
    expect(screen.getByText('Name')).toBeTruthy()
    const emailMatches = screen.getAllByText('Email')
    expect(emailMatches.length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('Role')).toBeTruthy()
    expect(screen.getByText('Status')).toBeTruthy()
    expect(screen.getByText('Verified')).toBeTruthy()
    expect(screen.getByText('Provider')).toBeTruthy()
    expect(screen.getByText('Last Login')).toBeTruthy()
    expect(screen.getByText('Created')).toBeTruthy()
  })

  it('shows auth provider badge', async () => {
    render(<MemoryRouter><AdminUsers /></MemoryRouter>)
    await waitFor(() => {
      expect(screen.getByText('email')).toBeTruthy()
      expect(screen.getByText('google')).toBeTruthy()
    })
  })

  it('shows View links for each user', async () => {
    render(<MemoryRouter><AdminUsers /></MemoryRouter>)
    await waitFor(() => {
      const links = screen.getAllByText('View')
      expect(links.length).toBe(2)
    })
  })

  it('has search input and filter dropdowns', () => {
    render(<MemoryRouter><AdminUsers /></MemoryRouter>)
    expect(screen.getByPlaceholderText(/search name/i)).toBeTruthy()
    expect(screen.getByText('All Roles')).toBeTruthy()
    expect(screen.getByText('All Statuses')).toBeTruthy()
    expect(screen.getByText('All Providers')).toBeTruthy()
  })

  it('renders mobile cards when on small screen', async () => {
    global.innerWidth = 360
    global.dispatchEvent(new Event('resize'))
    render(<MemoryRouter><AdminUsers /></MemoryRouter>)
    await waitFor(() => {
      const aliceCards = screen.getAllByText('Alice Admin')
      expect(aliceCards.length).toBe(1)
      const bobCards = screen.getAllByText('Bob User')
      expect(bobCards.length).toBe(1)
    })
  })
})
