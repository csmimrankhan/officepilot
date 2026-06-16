import { useState } from 'react'
import { api } from '../api.js'

const FEEDBACK_TYPES = [
  { value: 'bug', label: 'Bug' },
  { value: 'confusing_ux', label: 'Confusing UX' },
  { value: 'extraction_mistake', label: 'Extraction Mistake' },
  { value: 'missing_feature', label: 'Missing Feature' },
  { value: 'performance_issue', label: 'Performance Issue' },
  { value: 'security_concern', label: 'Security Concern' },
  { value: 'general_feedback', label: 'General Feedback' },
]

export default function FeedbackModal({ onClose }) {
  const [type, setType] = useState('general_feedback')
  const [title, setTitle] = useState('')
  const [message, setMessage] = useState('')
  const [severity, setSeverity] = useState('medium')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!title.trim() || !message.trim()) return
    setSubmitting(true)
    try {
      const res = await api.createFeedback({
        feedback_type: type,
        title: title.trim(),
        message: message.trim(),
        severity,
        page_url: window.location.href,
      })
      setResult('success')
    } catch (err) {
      setResult('error: ' + err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
      <div className="card" style={{ width: '500px', maxHeight: '90vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0 }}>Send Feedback</h2>
          <button className="btn btn--small btn--secondary" onClick={onClose}>Close</button>
        </div>
        {result === 'success' ? (
          <div style={{ textAlign: 'center', padding: '24px' }}>
            <p style={{ color: '#4caf50', fontSize: '1.2rem' }}>Thank you for your feedback!</p>
            <button className="btn" onClick={onClose}>Close</button>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>
            {result && result.startsWith('error') && <p style={{ color: '#f44336' }}>{result}</p>}
            <div style={{ marginBottom: '12px' }}>
              <label>Type <select value={type} onChange={e => setType(e.target.value)} style={{ width: '100%' }}>
                {FEEDBACK_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select></label>
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label>Title <input value={title} onChange={e => setTitle(e.target.value)} required style={{ width: '100%' }} /></label>
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label>Message <textarea value={message} onChange={e => setMessage(e.target.value)} required rows={4} style={{ width: '100%' }} /></label>
            </div>
            <div style={{ marginBottom: '12px' }}>
              <label>Severity <select value={severity} onChange={e => setSeverity(e.target.value)} style={{ width: '100%' }}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select></label>
            </div>
            <p style={{ fontSize: '0.8rem', color: '#888' }}>Page: {window.location.href}</p>
            <button className="btn" type="submit" disabled={submitting}>{submitting ? 'Submitting...' : 'Submit Feedback'}</button>
          </form>
        )}
      </div>
    </div>
  )
}
