// Phase 10 — File Snapshots browser. Lists every snapshot the
// system has taken (excel exports, pre-move invoice files) and
// lets the user download or restore each one.

import { useEffect, useMemo, useState } from 'react'
import { api, formatDateTime } from '../api.js'
import RestoreConfirmModal from '../components/RestoreConfirmModal.jsx'

export default function FileSnapshots() {
  const [fileType, setFileType] = useState('')
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.listFileSnapshots({
        fileType: fileType || null,
        limit: 200,
      })
      setRows(data || [])
    } catch (err) {
      setError(err.message || 'Failed to load snapshots')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileType])

  const onRestore = async (id, reason) => {
    await api.restoreFileSnapshot(id, { actor: 'user', reason })
    setPending(null)
    await load()
  }

  const groupedByType = useMemo(() => {
    const out = {}
    for (const r of rows) {
      (out[r.file_type] ||= []).push(r)
    }
    return out
  }, [rows])

  return (
    <div className="page">
      <h2>File Snapshots</h2>
      <p className="muted">
        Snapshots are taken automatically before destructive file
        operations. Restore copies the snapshot back to its original
        path; the audit log records who, when, and why.
      </p>

      <div className="card version-picker">
        <div className="field-row">
          <label>File type</label>
          <select
            value={fileType}
            onChange={(e) => setFileType(e.target.value)}
          >
            <option value="">All</option>
            <option value="excel_export">Excel exports</option>
            <option value="invoice_file">Invoice files (pre-move)</option>
          </select>
        </div>
        <button className="primary" onClick={load} disabled={loading}>
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      {Object.keys(groupedByType).length === 0 && !loading && (
        <div className="alert subtle">
          No snapshots yet. Snapshots are created when you export to
          Excel or when the organizer moves a file.
        </div>
      )}

      {Object.entries(groupedByType).map(([type, items]) => (
        <div className="card" key={type}>
          <h3>
            {type} <span className="muted small">({items.length})</span>
          </h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>When</th>
                <th>Action</th>
                <th>Original path</th>
                <th>Size</th>
                <th>Hash</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => (
                <tr key={s.id}>
                  <td>{formatDateTime(s.created_at)}</td>
                  <td>
                    <span className="badge subtle">{s.action_type}</span>
                  </td>
                  <td className="path" title={s.original_path}>
                    {s.original_path}
                  </td>
                  <td>
                    {s.size_bytes
                      ? `${(s.size_bytes / 1024).toFixed(1)} KB`
                      : '—'}
                  </td>
                  <td className="hash">
                    {s.file_hash_before
                      ? `${s.file_hash_before.slice(0, 12)}…`
                      : '—'}
                  </td>
                  <td>
                    <span
                      className={`badge ${
                        s.restore_status === 'restored'
                          ? 'ok'
                          : s.restore_status === 'missing'
                            ? 'failed'
                            : 'subtle'
                      }`}
                    >
                      {s.restore_status} ({s.restore_count})
                    </span>
                  </td>
                  <td className="actions">
                    <a
                      className="link"
                      href={`/api/file-snapshots/${s.id}/download`}
                      onClick={(e) => {
                        e.preventDefault()
                        window.open(
                          `${api.base}/api/file-snapshots/${s.id}/download`,
                          '_blank'
                        )
                      }}
                    >
                      Download
                    </a>
                    {' · '}
                    <button
                      className="link"
                      onClick={() => setPending(s)}
                      disabled={s.restore_status === 'missing'}
                    >
                      Restore
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}

      {pending && (
        <RestoreConfirmModal
          entityType="file_snapshot"
          entityId={String(pending.id)}
          version={{
            version_number: 1,
            created_at: pending.created_at,
            created_by: pending.created_by,
          }}
          onClose={() => setPending(null)}
          onConfirm={(reason) => onRestore(pending.id, reason)}
        />
      )}
    </div>
  )
}
