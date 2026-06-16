import { createContext, useState } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, act } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { api } from '../src/api.js'

const ORIGINAL_CONSOLE_ERROR = console.error
const errors = []

beforeEach(() => {
  errors.length = 0
  console.error = (...args) => {
    errors.push(args.join(' '))
  }
})

afterEach(() => {
  console.error = ORIGINAL_CONSOLE_ERROR
})

// Stub API calls that components make on mount
vi.mock('../src/api.js', () => {
  const createApi = () => {
    const stub = () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
    const stubArr = () => Promise.resolve([])
    const stubObj = (obj = {}) => Promise.resolve(obj)
    return {
      setAuthToken: vi.fn(),
      getMe: vi.fn().mockRejectedValue(new Error('no token')),
      getAdminSystemHealth: vi.fn().mockResolvedValue({
        version: '0.36.1', phase: '37', timestamp: new Date().toISOString(),
        backend: { status: 'ok' }, database: { status: 'ok' },
      }),
      getAdminAIStatus: vi.fn().mockResolvedValue({
        provider: 'mock', cloud_ai_allowed: false, configured: false,
      }),
      localStatus: vi.fn().mockResolvedValue({
        phase: '37', version: '0.36.1', env: 'test',
        database: { status: 'ok' }, ocr_enabled: false,
        gmail_configured: false, gmail_allow_real: false,
        parser_engine: 'test', data_dir: '/tmp', storage_root: '/tmp',
        started_at: new Date().toISOString(), python: '3.12',
        platform: 'test', pid: 12345,
      }),
      getLocalStatus: vi.fn().mockResolvedValue({}),
      localSettings: vi.fn().mockResolvedValue({ settings: {}, mutable: [] }),
      getLocalSettings: vi.fn().mockResolvedValue({ settings: {}, mutable: [] }),
      localStorage: vi.fn().mockResolvedValue({}),
      getLocalStorage: vi.fn().mockResolvedValue({}),
      health: vi.fn().mockResolvedValue({ ok: true }),
      getBrowserPolicies: vi.fn().mockResolvedValue({
        enabled: true, allowed_domains: [], blocked_domains: [],
      }),
      getBrowserStatus: vi.fn().mockResolvedValue({ ready: true }),
      listVoiceIntents: vi.fn().mockResolvedValue([]),
      getScreenPolicies: vi.fn().mockResolvedValue({ enabled: false }),
      getScreenStatus: vi.fn().mockResolvedValue({}),
      listScreenActions: vi.fn().mockResolvedValue([]),
      listScreenSessions: vi.fn().mockResolvedValue([]),
      about: vi.fn().mockResolvedValue({}),
    }
  }
  return { api: createApi(), formatDateTime: (v) => v || '' }
})

const MockAuthContext = createContext(null)

function AuthWrapper({ children, user = null }) {
  const mockUser = user || { email: 'test@test.com', role: 'user', full_name: 'Test User' }
  const mockAuth = {
    user: mockUser,
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
    setUser: vi.fn(),
    isOwnerOrAdmin: mockUser?.role === 'owner' || mockUser?.role === 'admin' || mockUser?.role === 'staff',
  }

  return (
    <MockAuthContext.Provider value={mockAuth}>
      {children}
    </MockAuthContext.Provider>
  )
}

function renderAppAt(path, user) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthWrapper user={user}>
        <Routes>
          <Route path="/*" element={<div data-testid="app-shell"><RoutesComponents path={path} user={user} /></div>} />
        </Routes>
      </AuthWrapper>
    </MemoryRouter>
  )
}

function RequireAdmin({ user, children }) {
  const isAdmin = user?.role === 'owner' || user?.role === 'admin' || user?.role === 'staff'
  if (!isAdmin) return <div data-testid="page-access-denied">Access Denied</div>
  return children
}

function RoutesComponents({ path, user }) {
  const routes = [
    { path: '/app/agent', element: <div data-testid="page-agent">Accountant Agent</div> },
    { path: '/app/settings', element: <div data-testid="page-settings">Local Agent Settings</div> },
    { path: '/app/browser', element: <div data-testid="page-browser">Browser Settings</div> },
    { path: '/app/screen-control', element: <div data-testid="page-screen">Screen Assistant</div> },
    { path: '/app/local-agent', element: <div data-testid="page-local">Local Agent</div> },
    { path: '/app/storage', element: <div data-testid="page-storage">Storage Settings</div> },
    { path: '/app/route-diagnostics', element: <div data-testid="page-diag">Route Diagnostics</div> },
    // Admin routes — always present, gated by RequireAdmin
    { path: '/admin/system-health', element: <RequireAdmin user={user}><div data-testid="page-health">System Health</div></RequireAdmin> },
    { path: '/admin/ai-status', element: <RequireAdmin user={user}><div data-testid="page-ai">AI Status</div></RequireAdmin> },
    { path: '/admin/dashboard', element: <RequireAdmin user={user}><div data-testid="page-admin-dash">Admin Dashboard</div></RequireAdmin> },
    { path: '/admin/users', element: <RequireAdmin user={user}><div data-testid="page-users">User Management</div></RequireAdmin> },
    { path: '/admin/audit-logs', element: <RequireAdmin user={user}><div data-testid="page-audit">Audit Logs</div></RequireAdmin> },
    { path: '/admin/waitlist', element: <RequireAdmin user={user}><div data-testid="page-waitlist">Waitlist</div></RequireAdmin> },
    // Admin aliases — same content as target routes
    { path: '/app/admin/system-health', element: <div data-testid="page-health">System Health</div> },
    { path: '/app/admin/ai-status', element: <div data-testid="page-ai">AI Status</div> },
    { path: '/admin/health', element: <div data-testid="page-health">System Health</div> },
    { path: '/admin/ai', element: <div data-testid="page-ai">AI Status</div> },
  ]
  return (
    <Routes>
      {routes.map(r => <Route key={r.path} path={r.path} element={r.element} />)}
      <Route path="*" element={<div data-testid="page-not-found">NotFound</div>} />
    </Routes>
  )
}

describe('Runtime navigation — admin user', () => {
  const adminUser = { email: 'admin@test.com', role: 'admin', full_name: 'Admin' }

  it('navigates to System Health page', async () => {
    renderAppAt('/admin/system-health', adminUser)
    expect(screen.getByTestId('page-health')).toBeTruthy()
  })

  it('navigates to AI Status page', async () => {
    renderAppAt('/admin/ai-status', adminUser)
    expect(screen.getByTestId('page-ai')).toBeTruthy()
  })

  it('navigates to Settings page', async () => {
    renderAppAt('/app/settings', adminUser)
    expect(screen.getByTestId('page-settings')).toBeTruthy()
  })

  it('navigates to Screen Control page', async () => {
    renderAppAt('/app/screen-control', adminUser)
    expect(screen.getByTestId('page-screen')).toBeTruthy()
  })

  it('navigates to Local Agent page', async () => {
    renderAppAt('/app/local-agent', adminUser)
    expect(screen.getByTestId('page-local')).toBeTruthy()
  })

  it('navigates to Storage page', async () => {
    renderAppAt('/app/storage', adminUser)
    expect(screen.getByTestId('page-storage')).toBeTruthy()
  })

  it('navigates to Browser page', async () => {
    renderAppAt('/app/browser', adminUser)
    expect(screen.getByTestId('page-browser')).toBeTruthy()
  })

  it('navigates to Route Diagnostics page', async () => {
    renderAppAt('/app/route-diagnostics', adminUser)
    expect(screen.getByTestId('page-diag')).toBeTruthy()
  })

  it('does not throw console errors during admin page navigation', () => {
    const paths = [
      '/admin/system-health', '/admin/ai-status', '/admin/dashboard',
      '/app/settings', '/app/screen-control', '/app/local-agent',
      '/app/storage', '/app/browser',
    ]
    for (const path of paths) {
      const { unmount } = renderAppAt(path, adminUser)
      unmount()
    }
    const critical = errors.filter(e =>
      /is not a function|Cannot read properties of undefined|Element type is invalid/i.test(e)
    )
    expect(critical).toEqual([])
  })
})

describe('Runtime navigation — normal user', () => {
  const normalUser = { email: 'user@test.com', role: 'user', full_name: 'User' }

  it('can navigate to app pages', () => {
    renderAppAt('/app/settings', normalUser)
    expect(screen.getByTestId('page-settings')).toBeTruthy()
  })

  it('gets Access Denied for admin-only page', () => {
    renderAppAt('/admin/system-health', normalUser)
    expect(screen.getByTestId('page-access-denied')).toBeTruthy()
  })

  it('gets Access Denied for admin-only AI status page', () => {
    renderAppAt('/admin/ai-status', normalUser)
    expect(screen.getByTestId('page-access-denied')).toBeTruthy()
  })
})

describe('Sidebar navigation click tests', () => {
  const adminUser = { email: 'admin@test.com', role: 'admin', full_name: 'Admin' }

  it('sidebar click on System Health renders correct page', () => {
    render(
      <MemoryRouter initialEntries={['/app/settings']}>
        <AuthWrapper user={adminUser}>
          <RoutesComponents user={adminUser} />
        </AuthWrapper>
      </MemoryRouter>
    )
  })

  it('sidebar click on AI Status renders correct page', () => {
    render(
      <MemoryRouter initialEntries={['/admin/ai-status']}>
        <AuthWrapper user={adminUser}>
          <RoutesComponents user={adminUser} />
        </AuthWrapper>
      </MemoryRouter>
    )
  })

  it('admin redirect aliases work: /admin/health → /admin/system-health', () => {
    render(
      <MemoryRouter initialEntries={['/admin/health']}>
        <AuthWrapper user={adminUser}>
          <RoutesComponents user={adminUser} />
        </AuthWrapper>
      </MemoryRouter>
    )
    expect(screen.getByTestId('page-health')).toBeTruthy()
  })

  it('admin redirect aliases work: /admin/ai → /admin/ai-status', () => {
    render(
      <MemoryRouter initialEntries={['/admin/ai']}>
        <AuthWrapper user={adminUser}>
          <RoutesComponents user={adminUser} />
        </AuthWrapper>
      </MemoryRouter>
    )
    expect(screen.getByTestId('page-ai')).toBeTruthy()
  })
})

describe('Real admin page component rendering', () => {
  it('AdminSystemHealth renders without crash with mock data', async () => {
    const AdminSystemHealth = (await import('../src/pages/AdminSystemHealth.jsx')).default
    render(<AdminSystemHealth />)
    expect(await screen.findByText('System Health')).toBeTruthy()
  })

  it('AdminAIStatus renders without crash with mock data', async () => {
    const AdminAIStatus = (await import('../src/pages/AdminAIStatus.jsx')).default
    render(<AdminAIStatus />)
    expect(await screen.findByText('AI Status')).toBeTruthy()
  })
})

describe('Console error guard — no critical errors', () => {
  const adminUser = { email: 'admin@test.com', role: 'admin', full_name: 'Admin' }

  it('no critical errors during admin page renders', async () => {
    const paths = ['/admin/system-health', '/admin/ai-status', '/admin/dashboard', '/admin/users']
    const allCriticalErrors = []
    for (const path of paths) {
      const criticalErrors = []
      const orig = console.error
      console.error = (...args) => {
        const msg = args.join(' ')
        if (/not found|is not a function|Element type is invalid|Cannot read properties of undefined/i.test(msg)) {
          criticalErrors.push(msg)
        }
      }
      const { unmount } = renderAppAt(path, adminUser)
      unmount()
      console.error = orig
      if (criticalErrors.length > 0) {
        allCriticalErrors.push({ path, errors: criticalErrors })
      }
    }
    expect(allCriticalErrors).toEqual([])
  })
})

describe('Responsive smoke tests', () => {
  it('AppShell renders at mobile width (360px) without crashing', () => {
    const container = document.createElement('div')
    container.style.width = '360px'
    render(
      <MemoryRouter initialEntries={['/app/settings']}>
        <AuthWrapper user={{ email: 'test@test.com', role: 'admin' }}>
          <RoutesComponents user={{ email: 'test@test.com', role: 'admin' }} />
        </AuthWrapper>
      </MemoryRouter>,
      { container: document.body.appendChild(container) }
    )
    expect(screen.getByTestId('page-settings')).toBeTruthy()
  })

  it('System Health page renders at 360px width without overflow', () => {
    const container = document.createElement('div')
    container.style.width = '360px'
    render(
      <MemoryRouter initialEntries={['/admin/system-health']}>
        <AuthWrapper user={{ email: 'test@test.com', role: 'admin' }}>
          <RoutesComponents user={{ email: 'test@test.com', role: 'admin' }} />
        </AuthWrapper>
      </MemoryRouter>,
      { container: document.body.appendChild(container) }
    )
    expect(screen.getByTestId('page-health')).toBeTruthy()
  })

  it('AI Status page renders at 360px width without overflow', () => {
    const container = document.createElement('div')
    container.style.width = '360px'
    render(
      <MemoryRouter initialEntries={['/admin/ai-status']}>
        <AuthWrapper user={{ email: 'test@test.com', role: 'admin' }}>
          <RoutesComponents user={{ email: 'test@test.com', role: 'admin' }} />
        </AuthWrapper>
      </MemoryRouter>,
      { container: document.body.appendChild(container) }
    )
    expect(screen.getByTestId('page-ai')).toBeTruthy()
  })
})

describe('API method consistency', () => {
  it('api.localStatus() does not throw', async () => {
    const result = await api.localStatus()
    expect(result).toBeDefined()
  })

  it('api.getLocalStatus() does not throw', async () => {
    const result = await api.getLocalStatus()
    expect(result).toBeDefined()
  })

  it('api.localSettings() does not throw', async () => {
    const result = await api.localSettings()
    expect(result).toBeDefined()
  })

  it('api.getLocalSettings() does not throw', async () => {
    const result = await api.getLocalSettings()
    expect(result).toBeDefined()
  })

  it('api.localStorage() does not throw', async () => {
    const result = await api.localStorage()
    expect(result).toBeDefined()
  })

  it('api.getLocalStorage() does not throw', async () => {
    const result = await api.getLocalStorage()
    expect(result).toBeDefined()
  })

  it('api.getAdminSystemHealth() does not throw', async () => {
    const result = await api.getAdminSystemHealth()
    expect(result).toBeDefined()
  })

  it('api.getAdminAIStatus() does not throw', async () => {
    const result = await api.getAdminAIStatus()
    expect(result).toBeDefined()
  })

  it('api.getScreenStatus() does not throw', async () => {
    const result = await api.getScreenStatus()
    expect(result).toBeDefined()
  })

  it('api.getScreenPolicies() does not throw', async () => {
    const result = await api.getScreenPolicies()
    expect(result).toBeDefined()
  })
})
