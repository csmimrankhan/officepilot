export function CardSkeleton({ lines = 3 }) {
  return (
    <div className="card skeleton-card" style={{ padding: 20 }}>
      <div className="skeleton-line skeleton-line--title" />
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="skeleton-line" style={{ width: `${60 + Math.random() * 30}%` }} />
      ))}
    </div>
  )
}

export function TableSkeleton({ rows = 5 }) {
  return (
    <div className="card skeleton-card" style={{ padding: 20 }}>
      <div className="skeleton-line skeleton-line--title" style={{ width: '40%' }} />
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton-line" style={{ width: `${70 + Math.random() * 20}%` }} />
      ))}
    </div>
  )
}

export function PageSkeleton() {
  return (
    <div style={{ padding: 24 }}>
      <div className="skeleton-line skeleton-line--title" style={{ width: '30%', height: 28, marginBottom: 20 }} />
      <CardSkeleton lines={4} />
    </div>
  )
}
