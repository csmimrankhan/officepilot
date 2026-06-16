export default function SkillDraftReview({ draft, onSaveSkill, onRejectDraft, loading }) {
  if (!draft) return null

  const steps = draft.steps || []
  const safetyRules = draft.safety_rules || {}
  const triggerPhrases = draft.trigger_phrases || []

  return (
    <div className="skill-draft-review" style={{ padding: 14 }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>
        Skill Draft Review
      </div>
      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 12 }}>
        {draft.description}
      </div>

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>
          Skill Name
        </label>
        <div style={{ fontSize: 14, fontWeight: 500, color: '#cdd6f4' }}>{draft.name}</div>
      </div>

      {triggerPhrases.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>
            Trigger Phrases
          </label>
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {triggerPhrases.map((p, i) => (
              <span key={i} style={{
                background: '#374151', color: '#93c5fd', fontSize: 11,
                padding: '2px 8px', borderRadius: 12,
              }}>
                {p}
              </span>
            ))}
          </div>
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>
          Steps ({steps.length})
        </label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {steps.map((s, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 8px', background: '#1e1e2e', borderRadius: 6, fontSize: 12,
              borderLeft: `3px solid ${s.risk_level === 'high' ? '#ef4444' : s.risk_level === 'medium' ? '#eab308' : '#22c55e'}`,
            }}>
              <span style={{ color: '#6b7280', minWidth: 20 }}>#{s.step_order || i + 1}</span>
              <span style={{ color: '#a78bfa', minWidth: 80 }}>{s.step_type}</span>
              <span style={{ color: '#cdd6f4', flex: 1 }}>{s.target || s.instruction || ''}</span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, color: '#6b7280', display: 'block', marginBottom: 4 }}>
          Safety Rules
        </label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {safetyRules.requires_dry_run && (
            <span style={{ background: '#1e3a5f', color: '#60a5fa', fontSize: 11, padding: '2px 8px', borderRadius: 4 }}>
              Dry-run required
            </span>
          )}
          {safetyRules.approval_required && (
            <span style={{ background: '#5f1e1e', color: '#f87171', fontSize: 11, padding: '2px 8px', borderRadius: 4 }}>
              Approval required
            </span>
          )}
          <span style={{
            background: '#374151', color: '#cdd6f4', fontSize: 11, padding: '2px 8px', borderRadius: 4,
          }}>
            Max risk: {safetyRules.max_risk_level || 'low'}
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={onSaveSkill}
          disabled={loading}
          style={{
            flex: 1, padding: '10px 16px',
            background: loading ? '#9ca3af' : '#7c3aed', color: '#fff',
            border: 'none', borderRadius: 8, cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 600, fontSize: 14,
          }}
        >
          {loading ? 'Saving...' : 'Save Skill'}
        </button>
        {onRejectDraft && (
          <button
            onClick={onRejectDraft}
            disabled={loading}
            style={{
              padding: '10px 16px', background: '#f3f4f6', color: '#666',
              border: '1px solid #d1d5db', borderRadius: 8, cursor: 'pointer', fontSize: 14,
            }}
          >
            Reject
          </button>
        )}
      </div>
    </div>
  )
}
