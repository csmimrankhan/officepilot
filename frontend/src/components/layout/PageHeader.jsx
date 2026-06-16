export default function PageHeader({ title, subtitle, actions, status, helpText }) {
  return (
    <div className="page-header">
      <div className="page-header-info">
        <h2>{title}</h2>
        {subtitle && <p className="page-header-subtitle">{subtitle}</p>}
        {helpText && <p className="page-header-help">{helpText}</p>}
      </div>
      <div className="page-header-actions">
        {status && <div className="page-header-status">{status}</div>}
        {actions}
      </div>
    </div>
  )
}
