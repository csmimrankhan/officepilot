// Phase 10 — Version History browser.
//
// This page lets the user view and restore prior versions of any
// tracked entity (invoices, settings, workflow runs). It accepts an
// optional ``entityType`` + ``entityId`` route param so it can be
// embedded from an invoice's detail page with a deep link.

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, formatDateTime } from '../api.js'
import RestoreConfirmModal from '../components/RestoreConfirmModal.jsx'

const ENTITY_PRESETS = [
  { type: 'invoice', label: 'Invoice', hint: 'e.g. invoice/42' },
  { type: 'settings', label: 'Settings', hint: 'e.g. settings/folder_rules' },
  { type: 'extraction', label: 'Extraction', hint: 'e.g. extraction/42' },
]

export default function VersionHistory() {
  const { entityType: typeParam, entityId: idParam } = useParams()
  const [entityType, setEntityType] = useState(typeParam || 'invoice')
  const [entityId, setEntityId] = useState(idParam || '')
  const [versions, setVersions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [pendingRestore, setPendingRestore] = useState(null)

  useEffect(() => {
    if (typeParam) setEntityType(typeParam)
    if (idParam) setEntityId(idParam)
  }, [typeParam, idParam])

  const canLoad = useMemo(
    () => entityType.trim().length > 0 && entityId.trim().length > 0,
    [entityType, entityId]
  )

  const load = async () => {
    if (!canLoad) return
    setLoading(true)
    setError('')
    try {
      const rows = await api.listVersions(entityType.trim(), entityId.trim())
      setVersions(rows || [])
    } catch (err) {
      setError(err.message || 'Failed to load versions')
      setVersions([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (canLoad) load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entityType, entityId])

  const onRestore = async (versionNumber, reason) => {
    const newV = await api.restoreVersion(
      entityType.trim(),
      entityId.trim(),
      versionNumber,
      { actor: 'user', reason }
    )
    setPendingRestore(null)
    await load()
    return newV
  }

  return (
    <div className="page">
      <h2>Version History</h2>
      <p className="muted">
        Browse and restore prior versions of any tracked entity.
        Restoring never deletes history — a new version is appended
        with a link back to the source.
      </p>

      <div className="card version-picker">
        <div className="field-row">
          <label>Entity type</label>
          <select
            value={entityType}
            onChange={(e) => setEntityType(e.target.value)}
          >
            {ENTITY_PRESETS.map((p) => (
              <option key={p.type} value={p.type}>{p.label}</option>
            ))}
            <option value="workflow_run">Workflow run</option>
          </select>
        </div>
        <div className="field-row">
          <label>Entity id</label>
          <input
            type="text"
            placeholder={ENTITY_PRESETS.find((p) => p.type === entityType)?.hint || 'id'}
            value={entityId}
            onChange={(e) => setEntityId(e.target.value)}
          />
        </div>
        <button className="primary" onClick={load} disabled={!canLoad || loading}>
          {loading ? 'Loading…' : 'Load versions'}
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      {versions.length === 0 && !loading && !error && canLoad && (
        <div className="alert subtle">No versions yet for this entity.</div>
      )}

      {versions.length > 0 && (
        <div className="card">
          <h3>
            {entityType}/{entityId} — {versions.length} version
            {versions.length === 1 ? '' : 's'}
          </h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Version</th>
                <th>When</th>
                <th>Source</th>
                <th>By</th>
                <th>Change</th>
                <th>Restored from</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {versions.map((v) => (
                <tr key={v.id}>
                  <td>
                    <span className="badge subtle">v{v.version_number}</span>
                  </td>
                  <td>{formatDateTime(v.created_at)}</td>
                  <td>
                    <span className={`badge ${_sourceBadge(v.source_action)}`}>
                      {v.source_action}
                    </span>
                  </td>
                  <td>{v.created_by}</td>
                  <td className="change-summary">{v.change_summary || '—'}</td>
                  <td>
                    {v.restored_from_version
                      ? `v${v.restored_from_version}`
                      : '—'}
                  </td>
                  <td>
                    {v.source_action !== 'restore' && (
                      <button
                        className="link"
                        onClick={() => setPendingRestore(v)}
                      >
                        Restore this version
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pendingRestore && (
        <RestoreConfirmModal
          entityType={entityType}
          entityId={entityId}
          version={pendingRestore}
          onClose={() => setPendingRestore(null)}
          onConfirm={(reason) =>
            onRestore(pendingRestore.version_number, reason)
          }
        />
      )}
    </div>
  )
}

function _sourceBadge(action) {
  if (!action) return 'subtle'
  if (action.startsWith('user')) return 'ok'
  if (action.startsWith('parser')) return 'subtle'
  if (action === 'restore') return 'warning'
  if (action.startsWith('workflow')) return 'info'
  return 'subtle'
}
