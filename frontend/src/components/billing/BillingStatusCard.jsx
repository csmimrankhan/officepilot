import { useState, useEffect } from 'react'
import { api } from '../../api.js'

export default function BillingStatusCard({ compact }) {
  const [license, setLicense] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadLicense()
  }, [])

  const loadLicense = async () => {
    setLoading(true)
    try {
      const data = await api.getLicense()
      setLicense(data)
      setError(null)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  if (loading) {
    return <div className="billing-card"><div className="billing-card-loading">Loading license...</div></div>
  }

  if (error) {
    return <div className="billing-card"><div className="billing-card-error">Failed to load license: {error}</div></div>
  }

  if (!license) return null

  const isExpired = license.status === 'expired'
  const planLabel = license.plan?.charAt(0).toUpperCase() + license.plan?.slice(1) || 'Trial'

  if (compact) {
    return (
      <span className={`plan-badge plan-badge--${license.plan} ${isExpired ? 'plan-badge--expired' : ''}`}>
        {isExpired ? 'Expired' : planLabel}
      </span>
    )
  }

  return (
    <div className={`billing-card ${isExpired ? 'billing-card--expired' : ''}`}>
      <div className="billing-card-header">
        <h3>{planLabel} Plan</h3>
        <span className={`billing-status ${isExpired ? 'billing-status--expired' : 'billing-status--active'}`}>
          {isExpired ? 'Expired' : 'Active'}
        </span>
      </div>
      {license.trial_ends_at && !isExpired && (
        <div className="billing-card-trial">
          Trial ends: {new Date(license.trial_ends_at).toLocaleDateString()}
        </div>
      )}
      {isExpired && (
        <div className="billing-card-expired-msg">
          Your trial has expired. Upgrade to continue using OfficePilot.
        </div>
      )}
      <div className="billing-card-features">
        <h4>Features</h4>
        {license.features && Object.entries(license.features).map(([key, value]) => (
          <div key={key} className="billing-card-feature">
            <span className="billing-card-feature-key">{key.replace(/_/g, ' ')}</span>
            <span className={`billing-card-feature-value ${value ? 'enabled' : 'disabled'}`}>
              {typeof value === 'number' ? value : (value ? '✓' : '✗')}
            </span>
          </div>
        ))}
      </div>
      <div className="billing-card-actions">
        <button
          className="btn btn--primary btn--sm"
          onClick={async () => {
            try {
              await api.startCheckout({ plan: 'pro' })
              alert('Billing checkout is not yet configured. Contact officepilot.ai for subscription management.')
            } catch {}
          }}
        >
          Upgrade to Pro
        </button>
        <button
          className="btn btn--ghost btn--sm"
          onClick={async () => {
            try {
              const res = await api.manageBilling()
              alert(res.message || 'Billing management is not yet configured.')
            } catch {}
          }}
        >
          Manage Billing
        </button>
      </div>
    </div>
  )
}
