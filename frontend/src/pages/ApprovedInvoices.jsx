import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatDateTime, formatMoney } from '../api.js'
import StatusBadge from '../components/StatusBadge.jsx'

export default function ApprovedInvoices() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true); setError('')
    try {
      const data = await api.listInvoices({ status: 'approved', limit: 500 })
      setItems(data)
    } catch (err) {
      setError(err.message || 'Failed to load.')
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  return (
    <div>
      <div className="page-header">
        <h2>Approved Invoices</h2>
        <span className="subtle">{items.length} ready to export</span>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="card" style={{ padding: 0 }}>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Vendor</th>
              <th>Invoice #</th>
              <th>Date</th>
              <th className="right">Total</th>
              <th>Status</th>
              <th>Approved</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan="8" className="muted">Loading…</td></tr>}
            {!loading && items.length === 0 && (
              <tr><td colSpan="8" className="muted">No approved invoices yet. Review and approve invoices to see them here.</td></tr>
            )}
            {items.map((i) => (
              <tr key={i.id}>
                <td className="mono">#{i.id}</td>
                <td>{i.vendor_name || <span className="muted">—</span>}</td>
                <td className="mono">{i.invoice_number || <span className="muted">—</span>}</td>
                <td className="nowrap">{i.invoice_date || <span className="muted">—</span>}</td>
                <td className="right nowrap">{formatMoney(i.total_amount, i.currency)}</td>
                <td><StatusBadge status={i.status} /></td>
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
