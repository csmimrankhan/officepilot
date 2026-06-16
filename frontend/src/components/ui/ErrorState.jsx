export default function ErrorState({ message, onRetry, details }) {
  return (
    <div className="error-state">
      <div className="error-state-icon">⚠️</div>
      <h3>Something went wrong</h3>
      <p>{message || 'An unexpected error occurred.'}</p>
      {details && <pre className="error-detail">{details}</pre>}
      {onRetry && <button className="btn btn--primary" onClick={onRetry}>Retry</button>}
    </div>
  )
}
