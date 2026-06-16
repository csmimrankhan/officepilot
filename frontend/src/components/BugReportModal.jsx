import { useState } from 'react'
import { api } from '../api.js'

export default function BugReportModal({ onClose }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [severity, setSeverity] = useState('medium')
  const [includeLogs, setIncludeLogs] = useState(false)
  const [includeScreenshot, setIncludeScreenshot] = useState(false)
  const [includeReadiness, setIncludeReadiness] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [downloadUrl, setDownloadUrl] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!title.trim() || !description.trim()) return
    setSubmitting(true)
    try {
      const res = await api.createBugReport({
        title: title.trim(),
        description: description.trim(),
        severity,
        include_logs: includeLogs,
        include_screenshot: includeScreenshot,
        include_readiness: includeReadiness,
      })
      setResult('success')
      setDownloadUrl(api.downloadBugReportUrl(res.id))
    } catch (err) {
      setResult('error: ' + err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="card" style={{ width: '550px', maxHeight: '90vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0 }}>Report a Bug</h2>
          <button className="btn btn--small btn--secondary" onClick={onClose}>Close</button>
        </div>
        {result === 'success' ? (
          <div style={{ textAlign: 'center', padding: '24px' }}>
            <p style={{ color: '#4caf50', fontSize: '1.2rem' }}>Bug report submitted!</p>
            <p>You can download the diagnostic package below.</p>
            <a href={downloadUrl} className="btn" target="_blank" rel="noopener noreferrer" style={{ display: 'inline-block', textDecoration: 'none' }}>Download Package</a>
            <div style={{ marginTop: '12px' }}>
              <button className="btn btn--secondary" onClick={onClose}>Close</button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {result && result.startsWith('error') && <p style={{ color: '#f44336' }}>{result}</p>}
            <div style={{ marginBottom: '12px' }}>
              <label>Title <input value={title} onChange={e => setTitle(e.target.value)} required style={{ width: '100%' }} /></label>
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label>Description <textarea value={description} onChange={e => setDescription(e.target.value)} required rows={4} style={{ width: '100%' }} /></label>
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label>Severity <select value={severity} onChange={e => setSeverity(e.target.value)} style={{ width: '100%' }}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select></label>
            </div>
            <div style={{ marginBottom: '8px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input type="checkbox" checked={includeLogs} onChange={e => setIncludeLogs(e.target.checked)} />
                Include recent logs
              </label>
            </div>
            <div style={{ marginBottom: '8px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input type="checkbox" checked={includeScreenshot} onChange={e => setIncludeScreenshot(e.target.checked)} />
                Include screenshot (explicit)
              </label>
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input type="checkbox" checked={includeReadiness} onChange={e => setIncludeReadiness(e.target.checked)} />
                Include readiness status
              </label>
            </div>
            <div style={{ background: '#fff3e0', padding: '8px', borderRadius: '4px', marginBottom: '12px', fontSize: '0.8rem' }}>
              <strong>Privacy Note:</strong> Passwords, tokens, secrets, and email addresses are automatically redacted. No invoice files or screenshots are included unless you explicitly check the box above.
            </div>
            <button className="btn" type="submit" disabled={submitting}>{submitting ? 'Submitting...' : 'Submit Bug Report'}</button>
          </form>
        )}
      </div>
    </div>
  )
}
