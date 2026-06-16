import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import AuthLayout from '../components/auth/AuthLayout.jsx'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!email) {
      setError('Please enter your email address.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await api.forgotPassword(email)
      setSent(true)
    } catch (err) {
      setError(err.message || 'Request failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (sent) {
    return (
      <AuthLayout title="Check your email" subtitle="Password reset link sent">
        <div className="auth-success-state">
          <div className="auth-success-icon">✉️</div>
          <p>If the email is registered, a password reset link has been sent.</p>
          <p className="auth-footer-text" style={{ marginTop: 20 }}>
            <Link to="/login">Back to sign in</Link>
          </p>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Reset password" subtitle="Enter your email to receive a reset link">
      {error && <div className="alert error" role="alert">{error}</div>}
      <form onSubmit={handleSubmit} noValidate>
        <div className="auth-field">
          <label htmlFor="forgot-email">Email address</label>
          <input id="forgot-email" type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus placeholder="you@example.com" autoComplete="email" />
        </div>
        <button className="btn btn--primary auth-submit" type="submit" disabled={loading} aria-label="Send password reset link">
          {loading ? 'Sending…' : 'Send Reset Link'}
        </button>
      </form>
      <p className="auth-footer-text">
        Remember your password? <Link to="/login">Sign in</Link>
      </p>
    </AuthLayout>
  )
}
