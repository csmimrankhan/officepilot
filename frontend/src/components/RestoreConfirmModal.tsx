import { useEffect, useState } from 'react'
import { formatDateTime } from '../api.js'

interface VersionInfo {
  version_number: number
  created_at: string
  created_by: string
}

interface RestoreConfirmModalProps {
  entityType: string
  entityId: string | number
  version: VersionInfo
  onClose: () => void
  onConfirm: (reason: string) => Promise<void>
}

export default function RestoreConfirmModal({
  entityType,
  entityId,
  version,
  onClose,
  onConfirm,
}: RestoreConfirmModalProps) {
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && !busy) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [busy, onClose])

  const canSubmit = reason.trim().length >= 3 && !busy

  const submit = async () => {
    if (!canSubmit) return
    setBusy(true)
    setErr('')
    try {
      await onConfirm(reason.trim())
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Restore failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" onClick={busy ? undefined : onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>Restore previous version</h3>
        <p className="muted">
          You are about to restore{' '}
          <code>
            {entityType}/{entityId}
          </code>{' '}
          to{' '}
          <strong>
            v{version.version_number}
          </strong>{' '}
          (created {formatDateTime(version.created_at)} by{' '}
          {version.created_by}).
        </p>
        <p className="muted small">
          A new version will be appended to history (this action is
          never destructive). Please describe why you want to roll
          back:
        </p>
        <textarea
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. wrong totals entered, reverting to parser output"
          disabled={busy}
        />
        {err && <div className="alert error">{err}</div>}
        <div className="modal-actions">
          <button onClick={onClose} disabled={busy}>Cancel</button>
          <button
            className="primary"
            onClick={submit}
            disabled={!canSubmit}
          >
            {busy ? 'Restoring…' : 'Restore this version'}
          </button>
        </div>
      </div>
    </div>
  )
}
