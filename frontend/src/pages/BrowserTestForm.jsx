import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import BrowserPreviewModal from '../components/BrowserPreviewModal.jsx'

/**
 * Safe local browser automation playground. Shows the local
 * test form on the left and a "fill with this invoice" panel
 * on the right. The preview modal walks the user through the
 * approval flow before anything touches the form.
 */
export default function BrowserTestForm() {
  const [params] = useSearchParams()
  const initialInvoice = params.get('invoice_id') ? Number(params.get('invoice_id')) : null

  const [invoices, setInvoices] = useState([])
  const [invoiceId, setInvoiceId] = useState(initialInvoice || '')
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [modalError, setModalError] = useState('')
  const [lastSaved, setLastSaved] = useState(null)

  const loadInvoices = useCallback(async () => {
    try {
      const rows = await api.listInvoices({ status: 'APPROVED', limit: 50 })
      setInvoices(rows)
    } catch (err) {
      setError(err.message || 'Failed to load invoices.')
    }
  }, [])

  useEffect(() => { loadInvoices() }, [loadInvoices])

  // The test form itself posts to window.__lastTestFormSubmission;
  // we poll it from the iframe below.
  useEffect(() => {
    const timer = setInterval(() => {
      try {
        const iframe = document.getElementById('op-test-form-iframe')
        if (!iframe || !iframe.contentWindow) return
        const data = iframe.contentWindow.__lastTestFormSubmission
        if (data && JSON.stringify(data) !== JSON.stringify(lastSaved)) {
          setLastSaved(data)
        }
      } catch (_) {
        // cross-origin etc.; safe to ignore
      }
    }, 1500)
    return () => clearInterval(timer)
  }, [lastSaved])

  const buildPreview = async (submitAfter) => {
    if (!invoiceId) {
      setError('Pick an approved invoice to fill into the form.')
      return
    }
    setError('')
    setMessage('')
    setModalError('')
    try {
      const res = await api.fillTestFormPreview({
        invoice_id: Number(invoiceId),
        actor: 'user',
        submit: !!submitAfter
      })
      setPreview(res)
    } catch (err) {
      setError(err.message || 'Failed to build preview.')
    }
  }

  const approve = async (reason) => {
    if (!preview?.run_id) return
    setBusy(true)
    setModalError('')
    try {
      await api.approveBrowserAction(preview.run_id, { actor: 'user', reason })
      setMessage(`Browser action approved and run #${preview.run_id} completed.`)
      setPreview(null)
    } catch (err) {
      setModalError(err.message || 'Approval failed.')
    } finally {
      setBusy(false)
    }
  }

  const reject = async (reason) => {
    if (!preview?.run_id) {
      setPreview(null)
      return
    }
    setBusy(true)
    try {
      await api.rejectBrowserAction(preview.run_id, { actor: 'user', reason })
      setMessage('Preview rejected; no form fields were touched.')
      setPreview(null)
    } catch (err) {
      setModalError(err.message || 'Rejection failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Local Test Web Form</h2>
        <span className="subtle">A safe target for browser automation drills.</span>
      </div>

      {error && <div className="alert error">{error}</div>}
      {message && <div className="alert success">{message}</div>}

      <div className="card">
        <h3>1. Pick an approved invoice</h3>
        <p className="subtle">The selected invoice's fields will be redacted and shown in the preview modal before anything is written.</p>
        <select
          value={invoiceId}
          onChange={(e) => setInvoiceId(e.target.value)}
          style={{ minWidth: 320 }}
        >
          <option value="">— select invoice —</option>
          {invoices.map((i) => (
            <option key={i.id} value={i.id}>
              #{i.id} — {i.vendor_name || 'unknown'} — {i.invoice_number || 'no number'}
            </option>
          ))}
        </select>

        <div className="toolbar" style={{ marginTop: 12 }}>
          <button type="button" className="primary" onClick={() => buildPreview(false)} disabled={!invoiceId}>
            Build fill-form preview
          </button>
          <button type="button" className="secondary" onClick={() => buildPreview(true)} disabled={!invoiceId}>
            Build submit-form preview (high risk)
          </button>
        </div>
      </div>

      <div className="card">
        <h3>2. The test form itself</h3>
        <p className="subtle">
          The iframe loads <code>{api.testFormUrl()}</code>. Submissions are kept in memory and shown below.
        </p>
        <iframe
          id="op-test-form-iframe"
          title="Local test form"
          src={api.testFormUrl()}
          style={{ width: '100%', height: 480, border: '1px solid #cbd2d9', borderRadius: 6 }}
        />
        {lastSaved && (
          <div className="card" style={{ background: '#f4f5f7', marginTop: 12 }}>
            <h4>Last saved draft (from the form iframe)</h4>
            <pre className="json-block">{JSON.stringify(lastSaved, null, 2)}</pre>
          </div>
        )}
      </div>

      <BrowserPreviewModal
        preview={preview}
        onApprove={approve}
        onReject={reject}
        onCancel={() => setPreview(null)}
        onClose={() => setPreview(null)}
        busy={busy}
        errorMessage={modalError}
      />
    </div>
  )
}
