export default function ManualLoginCard({ website, status, onLoggedIn, onCancel, loading }) {
  return (
    <div className="card" style={{ padding: '14px', background: '#181825', borderRadius: '12px', borderLeft: '3px solid #f9e2af' }}>
      <style>{`
        .manual-login-card { font-size: 13px; color: #cdd6f4; }
        .manual-login-title { font-weight: 600; font-size: 14px; margin: 0 0 6px 0; color: #f9e2af; }
        .manual-login-website { background: #1e1e2e; padding: 6px 10px; border-radius: 6px; margin: 6px 0; word-break: break-all; font-family: monospace; font-size: 12px; }
        .manual-login-note { color: #a6adc8; font-size: 12px; margin: 8px 0; padding: 8px; background: #1e1e2e; border-radius: 6px; border-left: 3px solid #89b4fa; }
        .manual-login-btn { background: #a6e3a1; color: #1e1e2e; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; }
        .manual-login-btn:hover { background: #94e2d5; }
        .manual-login-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .manual-login-cancel { background: #45475a; color: #cdd6f4; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; margin-left: 8px; }
        .manual-login-cancel:hover { background: #585b70; }
      `}</style>
      <div className="manual-login-card">
        <p className="manual-login-title">🔐 Manual Login Required</p>
        {website && <div className="manual-login-website">{website}</div>}
        {status && <div style={{ marginBottom: 6 }}>Status: <strong>{status.replace('_', ' ')}</strong></div>}
        <div className="manual-login-note">
          OfficePilot does not store or type your password. Please log in manually in the browser then click "I am logged in" below.
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <button className="manual-login-btn" onClick={onLoggedIn} disabled={loading}>
            {loading ? '...' : "✓ I am logged in"}
          </button>
          {onCancel && <button className="manual-login-cancel" onClick={onCancel} disabled={loading}>Cancel</button>}
        </div>
      </div>
    </div>
  )
}
