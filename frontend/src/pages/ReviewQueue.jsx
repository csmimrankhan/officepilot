import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatMoney, formatDateTime, STATUS_LABELS } from '../api.js'
import StatusBadge from '../components/StatusBadge.jsx'
import ConfidenceBar from '../components/ConfidenceBar.jsx'
import SourceBadge from '../components/SourceBadge.jsx'

const STATUS_ORDER = [
  'needs_review',
  'ready_for_approval',
  'approved',
  'rejected',
  'duplicate',
  'exported'
]

export default function ReviewQueue() {
  const [data, setData] = useState({ by_status: {}, counts: {} })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeStatus, setActiveStatus] = useState('all')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.reviewQueue(50)
      setData(res || { by_status: {}, counts: {} })
    } catch (err) {
      setError(err.message || 'Failed to load.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  // Build a flat list respecting the active status filter.
  const flat = []
  for (const status of STATUS_ORDER) {
    if (activeStatus !== 'all' && activeStatus !== status) continue
    for (const item of (data.by_status[status] || [])) {
      flat.push({ ...item, status })
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Review Queue</h2>
        <span className="subtle">{flat.length} invoice(s) in view · {Object.values(data.counts || {}).reduce((a, b) => a + b, 0)} total</span>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="toolbar" style={{ flexWrap: 'wrap' }}>
        <button
          type="button"
          className={activeStatus === 'all' ? '' : 'secondary'}
          onClick={() => setActiveStatus('all')}
        >All ({Object.values(data.counts || {}).reduce((a, b) => a + b, 0)})</button>
        {STATUS_ORDER.map((s) => (
          <button
            key={s}
            type="button"
            className={activeStatus === s ? '' : 'secondary'}
            onClick={() => setActiveStatus(s)}
          >
            {STATUS_LABELS[s] || s} ({data.counts?.[s] || 0})
          </button>
        ))}
        <button className="secondary" onClick={load} disabled={loading}>Refresh</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Source</th>
              <th>Vendor</th>
              <th>Invoice #</th>
              <th>Date</th>
              <th className="right">Total</th>
              <th>Confidence</th>
              <th>Status</th>
              <th>Notes</th>
              <th>Updated</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan="11" className="muted">Loading…</td></tr>}
            {!loading && flat.length === 0 && (
              <tr><td colSpan="11" className="muted">No invoices match the current filter.</td></tr>
            )}
            {flat.map((i) => (
              <tr key={i.id}>
                <td className="nowrap mono">#{i.id}</td>
                <td><SourceBadge source={i.source} /></td>
                <td>{i.vendor_name || <span className="muted">—</span>}</td>
                <td className="mono">{i.invoice_number || <span className="muted">—</span>}</td>
                <td className="nowrap">{i.invoice_date || <span className="muted">—</span>}</td>
                <td className="right nowrap">{formatMoney(i.total_amount, i.currency)}</td>
                <td><ConfidenceBar value={i.confidence_score} /></td>
                <td><StatusBadge status={i.status} /></td>
                <td className="subtle">
                  {i.status === 'duplicate' && i.duplicate_of_invoice_id && (
                    <span>↳ dup of <Link to={`/invoices/${i.duplicate_of_invoice_id}`}>#{i.duplicate_of_invoice_id}</Link></span>
                  )}
                  {i.status === 'rejected' && i.rejected_reason && (
                    <span title={i.rejected_reason}>⚠ {i.rejected_reason}</span>
                  )}
                  {i.status === 'approved' && i.approved_by && (
                    <span>by {i.approved_by}</span>
                  )}
                </td>
                <td className="nowrap subtle">{formatDateTime(i.updated_at)}</td>
                <td className="nowrap"><Link to={`/invoices/${i.id}`}>Open</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
