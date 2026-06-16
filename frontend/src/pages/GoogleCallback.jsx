import { useEffect, useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth.jsx'
import { api } from '../api.js'

export default function GoogleCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { login } = useAuth()
  const [error, setError] = useState('')

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const err = searchParams.get('error')
    if (err) {
      setError(`Google login failed: ${err}`)
      return
    }
    if (!code) {
      setError('Missing authorization code')
      return
    }
    api.googleAuthCallback(code, state || '').then(data => {
      login(data)
      navigate('/app/agent')
    }).catch(err => {
      setError(err.message || 'Google login failed')
    })
  }, [])

  if (error) {
    return (
      <div className="login-page">
        <div className="login-card" style={{ textAlign: 'center' }}>
          <h2>Login Failed</h2>
          <p className="alert error">{error}</p>
          <a href="/login" className="btn btn--primary" style={{ marginTop: 16 }}>Back to Login</a>
        </div>
      </div>
    )
  }

  return (
    <div className="login-page">
      <div className="login-card" style={{ textAlign: 'center' }}>
        <div className="spinner" style={{ margin: '20px auto' }} />
        <p>Completing Google login...</p>
      </div>
    </div>
  )
}
