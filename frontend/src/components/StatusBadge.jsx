import { STATUS_LABELS } from '../api.js'

export default function StatusBadge({ status }) {
  const cls = `badge ${status || 'pending'}`
  return <span className={cls}>{STATUS_LABELS[status] || status || '—'}</span>
}
