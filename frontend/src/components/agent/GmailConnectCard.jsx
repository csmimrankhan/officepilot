export default function GmailConnectCard({
  status,
  email,
  accountId,
  onConnect,
  onDisconnect,
  loading,
}) {
  const isConnected = status === 'connected' || status === 'mock'

  return (
    <div className="card" style={{ padding: '14px', background: '#181825', borderRadius: '12px', borderLeft: '3px solid #89b4fa' }}>
      <style>{`
        .gmail-card { font-size: 13px; color: #cdd6f4; }
        .gmail-card-title { font-weight: 600; font-size: 14px; margin: 0 0 4px 0; color: #89b4fa; }
        .gmail-card-subtitle { font-size: 12px; color: #a6adc8; margin: 0 0 10px 0; }
        .gmail-card-status { display: flex; align-items: center; gap: 6px; margin: 8px 0; }
        .gmail-card-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
        .gmail-card-dot.connected { background: #a6e3a1; }
        .gmail-card-dot.disconnected { background: #f38ba8; }
        .gmail-card-dot.mock { background: #f9e2af; }
        .gmail-card-btn { background: #45475a; color: #cdd6f4; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; }
        .gmail-card-btn:hover { background: #585b70; }
        .gmail-card-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .gmail-card-btn.primary { background: #89b4fa; color: #1e1e2e; font-weight: 600; }
        .gmail-card-btn.primary:hover { background: #74c7ec; }
        .gmail-card-btn.danger { background: #f38ba8; color: #1e1e2e; font-weight: 600; }
        .gmail-card-btn.danger:hover { background: #eba0ac; }
        .gmail-card-note { margin-top: 8px; padding: 6px 8px; background: #1e1e2e; border-radius: 6px; font-size: 12px; color: #a6adc8; }
        .gmail-card-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
      `}</style>
      <div className="gmail-card">
        <p className="gmail-card-title">Gmail Read-Only Access</p>
        <p className="gmail-card-subtitle">Search emails and download attachments. Never sends, deletes, or modifies emails.</p>
        <div className="gmail-card-status">
          <span className={`gmail-card-dot ${isConnected ? (status === 'mock' ? 'mock' : 'connected') : 'disconnected'}`} />
          <span>{isConnected ? (status === 'mock' ? `Mock: ${email || 'mock-user@gmail.com'}` : `Connected: ${email || 'user@gmail.com'}`) : 'Not connected'}</span>
        </div>
        {!isConnected && (
          <div className="gmail-card-actions">
            <button className="gmail-card-btn primary" onClick={onConnect} disabled={loading}>
              {loading ? 'Connecting...' : 'Connect Gmail'}
            </button>
          </div>
        )}
        {isConnected && (
          <div className="gmail-card-actions">
            {onDisconnect && (
              <button className="gmail-card-btn danger" onClick={onDisconnect} disabled={loading}>
                {loading ? '...' : 'Disconnect'}
              </button>
            )}
          </div>
        )}
        <div className="gmail-card-note">
          🔒 Read-only only. Uses <code>gmail.readonly</code> scope.
          Separate from login access — no passwords requested.
        </div>
      </div>
    </div>
  )
}
