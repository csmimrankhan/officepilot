import { useState, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { api } from '../api.js'

export default function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState('verifying')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const token = searchParams.get('token')
    if (!token) {
      setStatus('error')
      setMessage('No verification token provided.')
      return
    }
    api.verifyEmail(token)
      .then(() => {
        setStatus('success')
        setMessage('Email verified successfully! You can now close this page.')
      })
      .catch(err => {
        setStatus('error')
        setMessage(err.message || 'Verification failed. The token may be expired.')
      })
  }, [searchParams])

  return (
    <div className="login-page">
      <div className="login-card" style={{ textAlign: 'center' }}>
        <div className="login-header">
          <h1 style={{ color: '#a6e3a1' }}>OfficePilot</h1>
          <p>Email Verification</p>
        </div>
        {status === 'verifying' && <p>Verifying your email...</p>}
        {status === 'success' && (
          <>
            <div className="alert success">{message}</div>
            <p style={{ marginTop: 16 }}><Link to="/login">Sign in to your account</Link></p>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="alert error">{message}</div>
            <p style={{ marginTop: 16 }}><Link to="/login">Back to sign in</Link></p>
          </>
        )}
      </div>
    </div>
  )
}
