import { useState } from 'react'

export default function BrowserAutomationCard({ url, status, screenshotUrl, nextAction, riskLevel, onScreenshot }) {
  const [showScreenshot, setShowScreenshot] = useState(false)

  if (!url && !status) return null

  return (
    <div className="card" style={{ padding: '12px', background: '#181825', borderRadius: '12px', borderLeft: '3px solid #89b4fa' }}>
      <style>{`
        .browser-auto-card { font-size: 13px; color: #cdd6f4; }
        .browser-auto-url { background: #1e1e2e; padding: 6px 10px; border-radius: 6px; margin: 4px 0; word-break: break-all; font-family: monospace; font-size: 12px; }
        .browser-auto-status { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
        .browser-auto-status.active { background: #45475a; color: #a6adc8; }
        .browser-auto-status.waiting_login { background: #f9e2af; color: #1e1e2e; }
        .browser-auto-status.logged_in { background: #a6e3a1; color: #1e1e2e; }
        .browser-auto-risk { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 10px; margin-left: 6px; }
        .browser-auto-risk.low { background: #a6e3a1; color: #1e1e2e; }
        .browser-auto-risk.medium { background: #f9e2af; color: #1e1e2e; }
        .browser-auto-risk.high { background: #f38ba8; color: #1e1e2e; }
        .browser-auto-btn { background: #45475a; color: #cdd6f4; border: none; padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 12px; margin-top: 6px; }
        .browser-auto-btn:hover { background: #585b70; }
      `}</style>
      <div className="browser-auto-card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <span>🌐 Browser</span>
          {status && <span className={`browser-auto-status ${status}`}>{status.replace('_', ' ')}</span>}
          {riskLevel && <span className={`browser-auto-risk ${riskLevel}`}>{riskLevel}</span>}
        </div>
        {url && <div className="browser-auto-url">{url}</div>}
        {nextAction && <div style={{ marginTop: 6, color: '#a6adc8' }}>Next: {nextAction}</div>}
        {screenshotUrl && (
          <div style={{ marginTop: 6 }}>
            <button className="browser-auto-btn" onClick={() => setShowScreenshot(!showScreenshot)}>
              {showScreenshot ? 'Hide' : 'Show'} Screenshot
            </button>
            {showScreenshot && (
              <div style={{ marginTop: 6 }}>
                <img src={screenshotUrl} alt="Browser screenshot" style={{ maxWidth: '100%', borderRadius: 6, border: '1px solid #45475a' }} />
              </div>
            )}
          </div>
        )}
        {!screenshotUrl && onScreenshot && (
          <button className="browser-auto-btn" onClick={onScreenshot}>Take Screenshot</button>
        )}
      </div>
    </div>
  )
}
