import { useState, useEffect } from 'react'
import { api } from '../api.js'
import BillingStatusCard from '../components/billing/BillingStatusCard.jsx'

export default function BillingPage() {
  const [plans, setPlans] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadPlans()
  }, [])

  const loadPlans = async () => {
    setLoading(true)
    try {
      const data = await api.getPlans()
      setPlans(data.plans || [])
      setError(null)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  return (
    <div className="billing-page">
      <div className="billing-page-header">
        <h1>Billing & Plan</h1>
        <p className="text-muted">Manage your subscription and feature access.</p>
      </div>
      <div className="billing-page-layout">
        <div className="billing-page-current">
          <h2>Current Plan</h2>
          <BillingStatusCard />
        </div>
        <div className="billing-page-plans">
          <h2>Available Plans</h2>
          {loading && <div className="text-muted">Loading plans...</div>}
          {error && <div className="error-message">Failed to load plans: {error}</div>}
          {!loading && !error && (
            <div className="plans-grid">
              {plans.map(plan => (
                <div key={plan.id} className="plan-card">
                  <h3 className="plan-card-name">{plan.name}</h3>
                  <div className="plan-card-price">
                    {plan.price === 0 ? 'Free' : `$${plan.price}/mo`}
                  </div>
                  <div className="plan-card-features">
                    {plan.features && Object.entries(plan.features).map(([key, value]) => (
                      <div key={key} className="plan-card-feature">
                        <span className={`plan-card-feature-icon ${value ? 'enabled' : 'disabled'}`}>
                          {typeof value === 'number' ? '#' : (value ? '✓' : '✗')}
                        </span>
                        <span>{key.replace(/_/g, ' ')}</span>
                        {typeof value === 'number' && (
                          <span className="plan-card-feature-limit">({value})</span>
                        )}
                      </div>
                    ))}
                  </div>
                  {plan.price > 0 && (
                    <button
                      className="btn btn--primary btn--sm"
                      onClick={async () => {
                        try {
                          await api.startCheckout({ plan: plan.id })
                          alert('Billing checkout is not yet configured. Contact officepilot.ai for subscription management.')
                        } catch {}
                      }}
                    >
                      Choose {plan.name}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
