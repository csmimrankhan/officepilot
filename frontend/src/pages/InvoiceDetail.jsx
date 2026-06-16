import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { api, formatDateTime, formatMoney } from '../api.js'
import StatusBadge from '../components/StatusBadge.jsx'
import ConfidenceBar from '../components/ConfidenceBar.jsx'
import SourceBadge from '../components/SourceBadge.jsx'
import FilePreview from '../components/FilePreview.jsx'
import AuditTimeline from '../components/AuditTimeline.jsx'

const EMPTY_ITEM = { description: '', quantity: '', unit_price: '', line_total: '' }

export default function InvoiceDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [inv, setInv] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState(null)
  const [lineItems, setLineItems] = useState([])
  const [rejectReason, setRejectReason] = useState('')
  const [dupOf, setDupOf] = useState('')
  const [auditKey, setAuditKey] = useState(0)
  const [previewKey, setPreviewKey] = useState(0)

  const load = async () => {
    setError('')
    try {
      const data = await api.getInvoice(id)
      setInv(data)
      setForm({
        vendor_name: data.vendor_name || '',
        invoice_number: data.invoice_number || '',
        invoice_date: data.invoice_date || '',
        due_date: data.due_date || '',
        currency: data.currency || '',
        subtotal: data.subtotal ?? '',
        tax: data.tax ?? '',
        total_amount: data.total_amount ?? '',
        notes: data.notes || ''
      })
      setLineItems((data.line_items || []).map((li) => ({
        description: li.description || '',
        quantity: li.quantity ?? '',
        unit_price: li.unit_price ?? '',
        line_total: li.line_total ?? ''
      })))
    } catch (err) {
      setError(err.message || 'Failed to load invoice.')
    }
  }

  useEffect(() => { load() }, [id])

  const onField = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))

  const updateLine = (idx, key, val) => {
    setLineItems((items) => items.map((it, i) => i === idx ? { ...it, [key]: val } : it))
  }
  const addLine = () => setLineItems((items) => [...items, { ...EMPTY_ITEM }])
  const removeLine = (idx) => setLineItems((items) => items.filter((_, i) => i !== idx))

  const save = async () => {
    setBusy(true); setError('')
    try {
      const payload = {
        ...form,
        subtotal: form.subtotal === '' ? null : Number(form.subtotal),
        tax: form.tax === '' ? null : Number(form.tax),
        total_amount: form.total_amount === '' ? null : Number(form.total_amount),
        line_items: lineItems.map((li) => ({
          description: li.description || null,
          quantity: li.quantity === '' ? null : Number(li.quantity),
          unit_price: li.unit_price === '' ? null : Number(li.unit_price),
          line_total: li.line_total === '' ? null : Number(li.line_total)
        }))
      }
      const updated = await api.updateInvoice(inv.id, payload)
      setInv(updated)
      setAuditKey((k) => k + 1)
    } catch (err) {
      setError(err.message || 'Save failed.')
    } finally {
      setBusy(false)
    }
  }

  const approve = async () => {
    setBusy(true); setError('')
    try {
      const updated = await api.approveInvoice(inv.id)
      setInv(updated)
      setAuditKey((k) => k + 1)
      setPreviewKey((k) => k + 1)
    } catch (err) {
      setError(err.message || 'Approve failed.')
    } finally { setBusy(false) }
  }

  const reject = async () => {
    if (!rejectReason.trim()) { setError('Please provide a reason for rejection.'); return }
    setBusy(true); setError('')
    try {
      const updated = await api.rejectInvoice(inv.id, rejectReason.trim())
      setInv(updated)
      setRejectReason('')
      setAuditKey((k) => k + 1)
    } catch (err) {
      setError(err.message || 'Reject failed.')
    } finally { setBusy(false) }
  }

  const markDuplicate = async () => {
    const target = Number(dupOf)
    if (!target || target === inv.id) { setError('Enter a valid target invoice id.'); return }
    setBusy(true); setError('')
    try {
      const updated = await api.markDuplicate(inv.id, target)
      setInv(updated)
      setDupOf('')
      setAuditKey((k) => k + 1)
    } catch (err) {
      setError(err.message || 'Mark duplicate failed.')
    } finally { setBusy(false) }
  }

  const organizeNow = async () => {
    setBusy(true); setError('')
    try {
      const updated = await api.organizeFile(inv.id)
      setInv(updated)
      setAuditKey((k) => k + 1)
      setPreviewKey((k) => k + 1)
    } catch (err) {
      setError(err.message || 'Organize failed.')
    } finally { setBusy(false) }
  }

  if (error && !inv) return <div className="alert error">{error}</div>
  if (!inv || !form) return <div className="card">Loading invoice #{id}…</div>

  const isLocked = inv.status === 'duplicate' || inv.status === 'rejected' || inv.status === 'approved'
  const isOrganized = !!(inv.file && inv.file.organized_path)

  return (
    <div>
      <div className="page-header">
        <h2>
          Invoice #{inv.id} <StatusBadge status={inv.status} />{' '}
          <SourceBadge source={inv.file?.source} emailImportId={inv.file?.email_import_id} />
        </h2>
        <div>
          <Link to="/review" className="subtle">← Back to Review Queue</Link>
        </div>
      </div>

      {inv.duplicate_of_invoice_id && (
        <div className="alert warning">
          Marked as duplicate of <Link to={`/invoices/${inv.duplicate_of_invoice_id}`}>invoice #{inv.duplicate_of_invoice_id}</Link>.
          Approve is blocked.
        </div>
      )}

      {inv.status === 'rejected' && inv.rejected_reason && (
        <div className="alert warning">
          <strong>Rejection reason:</strong> {inv.rejected_reason}
        </div>
      )}

      {inv.status === 'approved' && inv.approved_by && (
        <div className="alert info">
          Approved by <strong>{inv.approved_by}</strong> on {formatDateTime(inv.approved_at)}.
          {isOrganized && (
            <span> File moved to: <code>{inv.file.organized_path}</code></span>
          )}
        </div>
      )}

      {error && <div className="alert error">{error}</div>}

      <div className="card">
        <div className="grid-3">
          <div>
            <label>Vendor Name</label>
            <input type="text" value={form.vendor_name} onChange={onField('vendor_name')} disabled={isLocked} />
          </div>
          <div>
            <label>Invoice Number</label>
            <input type="text" value={form.invoice_number} onChange={onField('invoice_number')} disabled={isLocked} />
          </div>
          <div>
            <label>Currency</label>
            <input type="text" value={form.currency} onChange={onField('currency')} disabled={isLocked} maxLength={6} />
          </div>
          <div>
            <label>Invoice Date</label>
            <input type="text" value={form.invoice_date} onChange={onField('invoice_date')} disabled={isLocked} placeholder="YYYY-MM-DD" />
          </div>
          <div>
            <label>Due Date</label>
            <input type="text" value={form.due_date} onChange={onField('due_date')} disabled={isLocked} placeholder="YYYY-MM-DD" />
          </div>
          <div>
            <label>Confidence</label>
            <div style={{ paddingTop: 8 }}><ConfidenceBar value={inv.confidence_score} /></div>
          </div>
          <div>
            <label>Subtotal</label>
            <input type="number" step="0.01" value={form.subtotal} onChange={onField('subtotal')} disabled={isLocked} />
          </div>
          <div>
            <label>Tax</label>
            <input type="number" step="0.01" value={form.tax} onChange={onField('tax')} disabled={isLocked} />
          </div>
          <div>
            <label>Total</label>
            <input type="number" step="0.01" value={form.total_amount} onChange={onField('total_amount')} disabled={isLocked} />
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Line Items</h3>
        <table>
          <thead>
            <tr>
              <th>Description</th>
              <th style={{ width: 110 }}>Qty</th>
              <th style={{ width: 130 }}>Unit Price</th>
              <th style={{ width: 130 }}>Line Total</th>
              <th style={{ width: 60 }}></th>
            </tr>
          </thead>
          <tbody>
            {lineItems.length === 0 && (
              <tr><td colSpan="5" className="muted">No line items detected.</td></tr>
            )}
            {lineItems.map((li, idx) => (
              <tr key={idx}>
                <td><input type="text" value={li.description} onChange={(e) => updateLine(idx, 'description', e.target.value)} disabled={isLocked} /></td>
                <td><input type="number" step="0.01" value={li.quantity} onChange={(e) => updateLine(idx, 'quantity', e.target.value)} disabled={isLocked} /></td>
                <td><input type="number" step="0.01" value={li.unit_price} onChange={(e) => updateLine(idx, 'unit_price', e.target.value)} disabled={isLocked} /></td>
                <td><input type="number" step="0.01" value={li.line_total} onChange={(e) => updateLine(idx, 'line_total', e.target.value)} disabled={isLocked} /></td>
                <td>
                  <button className="secondary" type="button" onClick={() => removeLine(idx)} disabled={isLocked} style={{ padding: '4px 8px' }}>×</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ marginTop: 8 }}>
          <button className="secondary" type="button" onClick={addLine} disabled={isLocked}>+ Add line</button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Reviewer Notes</h3>
        <textarea value={form.notes} onChange={onField('notes')} placeholder="Optional notes for the audit trail" disabled={isLocked} />
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Warnings</h3>
        {inv.warnings_json && inv.warnings_json.length > 0 ? (
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {inv.warnings_json.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        ) : <div className="muted">No warnings.</div>}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>File Preview</h3>
        <FilePreview invoice={inv} refreshKey={previewKey} />
        {inv.file && (
          <div className="subtle" style={{ marginTop: 8 }}>
            <strong>{inv.file.original_filename}</strong> · {inv.file.mime_type} · {inv.file.size} bytes
            <div className="mono">sha256: {inv.file.file_hash}</div>
            {inv.file.original_path && inv.file.current_path && inv.file.original_path !== inv.file.current_path && (
              <div>
                Original: <code>{inv.file.original_path}</code><br />
                Current: <code>{inv.file.current_path}</code>
                {inv.file.organized_path && (
                  <><br />Organized: <code>{inv.file.organized_path}</code></>
                )}
              </div>
            )}
            {inv.file.source === 'email' && inv.file.email_import_id && (
              <div style={{ marginTop: 6 }}>
                Imported from email · <Link to={`/imported-emails/${inv.file.email_import_id}`}>view email import #{inv.file.email_import_id}</Link>
              </div>
            )}
          </div>
        )}
        <details style={{ marginTop: 8 }}>
          <summary>View extracted raw text</summary>
          <pre>{inv.raw_text || <span className="muted">(empty)</span>}</pre>
        </details>
      </div>

      <div className="card">
        <div className="toolbar" style={{ flexWrap: 'wrap' }}>
          <button onClick={save} disabled={busy || isLocked}>Save edits</button>
          <button className="success" onClick={approve} disabled={busy || isLocked || inv.status === 'approved' || inv.status === 'duplicate'}>
            Approve
          </button>
          <input
            type="text"
            placeholder="Reject reason…"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            disabled={isLocked}
            style={{ maxWidth: 280 }}
          />
          <button className="danger" onClick={reject} disabled={busy || isLocked || inv.status === 'rejected'}>
            Reject
          </button>
          {isLocked && <span className="subtle">This invoice is locked ({inv.status}).</span>}
        </div>
        <div className="toolbar" style={{ flexWrap: 'wrap', marginTop: 8 }}>
          <input
            type="number"
            placeholder="Original invoice #"
            value={dupOf}
            onChange={(e) => setDupOf(e.target.value)}
            disabled={isLocked}
            style={{ maxWidth: 200 }}
          />
          <Link
            to={`/browser/test-form?invoice_id=${inv.id}`}
            className="secondary"
            style={{ padding: '4px 10px' }}
          >
            Fill test form (browser)
          </Link>
          <Link
            to={`/browser/logs`}
            className="secondary"
            style={{ padding: '4px 10px' }}
          >
            View browser logs
          </Link>
          <Link
            to={`/accounting?invoice_id=${inv.id}&provider=quickbooks`}
            className="secondary"
            style={{ padding: '4px 10px' }}
          >
            Sync to QuickBooks
          </Link>
          <Link
            to={`/accounting?invoice_id=${inv.id}&provider=xero`}
            className="secondary"
            style={{ padding: '4px 10px' }}
          >
            Sync to Xero
          </Link>
          <Link
            to={`/accounting/sync-logs?invoice_id=${inv.id}`}
            className="secondary"
            style={{ padding: '4px 10px' }}
          >
            View sync logs
          </Link>
          <button
            className="secondary"
            onClick={markDuplicate}
            disabled={busy || isLocked || inv.status === 'duplicate'}
          >Mark as duplicate</button>
          <button
            className="secondary"
            onClick={organizeNow}
            disabled={busy || !inv.file}
            title="Move this file using the configured folder rules."
          >Organize file now</button>
          <Link to="/settings/folder" className="subtle">Configure folder rules →</Link>
        </div>
        <div className="toolbar" style={{ flexWrap: 'wrap', marginTop: 8 }}>
          <Link
            to={`/screen/assistant`}
            className="secondary"
            style={{ padding: '4px 10px' }}
          >
            Open in Screen Assistant
          </Link>
          <Link
            to={`/screen/logs`}
            className="secondary"
            style={{ padding: '4px 10px' }}
          >
            View Screen Logs
          </Link>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Audit Timeline</h3>
        <AuditTimeline invoiceId={inv.id} refreshKey={auditKey} />
      </div>
    </div>
  )
}
