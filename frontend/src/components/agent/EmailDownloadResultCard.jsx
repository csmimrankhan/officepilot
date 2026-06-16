export default function EmailDownloadResultCard({
  downloads = [],
  outputFolder = '',
  onCreateExcelSummary,
  onSaveAsSkill,
  onOpenFolder,
  onClear,
  loading,
}) {
  if (!downloads || downloads.length === 0) return null

  const hasSpreadsheet = downloads.some(
    d => (d.mime_type || '').includes('spreadsheet') || (d.filename || '').match(/\.(xlsx|xls|csv)$/i)
  )

  return (
    <div className="card" style={{ padding: '14px', background: '#181825', borderRadius: '12px', borderLeft: '3px solid #a6e3a1' }}>
      <style>{`
        .email-result-card { font-size: 13px; color: #cdd6f4; }
        .email-result-title { font-weight: 600; font-size: 14px; margin: 0 0 4px 0; color: #a6e3a1; }
        .email-result-subtitle { font-size: 12px; color: #a6adc8; margin: 0 0 10px 0; }
        .email-result-file { padding: 6px 8px; margin: 4px 0; background: #1e1e2e; border-radius: 6px; display: flex; align-items: center; gap: 8px; }
        .email-result-file-icon { color: #f9e2af; }
        .email-result-file-name { flex: 1; font-size: 12px; word-break: break-all; }
        .email-result-file-size { font-size: 11px; color: #6c7086; }
        .email-result-folder { background: #1e1e2e; padding: 6px 10px; border-radius: 6px; margin: 6px 0; font-family: monospace; font-size: 12px; color: #a6adc8; word-break: break-all; }
        .email-result-hint { margin-top: 8px; padding: 6px 8px; background: #1e1e2e; border-radius: 6px; font-size: 12px; color: #a6adc8; }
        .email-result-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
        .email-result-btn { background: #45475a; color: #cdd6f4; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; }
        .email-result-btn:hover { background: #585b70; }
        .email-result-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .email-result-btn.primary { background: #89b4fa; color: #1e1e2e; font-weight: 600; }
        .email-result-btn.primary:hover { background: #74c7ec; }
        .email-result-btn.excel { background: #a6e3a1; color: #1e1e2e; font-weight: 600; }
        .email-result-btn.excel:hover { background: #94e2d5; }
      `}</style>
      <div className="email-result-card">
        <p className="email-result-title">✓ Files Downloaded</p>
        <p className="email-result-subtitle">{downloads.length} attachment(s) saved</p>

        {downloads.map((d, i) => (
          <div key={i} className="email-result-file">
            <span className="email-result-file-icon">📎</span>
            <span className="email-result-file-name">{d.filename}</span>
            <span className="email-result-file-size">({Math.round((d.size_bytes || 0) / 1024)} KB)</span>
          </div>
        ))}

        {outputFolder && (
          <div>
            <span style={{ fontSize: 12, color: '#a6adc8' }}>Saved to:</span>
            <div className="email-result-folder">{outputFolder}</div>
          </div>
        )}

        <div className="email-result-actions">
          {onOpenFolder && (
            <button className="email-result-btn primary" onClick={onOpenFolder} disabled={loading}>
              Open Folder
            </button>
          )}
          {hasSpreadsheet && onCreateExcelSummary && (
            <button className="email-result-btn excel" onClick={onCreateExcelSummary} disabled={loading}>
              {loading ? '...' : 'Create Excel Summary'}
            </button>
          )}
          {onSaveAsSkill && (
            <button className="email-result-btn" onClick={onSaveAsSkill} disabled={loading}>
              Save as Skill
            </button>
          )}
          {onClear && (
            <button className="email-result-btn" onClick={onClear}>
              Clear
            </button>
          )}
        </div>

        {hasSpreadsheet && (
          <div className="email-result-hint">
            💡 Spreadsheet attachments detected.
            Click "Create Excel Summary" to auto-detect columns and build a summary.
          </div>
        )}
      </div>
    </div>
  )
}
