export default function AdminMetricCard({ label, value, subtitle, icon, color, trend, onClick }) {
  return (
    <div className={`admin-metric-card ${onClick ? 'admin-metric-card--clickable' : ''}`} onClick={onClick}
      style={color ? { borderLeftColor: color } : {}}>
      {icon && <div className="admin-metric-icon">{icon}</div>}
      <div className="admin-metric-value">{value ?? '—'}</div>
      <div className="admin-metric-label">{label}</div>
      {subtitle && <div className="admin-metric-subtitle">{subtitle}</div>}
      {trend && <div className="admin-metric-trend">{trend}</div>}
    </div>
  )
}
