import { useState, useRef } from 'react'

const ACCEPTED_TYPES = ['.xlsx', '.xlsm', '.csv']

export default function FilePickerCard({ message, onFileSelected, onCancel, acceptedTypes }) {
  const [selectedPath, setSelectedPath] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)
  const types = acceptedTypes || ACCEPTED_TYPES

  const validateFile = (filename) => {
    const ext = '.' + filename.split('.').pop().toLowerCase()
    if (!types.includes(ext)) {
      setError(`Unsupported file type "${ext}". Accepted: ${types.join(', ')}`)
      return false
    }
    setError(null)
    return true
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!validateFile(file.name)) return
    setSelectedPath(file.name)
  }

  const handlePathInput = (e) => {
    const val = e.target.value
    setSelectedPath(val)
    if (val && !validateFile(val)) return
    setError(null)
  }

  const handleBrowseClick = () => {
    fileInputRef.current?.click()
  }

  const handleContinue = () => {
    if (!selectedPath.trim()) {
      setError('Please select or enter a file path.')
      return
    }
    if (!validateFile(selectedPath.trim())) return
    onFileSelected(selectedPath.trim())
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => {
    setDragOver(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer?.files?.[0]
    if (file) {
      if (!validateFile(file.name)) return
      setSelectedPath(file.name)
    }
  }

  return (
    <div className={`file-picker-card ${dragOver ? 'file-picker-card--drag' : ''}`}
      onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}>
      <div className="file-picker-icon">📂</div>
      <p className="file-picker-message">{message || 'Choose the Excel file to summarize'}</p>

      <input
        ref={fileInputRef}
        type="file"
        accept={types.join(',')}
        onChange={handleFileChange}
        style={{ display: 'none' }}
      />

      <div className="file-picker-input-row">
        <input
          type="text"
          className="file-picker-path-input"
          value={selectedPath}
          onChange={handlePathInput}
          placeholder="Select a file or enter path..."
          readOnly={false}
        />
        <button className="btn btn--secondary btn--sm" onClick={handleBrowseClick}>
          Browse
        </button>
      </div>

      <div className="file-picker-types">
        Accepted: {types.join(', ')}
      </div>

      {error && (
        <div className="file-picker-error">{error}</div>
      )}

      <div className="file-picker-actions">
        <button className="btn btn--primary btn--sm" onClick={handleContinue} disabled={!selectedPath.trim()}>
          Continue
        </button>
        {onCancel && (
          <button className="btn btn--danger btn--sm" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>

      <style>{`
        .file-picker-card {
          padding: 16px;
          border: 2px dashed var(--border, #cbd5e1);
          border-radius: 12px;
          background: var(--bg-card, #f8fafc);
          text-align: center;
          transition: border-color 0.2s, background 0.2s;
        }
        .file-picker-card--drag {
          border-color: var(--primary, #2563eb);
          background: #eff6ff;
        }
        .file-picker-icon { font-size: 2rem; margin-bottom: 8px; }
        .file-picker-message { font-size: 0.9rem; color: var(--text, #1e293b); margin-bottom: 12px; font-weight: 500; }
        .file-picker-input-row { display: flex; gap: 8px; margin-bottom: 8px; }
        .file-picker-path-input {
          flex: 1;
          padding: 8px 12px;
          border: 1px solid var(--border, #cbd5e1);
          border-radius: 8px;
          font-size: 0.85rem;
          color: var(--text, #1e293b);
          background: var(--bg, #fff);
        }
        .file-picker-types { font-size: 0.75rem; color: var(--text-muted, #64748b); margin-bottom: 8px; }
        .file-picker-error { font-size: 0.82rem; color: #dc2626; margin-bottom: 8px; }
        .file-picker-actions { display: flex; gap: 8px; justify-content: center; margin-top: 8px; }
      `}</style>
    </div>
  )
}
