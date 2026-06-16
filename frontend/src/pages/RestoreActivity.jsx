// Phase 10 — Restore Activity feed. Read-only view of every
// restore action (entity, file, or workflow) the system has taken.
// Surfaced in the sidebar so admins can audit "who reverted what,
// when".

import { useEffect, useState } from 'react'
import { api, formatDateTime } from '../api.js'

export default function RestoreActivity() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.listRestoreLogs({ limit: 200 })
      setRows(data || [])
    } catch (err) {
      setError(err.message || 'Failed to load restore activity')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <div className="page">
      <h2>Restore Activity</h2>
      <p className="muted">
        Every restore action — invoice, file snapshot, or workflow —
        is recorded here for audit. Restores are append-only; the
        previous state is preserved in version history.
      </p>

      {error && <div className="alert error">{error}</div>}

      {rows.length === 0 && !loading && (
        <div className="alert subtle">No restore activity yet.</div>
      )}

      {rows.length > 0 && (
        <div className="card">
          <table className="data-table">
            <thead>
              <tr>
                <th>When</th>
                <th>Entity</th>
                <th>Type</th>
                <th>From → To</th>
                <th>By</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{formatDateTime(r.restored_at)}</td>
                  <td>
                    {r.entity_type} #{r.entity_id}
                  </td>
                  <td>
                    <span className="badge subtle">
                      {r.target_id || '—'}
                    </span>
                  </td>
                  <td>
                    {r.restored_from_version
                      ? `v${r.restored_from_version} → v${r.restored_to_version}`
                      : 'snapshot'}
                  </td>
                  <td>{r.restored_by}</td>
                  <td className="change-summary">{r.reason || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
