// Phase 10 — Workflow Versions browser. Lists prior versions of a
// workflow run and lets the user restore an earlier one (rewinds
// status, current_node, state, logs, and approvals).

import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, formatDateTime } from '../api.js'
import RestoreConfirmModal from '../components/RestoreConfirmModal.tsx'

export default function WorkflowVersions() {
  const { id: idParam } = useParams()
  const [runId, setRunId] = useState(idParam || '')
  const [versions, setVersions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(null)

  const load = async () => {
    if (!runId) return
    setLoading(true)
    setError('')
    try {
      const data = await api.listWorkflowVersions(Number(runId))
      setVersions(data || [])
    } catch (err) {
      setError(err.message || 'Failed to load workflow versions')
      setVersions([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (idParam) setRunId(idParam)
  }, [idParam])

  useEffect(() => {
    if (runId) load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId])

  const onRestore = async (versionNumber, reason) => {
    await api.restoreWorkflowVersion(Number(runId), versionNumber, {
      actor: 'user',
      reason,
    })
    setPending(null)
    await load()
  }

  return (
    <div className="page">
      <h2>Workflow Versions</h2>
      <p className="muted">
        Every workflow state transition (start, approve, reject,
        cancel, retry) is recorded. Restoring an earlier version
        rewinds the run status, current node, and the bundled log +
        approval history.
      </p>

      <div className="card version-picker">
        <div className="field-row">
          <label>Workflow run id</label>
          <input
            type="number"
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            placeholder="e.g. 12"
          />
        </div>
        <button className="primary" onClick={load} disabled={!runId || loading}>
          {loading ? 'Loading…' : 'Load versions'}
        </button>
      </div>

      {error && <div className="alert error">{error}</div>}

      {versions.length === 0 && runId && !loading && !error && (
        <div className="alert subtle">No versions for this run.</div>
      )}

      {versions.length > 0 && (
        <div className="card">
          <h3>
            Run #{runId} — {versions.length} version
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
                    <span className="badge subtle">{v.source_action}</span>
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
                        onClick={() => setPending(v)}
                      >
                        Restore
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pending && (
        <RestoreConfirmModal
          entityType="workflow_run"
          entityId={String(runId)}
          version={pending}
          onClose={() => setPending(null)}
          onConfirm={(reason) => onRestore(pending.version_number, reason)}
        />
      )}
    </div>
  )
}
