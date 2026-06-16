import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { api } from '../api.js'
import AuthLayout from '../components/auth/AuthLayout.jsx'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [remember, setRemember] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [googleConfigured, setGoogleConfigured] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    api.googleAuthStart().then(r => setGoogleConfigured(r.configured)).catch(() => {})
  }, [])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!email || !password) {
      setError('Please enter your email and password.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const data = await api.login({ email, password })
      login(data)
      navigate('/app/agent')
    } catch (err) {
      setError(err.message || 'Login failed. Please check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  function handleGoogleLogin() {
    api.googleAuthStart().then(r => {
      if (r.url) window.location.href = r.url
      else setError('Google login is not configured.')
    }).catch(() => setError('Google login is not available.'))
  }

  return (
    <AuthLayout title="Sign in" subtitle="Welcome back to OfficePilot AI">
      {error && <div className="alert error" role="alert">{error}</div>}
      <form onSubmit={handleSubmit} noValidate>
        <div className="auth-field">
          <label htmlFor="login-email">Email</label>
          <input id="login-email" type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus placeholder="you@example.com" autoComplete="email" />
        </div>
        <div className="auth-field">
          <label htmlFor="login-password">Password</label>
          <div className="auth-password-wrapper">
            <input id="login-password" type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} required placeholder="Enter your password" autoComplete="current-password" />
            <button type="button" className="auth-password-toggle" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
              {showPassword ? '🙈' : '👁️'}
            </button>
          </div>
        </div>
        <div className="auth-row">
          <label className="auth-checkbox-label">
            <input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />
            Remember me
          </label>
          <Link to="/forgot-password" className="auth-link">Forgot password?</Link>
        </div>
        <button className="btn btn--primary auth-submit" type="submit" disabled={loading} aria-label="Sign in to your account">
          {loading ? 'Signing in…' : 'Sign In'}
        </button>
      </form>
      {googleConfigured && (
        <>
          <div className="auth-divider"><span>or</span></div>
          <button className="btn btn--secondary auth-google-btn" onClick={handleGoogleLogin} aria-label="Continue with Google">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" style={{ marginRight: 8 }}>
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>
        </>
      )}
      <p className="auth-footer-text">
        Don't have an account? <Link to="/register">Create one</Link>
      </p>
    </AuthLayout>
  )
}
