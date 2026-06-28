import { useState, useEffect } from 'react'

export default function AttachmentDownloadCard({
  attachments = [],
  messageIds = [],
  onDownload,
  onCancel,
  loading,
  error: externalError,
  onErrorClear,
}) {
  const [folder, setFolder] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/system/downloads-path')
      .then(r => r.json())
      .then(d => { if (d.path) setFolder(d.path) })
      .catch(() => {})
  }, [])

  if (!attachments || attachments.length === 0) return null

  const handleBrowse = async () => {
    try {
      if (window.__TAURI__?.dialog?.open) {
        const selected = await window.__TAURI__.dialog.open({ directory: true, multiple: false, title: 'Select output folder' })
        if (selected) {
          setFolder(typeof selected === 'string' ? selected : selected.path || selected)
          setError('')
        }
        return
      }
    } catch (_e) { /* Tauri dialog not available */ }
    try {
      if ('showDirectoryPicker' in window) {
        const handle = await window.showDirectoryPicker()
        setFolder(folder || 'C:\\Users\\dsmim\\Downloads')
        setError('Folder selected. If the backend cannot access it, paste the full path manually.')
        return
      }
    } catch (_e) { /* cancelled or unsupported */ }
    const path = window.prompt('Enter the full folder path for downloads:', folder || 'C:\\Users\\dsmim\\Downloads')
    if (path && path.trim()) {
      setFolder(path.trim())
      setError('')
    }
  }

  const handleDownload = () => {
    setError('')
    if (onErrorClear) onErrorClear()
    if (!folder.trim()) {
      setError('Please enter or select an output folder path')
      return
    }
    if (onDownload) onDownload(messageIds, folder.trim())
  }

  return (
    <div className="card" style={{ padding: '14px', background: '#181825', borderRadius: '12px', borderLeft: '3px solid #f9e2af' }}>
      <style>{`
        .att-download-card { font-size: 13px; color: #cdd6f4; }
        .att-download-title { font-weight: 600; font-size: 14px; margin: 0 0 4px 0; color: #f9e2af; }
        .att-download-subtitle { font-size: 12px; color: #a6adc8; margin: 0 0 10px 0; }
        .att-download-list { margin: 8px 0; }
        .att-download-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 12px; }
        .att-download-warning { background: #1e1e2e; border-left: 3px solid #f38ba8; padding: 8px 10px; border-radius: 6px; margin: 8px 0; font-size: 12px; color: #f38ba8; }
        .att-download-folder-row { display: flex; gap: 6px; align-items: center; margin: 8px 0; }
        .att-download-folder-row input { flex: 1; background: #1e1e2e; border: 1px solid #45475a; padding: 8px 10px; border-radius: 6px; color: #cdd6f4; font-size: 13px; outline: none; min-width: 0; }
        .att-download-folder-row input:focus { border-color: #89b4fa; }
        .att-download-browse-btn { background: #45475a; color: #cdd6f4; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; white-space: nowrap; }
        .att-download-browse-btn:hover { background: #585b70; }
        .att-download-actions { display: flex; gap: 6px; margin-top: 10px; }
        .att-download-btn { background: #45475a; color: #cdd6f4; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; }
        .att-download-btn:hover { background: #585b70; }
        .att-download-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .att-download-btn.primary { background: #f9e2af; color: #1e1e2e; font-weight: 600; }
        .att-download-btn.primary:hover { background: #f5c2e7; }
        .att-download-btn.secondary { background: #45475a; }
        .att-download-error { background: #1e1e2e; border-left: 3px solid #f38ba8; padding: 6px 10px; border-radius: 4px; margin: 6px 0; font-size: 12px; color: #f38ba8; }
      `}</style>
      <div className="att-download-card">
        <p className="att-download-title">Download Attachments</p>
        <p className="att-download-subtitle">Approve downloading {attachments.length} attachment(s) from {messageIds.length} email(s)</p>
        <div className="att-download-list">
          {attachments.map((att, i) => (
            <div key={i} className="att-download-item">
              <span>📎</span>
              <span>{att.filename}</span>
              <span style={{ color: '#6c7086' }}>({Math.round((att.size || 0) / 1024)} KB)</span>
            </div>
          ))}
        </div>
        <div className="att-download-warning">
          Attachments will be saved to your local machine.
          Review and approve to proceed.
        </div>
        <div className="att-download-folder-row">
          <input
            type="text"
            value={folder}
            onChange={(e) => { setFolder(e.target.value); setError('') }}
            placeholder="C:\Users\...\Downloads\Invoices"
          />
          <button className="att-download-browse-btn" onClick={handleBrowse} disabled={loading} type="button">
            Browse
          </button>
        </div>
        {(error || externalError) && (
          <div className="att-download-error">{error || externalError}</div>
        )}
        <div className="att-download-actions">
          <button className="att-download-btn primary" onClick={handleDownload} disabled={loading}>
            {loading ? 'Downloading...' : 'Approve & Download'}
          </button>
          {onCancel && (
            <button className="att-download-btn secondary" onClick={onCancel} disabled={loading}>
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
