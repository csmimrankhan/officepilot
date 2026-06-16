export default function GuidedDownloadCard({
  watchedFolder,
  waiting,
  detectedFile,
  outputPath,
  onCancel,
  onContinue,
  loading,
}) {
  return (
    <div className="card" style={{ padding: '14px', background: '#181825', borderRadius: '12px', borderLeft: '3px solid #89dceb' }}>
      <style>{`
        .guided-dl-card { font-size: 13px; color: #cdd6f4; }
        .guided-dl-title { font-weight: 600; font-size: 14px; margin: 0 0 6px 0; color: #89dceb; }
        .guided-dl-path { background: #1e1e2e; padding: 6px 10px; border-radius: 6px; margin: 6px 0; word-break: break-all; font-family: monospace; font-size: 12px; }
        .guided-dl-note { color: #a6adc8; font-size: 12px; margin: 8px 0; padding: 8px; background: #1e1e2e; border-radius: 6px; }
        .guided-dl-spinner { display: inline-block; width: 12px; height: 12px; border: 2px solid #89dceb; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 6px; vertical-align: middle; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .guided-dl-btn { background: #89dceb; color: #1e1e2e; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; }
        .guided-dl-btn:hover { background: #74c7ec; }
        .guided-dl-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .guided-dl-cancel { background: #45475a; color: #cdd6f4; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; margin-left: 8px; }
        .guided-dl-success { color: #a6e3a1; font-weight: 500; }
      `}</style>
      <div className="guided-dl-card">
        <p className="guided-dl-title">📥 Guided Download</p>
        {watchedFolder && (
          <div style={{ marginBottom: 6 }}>
            <span style={{ color: '#a6adc8' }}>Watching folder:</span>
            <div className="guided-dl-path">{watchedFolder}</div>
          </div>
        )}
        {waiting && !detectedFile && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="guided-dl-spinner" />
            <span>Waiting for exported file... Please click Export/Download in the browser.</span>
          </div>
        )}
        {detectedFile && (
          <div>
            <p className="guided-dl-success">✓ File detected!</p>
            <div className="guided-dl-path">{detectedFile}</div>
            {outputPath && (
              <div style={{ marginTop: 6 }}>
                <span style={{ color: '#a6adc8' }}>Saved to:</span>
                <div className="guided-dl-path">{outputPath}</div>
              </div>
            )}
          </div>
        )}
        <div className="guided-dl-note">
          {detectedFile
            ? "The downloaded file has been copied to the output folder. Your original file in Downloads remains unchanged."
            : "Navigate to the report in the browser and click Export/Download (CSV, Excel, or PDF)."}
        </div>
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          {detectedFile && onContinue && (
            <button className="guided-dl-btn" onClick={onContinue} disabled={loading}>
              {loading ? '...' : 'Continue'}
            </button>
          )}
          {onCancel && (
            <button className="guided-dl-cancel" onClick={onCancel} disabled={loading}>
              {detectedFile ? 'Skip' : 'Cancel'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
