export default function MetricCard({ label, value, subtitle, icon, color, onClick }) {
  return (
    <div className={`metric-card ${onClick ? 'metric-card--clickable' : ''}`} onClick={onClick}
      style={color ? { borderLeftColor: color } : {}}>
      {icon && <div className="metric-icon">{icon}</div>}
      <div className="metric-value">{value ?? '—'}</div>
      <div className="metric-label">{label}</div>
      {subtitle && <div className="metric-subtitle">{subtitle}</div>}
    </div>
  )
}
