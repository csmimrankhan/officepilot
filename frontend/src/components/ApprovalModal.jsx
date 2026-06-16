import { useState } from 'react'

function formatValue(v) {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'object') return JSON.stringify(v, null, 2)
  return String(v)
}

/**
 * Modal that shows a pending workflow approval's before/after data
 * and lets the user approve or reject with an optional note.
 *
 * Props:
 *   approval      — the WorkflowApproval row (must have a `message`,
 *                   `before`, `after`, `node_name`)
 *   onApprove(note) — called with the optional note
 *   onReject(note)  — called with the optional note
 *   onClose()     — called to close the modal
 *   busy          — true while the parent is awaiting the API
 */
export default function ApprovalModal({ approval, onApprove, onReject, onClose, busy = false }) {
  const [note, setNote] = useState('')
  if (!approval) return null

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Approval required</h3>
          <button type="button" className="secondary" onClick={onClose} aria-label="Close">×</button>
        </div>
        <div className="modal-body">
          <div className="modal-row">
            <span className="subtle">Workflow node:</span>
            <code className="mono">{approval.node_name}</code>
          </div>
          {approval.message && (
            <p className="modal-message">{approval.message}</p>
          )}

          <div className="modal-grid">
            <div>
              <h4>Before</h4>
              <pre className="json-block">{formatValue(approval.before)}</pre>
            </div>
            <div>
              <h4>After</h4>
              <pre className="json-block">{formatValue(approval.after)}</pre>
            </div>
          </div>

          <label className="modal-field">
            <span>Decision note (optional)</span>
            <textarea
              rows={2}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. verified totals against PO-1234"
            />
          </label>
        </div>
        <div className="modal-footer">
          <button
            type="button"
            className="danger"
            onClick={() => onReject(note)}
            disabled={busy}
          >
            Reject
          </button>
          <button
            type="button"
            className="primary"
            onClick={() => onApprove(note)}
            disabled={busy}
          >
            {busy ? 'Working…' : 'Approve'}
          </button>
        </div>
      </div>
    </div>
  )
}
