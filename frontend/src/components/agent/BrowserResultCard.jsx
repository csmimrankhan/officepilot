export default function BrowserResultCard({
  filePath,
  filename,
  onOpenFile,
  onCreateExcelSummary,
  onSaveAsSkill,
  loading,
}) {
  if (!filePath && !filename) return null

  const isExcelFile = filePath && (
    filePath.endsWith('.xlsx') || filePath.endsWith('.xls') || filePath.endsWith('.csv')
  )

  return (
    <div className="card" style={{ padding: '14px', background: '#181825', borderRadius: '12px', borderLeft: '3px solid #a6e3a1' }}>
      <style>{`
        .browser-result-card { font-size: 13px; color: #cdd6f4; }
        .browser-result-title { font-weight: 600; font-size: 14px; margin: 0 0 6px 0; color: #a6e3a1; }
        .browser-result-filename { font-weight: 500; margin: 4px 0; }
        .browser-result-path { background: #1e1e2e; padding: 6px 10px; border-radius: 6px; margin: 6px 0; word-break: break-all; font-family: monospace; font-size: 12px; color: #a6adc8; }
        .browser-result-btn { background: #45475a; color: #cdd6f4; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; }
        .browser-result-btn:hover { background: #585b70; }
        .browser-result-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .browser-result-btn.primary { background: #89b4fa; color: #1e1e2e; font-weight: 600; }
        .browser-result-btn.primary:hover { background: #74c7ec; }
        .browser-result-btn.excel { background: #a6e3a1; color: #1e1e2e; font-weight: 600; }
        .browser-result-btn.excel:hover { background: #94e2d5; }
        .browser-result-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
      `}</style>
      <div className="browser-result-card">
        <p className="browser-result-title">✓ Report Downloaded</p>
        {filename && <div className="browser-result-filename">{filename}</div>}
        {filePath && (
          <div>
            <span style={{ color: '#a6adc8', fontSize: 12 }}>Saved to:</span>
            <div className="browser-result-path">{filePath}</div>
          </div>
        )}
        <div className="browser-result-actions">
          {onOpenFile && (
            <button className="browser-result-btn primary" onClick={onOpenFile} disabled={loading}>
              Open File
            </button>
          )}
          {isExcelFile && onCreateExcelSummary && (
            <button className="browser-result-btn excel" onClick={onCreateExcelSummary} disabled={loading}>
              {loading ? '...' : 'Create Excel Summary'}
            </button>
          )}
          {onSaveAsSkill && (
            <button className="browser-result-btn" onClick={onSaveAsSkill} disabled={loading}>
              Save as Skill
            </button>
          )}
        </div>
        {isExcelFile && (
          <div style={{ marginTop: 8, padding: '6px 8px', background: '#1e1e2e', borderRadius: 6, fontSize: 12, color: '#a6adc8' }}>
            💡 You can run "Create Excel Summary" on this file to auto-detect columns and generate a summary.
          </div>
        )}
      </div>
    </div>
  )
}
