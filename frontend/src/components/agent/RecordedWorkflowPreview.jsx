const RISK_COLORS = { low: '#22c55e', medium: '#eab308', high: '#ef4444' }

export default function RecordedWorkflowPreview({ events, onDeleteEvent, onConvertToSkill, loading }) {
  if (!events || events.length === 0) {
    return (
      <div style={{ padding: 16, color: '#888', fontSize: 13, fontStyle: 'italic' }}>
        No events recorded yet.
      </div>
    )
  }

  return (
    <div className="recorded-workflow-preview" style={{ padding: 14 }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
        Recorded Steps ({events.length})
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {events.map((ev, i) => (
          <div
            key={ev.id || i}
            style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '8px 10px', background: '#1e1e2e', borderRadius: 8,
              fontSize: 13, borderLeft: `3px solid ${RISK_COLORS[ev.risk_level] || '#6b7280'}`,
            }}
          >
            <span style={{ color: '#6b7280', minWidth: 24, fontSize: 12 }}>#{ev.event_order || i + 1}</span>
            <span style={{ color: '#a78bfa', minWidth: 100, fontSize: 12 }}>{ev.event_type}</span>
            <span style={{ color: '#cdd6f4', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {ev.label || ev.app_name || ev.event_type}
            </span>
            {ev.was_redacted && (
              <span style={{
                background: '#fef2f2', color: '#dc2626', fontSize: 11,
                padding: '2px 6px', borderRadius: 4,
              }}>
                [REDACTED]
              </span>
            )}
            {ev.text_value_redacted && !ev.was_redacted && (
              <span style={{ color: '#6b7280', fontSize: 12, maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                &quot;{ev.text_value_redacted.slice(0, 20)}&quot;
              </span>
            )}
            {ev.file_path && (
              <span style={{ color: '#22c55e', fontSize: 11 }}>file</span>
            )}
            {ev.browser_url && (
              <span style={{ color: '#60a5fa', fontSize: 11 }}>url</span>
            )}
            <div style={{ display: 'flex', gap: 4, marginLeft: 'auto' }}>
              <span style={{
                fontSize: 10, padding: '2px 6px', borderRadius: 4,
                background: RISK_COLORS[ev.risk_level] + '22',
                color: RISK_COLORS[ev.risk_level],
              }}>
                {ev.risk_level}
              </span>
              {onDeleteEvent && (
                <button
                  onClick={() => onDeleteEvent(ev.id || i)}
                  style={{
                    background: 'none', border: 'none', color: '#ef4444',
                    cursor: 'pointer', fontSize: 14, padding: '0 4px',
                  }}
                  title="Remove step"
                >
                  x
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      {onConvertToSkill && (
        <button
          onClick={onConvertToSkill}
          disabled={loading}
          style={{
            marginTop: 16, width: '100%', padding: '10px 16px',
            background: loading ? '#9ca3af' : '#7c3aed', color: '#fff',
            border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 600, fontSize: 14,
          }}
        >
          {loading ? 'Converting...' : 'Convert to Skill'}
        </button>
      )}
    </div>
  )
}
