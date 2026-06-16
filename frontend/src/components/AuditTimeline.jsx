import { useEffect, useState } from 'react'
import { api, formatDateTime } from '../api.js'

const ACTION_LABELS = {
  upload: 'Uploaded',
  extraction: 'Extracted',
  edit: 'Edited',
  approve: 'Approved',
  reject: 'Rejected',
  mark_duplicate: 'Marked as duplicate',
  organize_file: 'Moved file to organized folder',
  organize_file_skipped: 'Organize skipped',
  'export.excel': 'Exported to Excel',
  mark_exported: 'Marked as exported',
  'settings.folder_rules.update': 'Updated folder rules'
}

function formatValue(v) {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

function DiffView({ before, after }) {
  if (!before || !after) {
    return <span className="subtle">No diff available</span>
  }
  const keys = new Set([...Object.keys(before || {}), ...Object.keys(after || {})])
  const rows = []
  for (const k of keys) {
    const b = before ? before[k] : undefined
    const a = after ? after[k] : undefined
    if (b !== a) {
      rows.push(
        <tr key={k}>
          <td className="mono">{k}</td>
          <td className="subtle">{formatValue(b)}</td>
          <td>→</td>
          <td>{formatValue(a)}</td>
        </tr>
      )
    }
  }
  if (!rows.length) {
    return <span className="subtle">No field changes</span>
  }
  return (
    <table className="diff-table" style={{ marginTop: 6 }}>
      <thead><tr><th>Field</th><th>From</th><th></th><th>To</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  )
}

export default function AuditTimeline({ invoiceId, refreshKey = 0 }) {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState(new Set())

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError('')
    api.invoiceAuditTimeline(invoiceId, 200)
      .then((data) => { if (alive) setEntries(data || []) })
      .catch((err) => { if (alive) setError(err.message || 'Failed to load audit.') })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [invoiceId, refreshKey])

  const toggle = (id) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (loading) return <div className="subtle">Loading audit trail…</div>
  if (error) return <div className="alert error">{error}</div>
  if (!entries.length) return <div className="muted">No audit entries for this invoice yet.</div>

  return (
    <ol className="audit-timeline">
      {entries.map((e) => {
        const hasDiff = !!(e.before_data_json || e.after_data_json)
        const isOpen = expanded.has(e.id)
        return (
          <li key={e.id} className={`audit-item ${isOpen ? 'open' : ''}`}>
            <div className="audit-row" onClick={() => hasDiff && toggle(e.id)} style={{ cursor: hasDiff ? 'pointer' : 'default' }}>
              <div>
                <div className="audit-action">{ACTION_LABELS[e.action] || e.action}</div>
                <div className="subtle">
                  {formatDateTime(e.timestamp)} · by <strong>{e.actor}</strong>
                </div>
                {e.details && <div className="subtle">{e.details}</div>}
              </div>
              {hasDiff && (
                <button type="button" className="secondary" onClick={(ev) => { ev.stopPropagation(); toggle(e.id) }} style={{ padding: '4px 10px' }}>
                  {isOpen ? 'Hide diff' : 'View diff'}
                </button>
              )}
            </div>
            {isOpen && (
              <div className="audit-diff">
                <DiffView before={e.before_data_json} after={e.after_data_json} />
              </div>
            )}
          </li>
        )
      })}
    </ol>
  )
}
