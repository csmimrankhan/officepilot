import { useEffect, useState } from 'react'

export default function AccountingSyncPreviewModal({ preview, provider, invoiceId, onApprove, onReject, onClose, busy = false, errorMessage = '' }) {
  const [reason, setReason] = useState('Reviewed preview; approved for accounting sync.')

  useEffect(() => {
    if (preview) setReason('Reviewed preview; approved for accounting sync.')
  }, [preview?.preview_id])

  if (!preview) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <div className="modal-body">
            <div className="subtle">Building sync preview…</div>
          </div>
        </div>
      </div>
    )
  }

  const p = preview.preview || {}
  const mapping = p.mapping || {}
  const invoice = p.invoice || {}
  const blockers = preview.blockers || []
  const warnings = preview.warnings || []

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{provider} Sync Preview — Invoice #{invoiceId}</h3>
          <button type="button" className="secondary" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="modal-body">
          {errorMessage && <div className="alert error">{errorMessage}</div>}
          {blockers.length > 0 && (
            <div className="alert error">
              <strong>Blockers — sync cannot proceed:</strong>
              <ul style={{ margin: '4px 0 0 18px' }}>
                {blockers.map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
          )}
          {warnings.length > 0 && (
            <div className="alert warning">
              <strong>Warnings:</strong>
              <ul style={{ margin: '4px 0 0 18px' }}>
                {warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
          <div className="modal-grid">
            <div>
              <div className="modal-row"><span className="subtle">Provider:</span> <code className="mono">{provider}</code></div>
              <div className="modal-row"><span className="subtle">Invoice:</span> <code className="mono">#{invoiceId}</code></div>
              <div className="modal-row"><span className="subtle">Vendor:</span> <span>{invoice.vendor_name || '—'}</span></div>
              <div className="modal-row"><span className="subtle">Number:</span> <code className="mono">{invoice.invoice_number || '—'}</code></div>
            </div>
            <div>
              <div className="modal-row"><span className="subtle">Date:</span> <span>{invoice.invoice_date || '—'}</span></div>
              <div className="modal-row"><span className="subtle">Total:</span> <strong>{invoice.currency || 'USD'} {invoice.total_amount || '—'}</strong></div>
              <div className="modal-row"><span className="subtle">Risk:</span> <span className={`badge ${preview.risk_level || 'medium'}`}>{preview.risk_level || 'medium'}</span></div>
              <div className="modal-row"><span className="subtle">Approval required:</span> <strong>{preview.approval_required ? 'Yes' : 'No'}</strong></div>
            </div>
          </div>
          <div className="card" style={{ background: '#f9fbfd' }}>
            <h4>Mapped Fields</h4>
            <table className="data-table">
              <thead>
                <tr><th>Local Field</th><th>Local Value</th><th>External Field</th><th>External Value</th><th>Mapped</th></tr>
              </thead>
              <tbody>
                {(mapping.fields || []).map((f, i) => (
                  <tr key={i}>
                    <td><code className="mono">{f.local_field}</code></td>
                    <td>{f.local_value || '—'}</td>
                    <td><code className="mono">{f.external_field || '—'}</code></td>
                    <td>{f.external_value || '—'}</td>
                    <td>{f.mapped ? <span className="badge ok">✓</span> : <span className="badge failed">✗</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="modal-grid">
              <div>
                <div className="modal-row"><span className="subtle">Vendor mapping:</span> {mapping.vendor?.mapped ? <span className="badge ok">{mapping.vendor.external_name || mapping.vendor.external_id}</span> : <span className="badge failed">Unmapped</span>}</div>
              </div>
              <div>
                <div className="modal-row"><span className="subtle">Account mapping:</span> {mapping.account?.mapped ? <span className="badge ok">{mapping.account.external_name || mapping.account.external_id}</span> : <span className="badge warning">Unmapped</span>}</div>
              </div>
            </div>
          </div>
          <label className="modal-field">
            <span>Decision note</span>
            <textarea rows={2} value={reason} onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. reviewed mapped fields; approved for draft sync" />
          </label>
        </div>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={busy}>Close</button>
          <button type="button" className="secondary" onClick={() => onReject?.(reason)} disabled={busy || blockers.length > 0}>Reject</button>
          <button type="button" className="primary" onClick={() => onApprove?.(reason)}
            disabled={busy || blockers.length > 0 || !preview.approval_required}>
            {busy ? 'Working…' : 'Approve & Sync'}
          </button>
        </div>
      </div>
    </div>
  )
}
