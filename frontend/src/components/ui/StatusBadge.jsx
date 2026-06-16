export default function StatusBadge({ status, size }) {
  const colors = {
    imported: '#6366f1',
    extracting: '#f59e0b',
    needs_review: '#f97316',
    ready_for_approval: '#2563eb',
    approved: '#16a34a',
    rejected: '#dc2626',
    duplicate: '#8b5cf6',
    exported: '#059669',
    pending: '#f59e0b',
    active: '#16a34a',
    inactive: '#64748b',
    blocked: '#dc2626',
    green: '#16a34a',
    yellow: '#d97706',
    red: '#dc2626',
  }
  const label = status ? status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'Unknown'
  return (
    <span className={`status-badge ${size === 'sm' ? 'status-badge--sm' : ''}`}
      style={{ backgroundColor: colors[status] || '#64748b' }}>
      {label}
    </span>
  )
}
