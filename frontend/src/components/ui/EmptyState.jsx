export default function EmptyState({ icon = '📋', title, description, action, onAction, actionLabel }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <h3>{title || 'Nothing here yet'}</h3>
      {description && <p className="subtle">{description}</p>}
      {action && onAction && (
        <button className="btn btn--primary" onClick={onAction}>{actionLabel || 'Get Started'}</button>
      )}
    </div>
  )
}
