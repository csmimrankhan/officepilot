export default function AuthLayout({ children, title, subtitle }) {
  return (
    <div className="auth-layout">
      <div className="auth-brand-panel">
        <div className="auth-brand-content">
          <div className="auth-brand-logo">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="8" fill="#2563eb" />
              <path d="M10 14h20v3H10v-3zm0 6h16v3H10v-3zm0 6h12v3H10v-3z" fill="#fff" />
            </svg>
            <h1 className="auth-brand-name">OfficePilot</h1>
          </div>
          <h2 className="auth-brand-tagline">Local-first automation assistant for accounting teams</h2>
          <ul className="auth-brand-features">
            <li>Automate Excel, browser, and desktop workflows</li>
            <li>Works with QuickBooks, Xero, and any accounting platform</li>
            <li>Zero-cloud by default — your data stays local</li>
            <li>Voice commands in English and Roman Urdu</li>
            <li>Step-by-step planning with approval before execution</li>
          </ul>
          <div className="auth-brand-footer">
            <p className="auth-brand-footer-text">Zero-cloud by default. Optional AI only when enabled by admin.</p>
          </div>
        </div>
      </div>
      <div className="auth-card-panel">
        <div className="auth-card-container">
          <div className="auth-card-header">
            <h1 className="auth-card-title">{title || 'OfficePilot'}</h1>
            {subtitle && <p className="auth-card-subtitle">{subtitle}</p>}
          </div>
          {children}
        </div>
      </div>
    </div>
  )
}
