export default function FileSelectionCard({ files, message, onFileSelected, onCancel }) {
  if (!files || files.length === 0) return null

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatDate = (iso) => {
    try {
      const d = new Date(iso)
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    } catch {
      return iso
    }
  }

  return (
    <div className="file-selection-card">
      {message && <p className="file-selection-message">{message}</p>}
      <div className="file-selection-list">
        {files.map((f, i) => (
          <div key={i} className="file-selection-item">
            <div className="file-selection-info">
              <span className="file-selection-name">{f.filename}</span>
              <span className="file-selection-meta">
                {f.path} &middot; {formatSize(f.size)} &middot; {formatDate(f.modified_at)}
              </span>
            </div>
            <button
              className="btn btn--sm btn--primary"
              onClick={() => onFileSelected(f.path)}
            >
              Select
            </button>
          </div>
        ))}
      </div>
      {onCancel && (
        <button className="btn btn--sm btn--secondary file-selection-cancel" onClick={onCancel}>
          Cancel
        </button>
      )}
    </div>
  )
}
