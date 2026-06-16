import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'

const ACCEPT = '.pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg'

export default function UploadInvoice() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const onSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!file) { setError('Please choose a file.'); return }
    setBusy(true)
    try {
      const inv = await api.uploadInvoice(file, 'user')
      setResult(inv)
      setFile(null)
      e.target.reset()
    } catch (err) {
      setError(err.message || 'Upload failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Upload Invoice</h2>
        <span className="subtle">PDF, PNG, JPG, JPEG — single file per upload</span>
      </div>

      {error && <div className="alert error">{error}</div>}

      <form className="card" onSubmit={onSubmit}>
        <label htmlFor="file">Choose file</label>
        <input
          id="file"
          type="file"
          accept={ACCEPT}
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          disabled={busy}
        />
        <div className="toolbar" style={{ marginTop: 12 }}>
          <button type="submit" disabled={busy}>
            {busy ? 'Uploading…' : 'Upload & Extract'}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => navigate('/review')}
            disabled={busy}
          >
            Go to Review Queue
          </button>
        </div>
      </form>

      {result && (
        <div className="card">
          <div className="alert success">
            Uploaded as invoice <strong>#{result.id}</strong> — status: <strong>{result.status}</strong>.
          </div>
          <button onClick={() => navigate(`/invoices/${result.id}`)}>Open detail</button>
        </div>
      )}
    </div>
  )
}
