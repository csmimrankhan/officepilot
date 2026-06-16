import { useState } from 'react'

export default function ConfirmModal({ title, message, confirmLabel = 'Confirm', danger, reasonRequired, onConfirm, onCancel }) {
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)

  const canConfirm = !reasonRequired || reason.trim().length > 0

  const handleConfirm = async () => {
    setBusy(true)
    try { await onConfirm(reasonRequired ? reason : undefined) } catch (_) {}
    setBusy(false)
  }

  return (
    <div className="modal-overlay" onClick={onCancel}>
      <div className="modal-content confirm-modal" onClick={e => e.stopPropagation()}>
        <h3>{title || 'Confirm'}</h3>
        <p>{message}</p>
        {reasonRequired && (
          <textarea placeholder="Reason for this action..." value={reason}
            onChange={e => setReason(e.target.value)} rows={3} />
        )}
        <div className="modal-actions">
          <button className="btn btn--secondary" onClick={onCancel}>Cancel</button>
          <button className={`btn ${danger ? 'btn--danger' : 'btn--primary'}`}
            disabled={!canConfirm || busy} onClick={handleConfirm}>
            {busy ? 'Processing...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
