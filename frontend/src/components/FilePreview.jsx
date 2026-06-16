import { useState } from 'react'
import { api } from '../api.js'

export default function FilePreview({ invoice, refreshKey = 0 }) {
  const [mode, setMode] = useState('pdf')
  const [error, setError] = useState('')

  if (!invoice || !invoice.file) {
    return <div className="muted">No file attached to this invoice.</div>
  }

  const f = invoice.file
  const mime = (f.mime_type || '').toLowerCase()
  const isImage = mime.startsWith('image/')
  const isPdf = mime === 'application/pdf' || mime.includes('pdf')

  if (!isImage && !isPdf) {
    return (
      <div>
        <div><strong>{f.original_filename}</strong> · {f.mime_type || 'unknown type'}</div>
        <div className="subtle" style={{ marginTop: 6 }}>
          Preview not available for this file type.{' '}
          <a href={api.fileDownloadUrl(invoice.id)} target="_blank" rel="noreferrer">Download instead</a>
        </div>
      </div>
    )
  }

  const url = api.fileUrl(invoice.id) + `&_=${refreshKey}`

  return (
    <div>
      <div className="toolbar" style={{ marginBottom: 8 }}>
        {isPdf && (
          <button
            type="button"
            className={mode === 'pdf' ? '' : 'secondary'}
            onClick={() => setMode('pdf')}
          >PDF</button>
        )}
        {isImage && (
          <button
            type="button"
            className={mode === 'image' ? '' : 'secondary'}
            onClick={() => setMode('image')}
          >Image</button>
        )}
        <a className="subtle" href={api.fileDownloadUrl(invoice.id)} target="_blank" rel="noreferrer">Open in new tab</a>
      </div>
      {error && <div className="alert error">{error}</div>}
      {mode === 'pdf' && isPdf ? (
        <iframe
          key={refreshKey}
          src={url}
          title={`Invoice ${invoice.id} preview`}
          className="file-preview"
          onError={() => setError('PDF preview failed.')}
        />
      ) : mode === 'image' && isImage ? (
        <img
          key={refreshKey}
          src={url}
          alt={f.original_filename}
          className="file-preview"
          onError={() => setError('Image preview failed.')}
        />
      ) : (
        <div className="muted">No preview available.</div>
      )}
    </div>
  )
}
