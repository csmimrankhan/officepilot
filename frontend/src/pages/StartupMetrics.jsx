import { useState, useEffect } from 'react'

const NOTES = {
  process_start: 'The moment the Python process was launched and the interpreter began execution.',
  lifespan_started: 'FastAPI\'s lifespan handler (async startup/shutdown context) began running — database engine, background tasks, and service singletons are being initialised.',
  backend_ready: 'All startup hooks have completed successfully. The application is ready to accept incoming HTTP requests.',
}

function MetricCard({ label, value, unit }) {
  return (
    <div style={styles.card}>
      <div style={styles.cardLabel}>{label}</div>
      <div style={styles.cardValue}>
        {value}<span style={styles.cardUnit}>{unit}</span>
      </div>
    </div>
  )
}

function Table({ marks }) {
  if (!marks || marks.length === 0) return null
  return (
    <table style={styles.table}>
      <thead>
        <tr>
          <th style={styles.th}>Mark Name</th>
          <th style={styles.th}>Timestamp (relative)</th>
          <th style={styles.th}>Elapsed (seconds)</th>
        </tr>
      </thead>
      <tbody>
        {marks.map((m, i) => (
          <tr key={i}>
            <td style={styles.td}><code style={styles.code}>{m.name}</code></td>
            <td style={styles.td}>{m.relative_timestamp ?? '-'}</td>
            <td style={styles.td}>{m.elapsed_seconds != null ? m.elapsed_seconds.toFixed(3) : '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function NotesSection({ marks }) {
  if (!marks || marks.length === 0) return null
  const relevant = marks.filter(m => NOTES[m.name])
  if (relevant.length === 0) return null
  return (
    <div style={styles.notes}>
      <h3 style={styles.sectionTitle}>What Each Mark Means</h3>
      {relevant.map((m, i) => (
        <div key={i} style={styles.noteItem}>
          <strong><code style={styles.code}>{m.name}</code></strong>
          <p style={styles.noteText}>{NOTES[m.name]}</p>
        </div>
      ))}
    </div>
  )
}

export default function StartupMetrics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function loadMetrics() {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('http://127.0.0.1:8000/api/system/startup-metrics')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setData(await res.json())
    } catch (e) {
      setError('Failed to load: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadMetrics() }, [])

  const marks = data?.marks ?? []
  const totalTime = data?.total_startup_time_seconds ?? data?.total_elapsed_seconds ?? null

  return (
    <div style={styles.page}>
      <style>{`
        body { background: #f0f2f5; margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        @media (prefers-color-scheme: dark) {
          body { background: #1a1d23; }
        }
      `}</style>

      <h1 style={styles.title}>Startup Performance Metrics</h1>

      {loading && <p style={styles.status}>Loading startup metrics...</p>}

      {error && (
        <div style={styles.errorBox}>
          <p style={styles.errorText}>{error}</p>
          <button onClick={loadMetrics} style={styles.retryBtn}>Retry</button>
        </div>
      )}

      {!loading && !error && (!marks || marks.length === 0) && (
        <p style={styles.status}>No startup metrics available yet</p>
      )}

      {!loading && !error && marks.length > 0 && (
        <>
          {totalTime != null && (
            <MetricCard label="Total Startup Time" value={totalTime.toFixed(2)} unit="s" />
          )}
          <Table marks={marks} />
          <NotesSection marks={marks} />
        </>
      )}
    </div>
  )
}

const styles = {
  page: {
    maxWidth: 900,
    margin: '0 auto',
    padding: '32px 24px',
  },
  title: {
    fontSize: 28,
    fontWeight: 600,
    color: '#1a202c',
    marginBottom: 28,
    borderBottom: '2px solid #e2e8f0',
    paddingBottom: 12,
  },
  status: {
    color: '#718096',
    fontSize: 15,
    textAlign: 'center',
    padding: 40,
  },
  errorBox: {
    background: '#fff5f5',
    border: '1px solid #fed7d7',
    borderRadius: 8,
    padding: 20,
    textAlign: 'center',
  },
  errorText: {
    color: '#e53e3e',
    fontSize: 14,
    marginBottom: 12,
  },
  retryBtn: {
    background: '#3182ce',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    padding: '8px 20px',
    fontSize: 14,
    cursor: 'pointer',
  },
  card: {
    background: 'linear-gradient(135deg, #2b6cb0, #2c5282)',
    borderRadius: 12,
    padding: '28px 32px',
    marginBottom: 28,
    color: '#fff',
    textAlign: 'center',
    boxShadow: '0 4px 14px rgba(43,108,176,0.25)',
  },
  cardLabel: {
    fontSize: 13,
    fontWeight: 500,
    textTransform: 'uppercase',
    letterSpacing: 1,
    opacity: 0.85,
    marginBottom: 6,
  },
  cardValue: {
    fontSize: 48,
    fontWeight: 700,
    lineHeight: 1.1,
  },
  cardUnit: {
    fontSize: 20,
    fontWeight: 400,
    opacity: 0.8,
    marginLeft: 6,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    background: '#fff',
    borderRadius: 10,
    overflow: 'hidden',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    marginBottom: 28,
  },
  th: {
    background: '#edf2f7',
    color: '#2d3748',
    fontSize: 13,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    padding: '12px 16px',
    textAlign: 'left',
    borderBottom: '2px solid #e2e8f0',
  },
  td: {
    padding: '10px 16px',
    fontSize: 14,
    color: '#2d3748',
    borderBottom: '1px solid #f0f0f0',
    fontFamily: 'SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace',
  },
  code: {
    background: '#edf2f7',
    padding: '2px 6px',
    borderRadius: 4,
    fontSize: 13,
    color: '#2b6cb0',
  },
  notes: {
    background: '#fff',
    borderRadius: 10,
    padding: '20px 24px',
    boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: '#2d3748',
    marginTop: 0,
    marginBottom: 16,
    paddingBottom: 8,
    borderBottom: '1px solid #e2e8f0',
  },
  noteItem: {
    marginBottom: 14,
  },
  noteText: {
    margin: '4px 0 0',
    fontSize: 14,
    color: '#4a5568',
    lineHeight: 1.6,
  },
}
