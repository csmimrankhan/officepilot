import { createContext, useContext, useState, useEffect } from 'react'
import { api } from './api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      api.setAuthToken(token)
      api.getMe().then(r => {
        setUser({ ...r.user, onboarding_completed: r.user.onboarding_completed !== false, permissions: [] })
      }).catch(() => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        api.setAuthToken(null)
      }).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  function login(data) {
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    api.setAuthToken(data.access_token)
    setUser({
      id: data.user.id,
      email: data.user.email,
      full_name: data.user.full_name,
      role: data.user.role,
      email_verified: data.user.email_verified,
      status: data.user.status,
      auth_provider: data.user.auth_provider || 'email',
      onboarding_completed: data.user.onboarding_completed !== false,
      permissions: [],
    })
  }

  function logout() {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      api.logout(refreshToken).catch(() => {})
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    api.setAuthToken(null)
    setUser(null)
  }

  const isOwnerOrAdmin = user?.role === 'owner' || user?.role === 'admin' || user?.role === 'staff'

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, setUser, isOwnerOrAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
