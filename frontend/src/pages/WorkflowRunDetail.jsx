import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  api,
  formatDateTime,
  WORKFLOW_STATUS_LABELS,
  WORKFLOW_APPROVAL_STATUS_LABELS
} from '../api.js'
import WorkflowTimeline from '../components/WorkflowTimeline.jsx'
import ApprovalModal from '../components/ApprovalModal.jsx'

export default function WorkflowRunDetail() {
  const { id } = useParams()
  const runId = Number(id)
  const [run, setRun] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [actionBusy, setActionBusy] = useState(false)
  const [showApproval, setShowApproval] = useState(false)
  const [retryNode, setRetryNode] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.getWorkflowRun(runId)
      setRun(data)
      setRetryNode(data.current_node || '')
    } catch (err) {
      setError(err.message || 'Failed to load run.')
    } finally {
      setLoading(false)
    }
  }, [runId])

  useEffect(() => { load() }, [load])

  const handleApprove = async (note) => {
    setActionBusy(true)
    setActionError('')
    try {
      await api.approveWorkflowRun(runId, 'user', note)
      setShowApproval(false)
      await load()
    } catch (err) {
      setActionError(err.message || 'Failed to approve.')
    } finally {
      setActionBusy(false)
    }
  }

  const handleReject = async (note) => {
    setActionBusy(true)
    setActionError('')
    try {
      await api.rejectWorkflowRun(runId, 'user', note)
      setShowApproval(false)
      await load()
    } catch (err) {
      setActionError(err.message || 'Failed to reject.')
    } finally {
      setActionBusy(false)
    }
  }

  const handleCancel = async () => {
    if (!confirm('Cancel this workflow run?')) return
    setActionBusy(true)
    setActionError('')
    try {
      await api.cancelWorkflowRun(runId, 'user', 'cancelled from UI')
      await load()
    } catch (err) {
      setActionError(err.message || 'Failed to cancel.')
    } finally {
      setActionBusy(false)
    }
  }

  const handleRetry = async () => {
    setActionBusy(true)
    setActionError('')
    try {
      await api.retryWorkflowRun(runId, 'user', retryNode || null)
      await load()
    } catch (err) {
      setActionError(err.message || 'Failed to retry.')
    } finally {
      setActionBusy(false)
    }
  }

  if (loading && !run) return <div className="subtle">Loading…</div>
  if (error) return <div className="alert error">{error}</div>
  if (!run) return <div className="muted">Run not found.</div>

  const canApprove = run.status === 'awaiting_approval' && run.pending_approval
  const canCancel = ['pending', 'running', 'awaiting_approval'].includes(run.status)
  const canRetry = ['failed', 'cancelled', 'rejected'].includes(run.status)
  const isTerminal = ['completed', 'failed', 'cancelled', 'rejected'].includes(run.status)

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Workflow Run #{run.id}</h2>
          <span className="subtle">
            <code className="mono">{run.workflow_name}</code>
            {' · '}
            started {formatDateTime(run.started_at) || '—'}
          </span>
        </div>
        <Link to="/workflows" className="secondary" style={{ padding: '6px 12px' }}>
          ← Back to runs
        </Link>
      </div>

      {actionError && <div className="alert error">{actionError}</div>}

      <div className="run-summary">
        <div>
          <div className="subtle">Status</div>
          <div>
            <span className={`badge ${run.status}`}>
              {WORKFLOW_STATUS_LABELS[run.status] || run.status}
            </span>
          </div>
        </div>
        <div>
          <div className="subtle">Current node</div>
          <code className="mono">{run.current_node || '—'}</code>
        </div>
        <div>
          <div className="subtle">Actor</div>
          <div>{run.actor || '—'}</div>
        </div>
        <div>
          <div className="subtle">Completed</div>
          <div>{formatDateTime(run.completed_at) || '—'}</div>
        </div>
      </div>

      {run.error_message && (
        <div className="alert error">
          <strong>Error:</strong> {run.error_message}
        </div>
      )}

      <div className="toolbar" style={{ flexWrap: 'wrap' }}>
        {canApprove && (
          <button
            type="button"
            className="primary"
            onClick={() => setShowApproval(true)}
            disabled={actionBusy}
          >
            Review &amp; approve
          </button>
        )}
        {canCancel && (
          <button
            type="button"
            className="danger"
            onClick={handleCancel}
            disabled={actionBusy}
          >
            Cancel run
          </button>
        )}
        {canRetry && (
          <>
            <label className="subtle">
              From node:&nbsp;
              <input
                type="text"
                value={retryNode}
                onChange={(e) => setRetryNode(e.target.value)}
                placeholder={run.current_node || 'auto'}
                style={{ width: 200 }}
              />
            </label>
            <button
              type="button"
              className="primary"
              onClick={handleRetry}
              disabled={actionBusy}
            >
              Retry
            </button>
          </>
        )}
        <button type="button" className="secondary" onClick={load} disabled={actionBusy}>
          Refresh
        </button>
      </div>

      <h3>Node timeline</h3>
      <WorkflowTimeline logs={run.logs || []} />

      <h3>Approvals</h3>
      {(!run.approvals || run.approvals.length === 0) ? (
        <div className="muted">No approval checkpoints for this run.</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Node</th>
              <th>Status</th>
              <th>Message</th>
              <th>Decided by</th>
              <th>At</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {run.approvals.map((a) => (
              <tr key={a.id}>
                <td><code className="mono">{a.node_name}</code></td>
                <td>
                  <span className={`badge ${a.status}`}>
                    {WORKFLOW_APPROVAL_STATUS_LABELS[a.status] || a.status}
                  </span>
                </td>
                <td>{a.message || '—'}</td>
                <td>{a.approved_by || '—'}</td>
                <td className="subtle">{formatDateTime(a.approved_at) || '—'}</td>
                <td>{a.decision_note || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Final state</h3>
      <pre className="json-block">
        {JSON.stringify(run.state || {}, null, 2)}
      </pre>

      <h3>Input</h3>
      <pre className="json-block">
        {JSON.stringify(run.input || {}, null, 2)}
      </pre>

      {!isTerminal && (
        <p className="subtle" style={{ marginTop: 16 }}>
          Run is still in progress. The list will refresh on demand.
        </p>
      )}

      {showApproval && run.pending_approval && (
        <ApprovalModal
          approval={run.pending_approval}
          onApprove={handleApprove}
          onReject={handleReject}
          onClose={() => setShowApproval(false)}
          busy={actionBusy}
        />
      )}
    </div>
  )
}
