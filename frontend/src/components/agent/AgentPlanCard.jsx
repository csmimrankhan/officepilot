export default function AgentPlanCard({ plan }) {
  if (!plan || !plan.plan) return null

  const p = plan.plan
  const riskLabel = p.risk_level || 'unknown'
  const riskColor = riskLabel === 'low' ? '#a6e3a1' : riskLabel === 'medium' ? '#f9e2af' : riskLabel === 'high' || riskLabel === 'blocked' ? '#f38ba8' : '#6c7086'
  const steps = p.steps || []
  const isBlocked = !!p.blocked_reason
  const needsClarification = !!p.clarification_needed

  return (
    <div className="card" style={{ padding: '12px', background: '#181825', borderRadius: '12px' }}>
      <style>{`
        .agent-plan-title { font-size: 14px; font-weight: 600; color: #cdd6f4; margin: 0 0 4px; }
        .agent-plan-summary { font-size: 12px; color: #a6adc8; margin: 0 0 8px; }
        .agent-plan-risk { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; }
        .agent-plan-step { padding: 6px 8px; background: #1e1e2e; border-radius: 6px; margin-bottom: 4px; font-size: 12px; color: #bac2de; display: flex; align-items: center; gap: 8px; }
        .agent-plan-step-order { width: 20px; height: 20px; border-radius: 50%; background: #45475a; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 600; color: #cdd6f4; flex-shrink: 0; }
        .agent-plan-step.info { color: #89b4fa; font-size: 11px; margin-top: 4px; }
        .agent-plan-blocked { color: #f38ba8; font-size: 12px; padding: 8px; background: #1e1e2e; border-radius: 6px; }
        .agent-plan-clarification { color: #f9e2af; font-size: 12px; padding: 8px; background: #1e1e2e; border-radius: 6px; }
        .agent-plan-badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 500; margin-left: 4px; }
        .agent-plan-badge.ru { background: #45475a; color: #89b4fa; }
        .agent-plan-badge.wf { background: #45475a; color: #a6e3a1; }
      `}</style>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h4 className="agent-plan-title">{p.task_title || 'Task Plan'}</h4>
        <span className="agent-plan-risk" style={{ background: riskColor + '22', color: riskColor }}>
          {riskLabel}
        </span>
      </div>

      <p className="agent-plan-summary">{p.task_summary || ''}</p>

      <div style={{ marginBottom: '8px' }}>
        {plan.detected_language && plan.detected_language !== 'en' && (
          <span className="agent-plan-badge ru">Language: {plan.detected_language}</span>
        )}
        {p.can_save_workflow && <span className="agent-plan-badge wf">Saves as workflow</span>}
        {plan.matched_workflow_name && <span className="agent-plan-badge wf">Matched: {plan.matched_workflow_name}</span>}
      </div>

      {isBlocked && (
        <div className="agent-plan-blocked">⛔ {p.blocked_reason}</div>
      )}

      {needsClarification && !isBlocked && (
        <div className="agent-plan-clarification">❓ {p.clarification_question || 'Clarification needed.'}</div>
      )}

      {!isBlocked && !needsClarification && steps.length > 0 && (
        <div>
          <div style={{ fontSize: '12px', color: '#6c7086', marginBottom: '6px' }}>
            {steps.length} step{steps.length !== 1 ? 's' : ''}
          </div>
          {steps.map((step) => (
            <div key={step.step_order} className="agent-plan-step" title={step.instruction || ''}>
              <span className="agent-plan-step-order">{step.step_order}</span>
              <div style={{ flex: 1 }}>
                <div><strong>{step.step_type}</strong> {step.target ? `→ ${step.target}` : ''}</div>
                <div className="agent-plan-step info">{step.instruction || step.expected_result || ''}</div>
              </div>
              {step.risk_level && step.risk_level !== 'low' && (
                <span style={{ fontSize: '10px', color: step.risk_level === 'medium' ? '#f9e2af' : '#f38ba8' }}>
                  {step.risk_level}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {!isBlocked && !needsClarification && steps.length === 0 && (
        <p style={{ fontSize: '12px', color: '#6c7086' }}>No steps to display.</p>
      )}
    </div>
  )
}
