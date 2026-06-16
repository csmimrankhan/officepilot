import { useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { api } from '../api.js'
import AuthLayout from '../components/auth/AuthLayout.jsx'

export default function ResetPassword() {
  const [searchParams] = useSearchParams()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    const token = searchParams.get('token')
    if (!token) {
      setError('Missing reset token. Please use the link from your email.')
      return
    }
    if (!password || !confirm) {
      setError('Please fill in all fields.')
      return
    }
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await api.resetPassword(token, password)
      setDone(true)
    } catch (err) {
      setError(err.message || 'Reset failed. The link may have expired.')
    } finally {
      setLoading(false)
    }
  }

  if (done) {
    return (
      <AuthLayout title="Password reset" subtitle="Your password has been updated">
        <div className="auth-success-state">
          <div className="auth-success-icon">✅</div>
          <p>Your password has been updated. You can now sign in with your new password.</p>
          <p className="auth-footer-text" style={{ marginTop: 20 }}>
            <Link to="/login">Sign in</Link>
          </p>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Reset password" subtitle="Enter your new password">
      {error && <div className="alert error" role="alert">{error}</div>}
      <form onSubmit={handleSubmit} noValidate>
        <div className="auth-field">
          <label htmlFor="reset-password">New password</label>
          <div className="auth-password-wrapper">
            <input id="reset-password" type={showPassword ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} required minLength={8} autoFocus placeholder="New password" autoComplete="new-password" />
            <button type="button" className="auth-password-toggle" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Hide password' : 'Show password'}>
              {showPassword ? '🙈' : '👁️'}
            </button>
          </div>
          <p className="auth-hint">Min 8 characters, upper + lower + number + special</p>
        </div>
        <div className="auth-field">
          <label htmlFor="reset-confirm">Confirm password</label>
          <input id="reset-confirm" type="password" value={confirm} onChange={e => setConfirm(e.target.value)} required placeholder="Repeat password" autoComplete="new-password" />
        </div>
        <button className="btn btn--primary auth-submit" type="submit" disabled={loading} aria-label="Reset your password">
          {loading ? 'Resetting…' : 'Reset Password'}
        </button>
      </form>
      <p className="auth-footer-text">
        <Link to="/login">Back to sign in</Link>
      </p>
    </AuthLayout>
  )
}
