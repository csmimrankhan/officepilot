import { formatDateTime, WORKFLOW_LOG_STATUS_LABELS } from '../api.js'

const STATUS_BADGE = {
  ok: 'badge ok',
  awaiting_approval: 'badge awaiting_approval',
  skipped: 'badge skipped',
  failed: 'badge failed'
}

function formatValue(v) {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'object') return JSON.stringify(v, null, 2)
  return String(v)
}

export default function WorkflowTimeline({ logs = [] }) {
  if (!logs.length) {
    return <div className="muted">No node activity recorded yet.</div>
  }
  return (
    <ol className="audit-timeline workflow-timeline">
      {logs.map((l) => {
        const cls = STATUS_BADGE[l.status] || 'badge'
        return (
          <li key={l.id} className="audit-item">
            <div className="audit-row">
              <div>
                <div className="audit-action">
                  <code className="mono">{l.node_name}</code>
                </div>
                <div className="subtle">
                  {formatDateTime(l.created_at)}
                  {l.message ? ` · ${l.message}` : ''}
                </div>
                {l.data && Object.keys(l.data).length > 0 && (
                  <details style={{ marginTop: 4 }}>
                    <summary className="subtle" style={{ cursor: 'pointer' }}>
                      View node data
                    </summary>
                    <pre className="json-block">{formatValue(l.data)}</pre>
                  </details>
                )}
              </div>
              <span className={cls}>
                {WORKFLOW_LOG_STATUS_LABELS[l.status] || l.status}
              </span>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
