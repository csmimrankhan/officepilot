import { Component } from 'react'
import { Link } from 'react-router-dom'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div className="error-state" style={{ padding: 40, textAlign: 'center' }}>
          <h3>Something went wrong</h3>
          <p className="muted">An unexpected error occurred. Please try refreshing the page.</p>
          {this.state.error && (
            <pre style={{ fontSize: 12, color: '#dc2626', background: '#fef2f2', padding: 12, borderRadius: 8, margin: '12px 0', maxWidth: 500, marginInline: 'auto', overflow: 'auto' }}>
              {this.state.error.message}
            </pre>
          )}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 16 }}>
            <button className="primary" onClick={() => window.location.reload()}>Refresh Page</button>
            <Link to="/app/agent" className="btn btn--primary">Go to Agent</Link>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
