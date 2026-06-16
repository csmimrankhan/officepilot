import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, formatDateTime, IMPORT_STATUS_LABELS } from '../api.js'

export default function ImportedEmailDetail() {
  const { id } = useParams()
  const [item, setItem] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    (async () => {
      setError('')
      try {
        const data = await api.getEmailImport(id)
        setItem(data)
      } catch (err) {
        setError(err.message || 'Failed to load.')
      }
    })()
  }, [id])

  if (error) return <div className="alert error">{error}</div>
  if (!item) return <div className="card">Loading…</div>

  const bd = item.score_breakdown || {}

  return (
    <div>
      <div className="page-header">
        <h2>Email Import #{item.id}</h2>
        <Link to="/imported-emails" className="subtle">← Back</Link>
      </div>

      <div className="card">
        <div className="grid-2">
          <div>
            <label>Subject</label>
            <div>{item.subject || <span className="muted">(no subject)</span>}</div>
          </div>
          <div>
            <label>From</label>
            <div className="mono">{item.sender || '—'}</div>
          </div>
          <div>
            <label>Received</label>
            <div>{formatDateTime(item.received_at)}</div>
          </div>
          <div>
            <label>Status</label>
            <div><span className={`badge ${item.status}`}>{IMPORT_STATUS_LABELS[item.status] || item.status}</span></div>
          </div>
          <div>
            <label>Score</label>
            <div>{Math.round((item.score || 0) * 100)}%</div>
          </div>
          <div>
            <label>Message ID</label>
            <div className="mono subtle">{item.provider_message_id}</div>
          </div>
        </div>
        {item.snippet && (
          <div style={{ marginTop: 12 }}>
            <label>Snippet</label>
            <div className="muted">{item.snippet}</div>
          </div>
        )}
        {item.error && (
          <div className="alert error" style={{ marginTop: 12 }}>{item.error}</div>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Scoring breakdown</h3>
        {bd.matched?.length > 0 ? (
          <ul style={{ marginTop: 0 }}>
            {bd.matched.map((m, i) => <li key={i} className="mono">{m}</li>)}
          </ul>
        ) : <div className="muted">No positive matches.</div>}
        {bd.reasons?.length > 0 && (
          <details style={{ marginTop: 8 }}>
            <summary>Reasoning</summary>
            <ul>{bd.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
          </details>
        )}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Attachments</h3>
        {item.attachments?.length === 0 && <div className="muted">No attachments recorded.</div>}
        {item.attachments?.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Filename</th>
                <th>Mime</th>
                <th>Size</th>
                <th>Status</th>
                <th>Invoice</th>
              </tr>
            </thead>
            <tbody>
              {item.attachments.map((a) => (
                <tr key={a.id}>
                  <td className="mono">{a.filename}</td>
                  <td className="subtle">{a.mime_type || '—'}</td>
                  <td className="nowrap">{a.size}</td>
                  <td><span className={`badge ${a.status === 'imported' ? 'approved' : a.status === 'duplicate' ? 'duplicate' : a.status === 'error' ? 'rejected' : 'pending'}`}>{a.status}</span></td>
                  <td>
                    {a.processed_invoice_id
                      ? <Link to={`/invoices/${a.processed_invoice_id}`}>#{a.processed_invoice_id}</Link>
                      : <span className="muted">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
