import { useEffect, useState } from 'react'
import { api, BROWSER_RISK_LABELS } from '../api.js'

/**
 * Modal that shows a browser action preview and lets the user
 * approve / reject / cancel. Renders nothing while the preview
 * is being fetched.
 *
 * Props:
 *   preview          — the BrowserPreviewResponse (or null while loading)
 *   onApprove(reason)
 *   onReject(reason)
 *   onCancel(reason)
 *   onClose()
 *   busy             — true while the parent is awaiting the API
 *   errorMessage     — optional error string from the last API call
 */
export default function BrowserPreviewModal({ preview, onApprove, onReject, onCancel, onClose, busy = false, errorMessage = '' }) {
  const [reason, setReason] = useState('Reviewed preview; safe to proceed.')

  useEffect(() => {
    if (preview) setReason('Reviewed preview; safe to proceed.')
  }, [preview?.run_id])

  if (!preview) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <div className="modal-body">
            <div className="subtle">Building preview…</div>
          </div>
        </div>
      </div>
    )
  }

  const p = preview.preview || {}
  const risk = p.risk || {}
  const decision = p.domain_decision || {}
  const steps = p.steps || []
  const notes = p.notes || []

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Browser automation preview</h3>
          <button type="button" className="secondary" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="modal-body">
          {errorMessage && <div className="alert error">{errorMessage}</div>}

          <div className="modal-grid">
            <div>
              <div className="modal-row">
                <span className="subtle">Action:</span>
                <code className="mono">{p.action_type}</code>
              </div>
              <div className="modal-row">
                <span className="subtle">Target URL:</span>
                <code className="mono">{p.target_url || '—'}</code>
              </div>
              <div className="modal-row">
                <span className="subtle">Target domain:</span>
                <code className="mono">{p.target_domain || '—'}</code>
              </div>
            </div>
            <div>
              <div className="modal-row">
                <span className="subtle">Risk level:</span>
                <span className={`badge ${risk.risk_level || 'low'}`}>
                  {BROWSER_RISK_LABELS[risk.risk_level] || risk.risk_level}
                </span>
              </div>
              <div className="modal-row">
                <span className="subtle">Approval required:</span>
                <strong>{preview.requires_approval ? 'Yes' : 'No'}</strong>
              </div>
              <div className="modal-row">
                <span className="subtle">Domain check:</span>
                <span className={`badge ${decision.allowed ? 'ok' : 'failed'}`}>
                  {decision.allowed ? 'Allowed' : 'Blocked'}
                </span>
              </div>
            </div>
          </div>

          {decision.reason && (
            <div className="alert info">
              <strong>Domain decision:</strong> {decision.reason}
            </div>
          )}

          {notes.length > 0 && (
            <ul className="phase-list">
              {notes.map((n, i) => <li key={i}>{n}</li>)}
            </ul>
          )}

          {steps.length > 0 && (
            <div>
              <h4>Planned steps ({steps.length})</h4>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Step</th>
                    <th>Description</th>
                    <th>Value (redacted)</th>
                    <th>Approval</th>
                  </tr>
                </thead>
                <tbody>
                  {steps.map((s) => (
                    <tr key={s.step_order}>
                      <td>{s.step_order + 1}</td>
                      <td><code className="mono">{s.step_type}</code></td>
                      <td>{s.target_description}</td>
                      <td className="mono">{s.input_value_redacted || '—'}</td>
                      <td>
                        {s.requires_approval
                          ? <span className="badge medium">Required</span>
                          : <span className="badge subtle">Not required</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {(risk.reasons || []).length > 0 && (
            <div className="alert info">
              <strong>Why this risk level:</strong>
              <ul style={{ margin: '4px 0 0 18px' }}>
                {risk.reasons.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}

          <label className="modal-field">
            <span>Decision note (required to approve / reject)</span>
            <textarea
              rows={2}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. reviewed the row that will be appended"
            />
          </label>
        </div>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={busy}>
            Close
          </button>
          <button type="button" className="secondary" onClick={() => onCancel?.(reason)} disabled={busy}>
            Cancel
          </button>
          <button type="button" className="secondary" onClick={() => onReject?.(reason)} disabled={busy}>
            Reject
          </button>
          <button
            type="button"
            className="primary"
            onClick={() => onApprove?.(reason)}
            disabled={busy || !preview.requires_approval}
            title={preview.requires_approval ? 'Approve and run' : 'No approval required for this action'}
          >
            {busy ? 'Working…' : (preview.requires_approval ? 'Approve & run' : 'Run without approval')}
          </button>
        </div>
      </div>
    </div>
  )
}
