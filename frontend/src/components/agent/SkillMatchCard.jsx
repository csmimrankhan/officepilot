import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api.js'

export default function SkillMatchCard({ matchedSkill, voiceReply, onDryRun, onCreateNewPlan, onCancel }) {
  const navigate = useNavigate()
  const [dryRunResult, setDryRunResult] = useState(null)
  const [dryRunning, setDryRunning] = useState(false)
  const [dryRunError, setDryRunError] = useState(null)
  const [executing, setExecuting] = useState(false)
  const [executeError, setExecuteError] = useState(null)

  if (!matchedSkill) return null

  const skill = matchedSkill
  const steps = skill.steps || []
  const confidence = skill.confidence || 0
  const isStrong = confidence >= 0.85
  const isPossible = confidence >= 0.6 && confidence < 0.85
  const matchLabel = isStrong ? 'Strong Match' : isPossible ? 'Possible Match' : 'Weak Match'
  const riskLabel = skill.safety_rules?.max_risk_level || 'low'
  const needsApproval = skill.approval_required !== false

  const handleDryRun = async () => {
    setDryRunning(true)
    setDryRunError(null)
    setDryRunResult(null)
    try {
      const result = await api.dryRunSkill(skill.skill_id)
      setDryRunResult(result)
      if (onDryRun) onDryRun(result)
    } catch (err) {
      setDryRunError(err.message)
    }
    setDryRunning(false)
  }

  const handleExecute = async () => {
    setExecuting(true)
    setExecuteError(null)
    try {
      const result = await api.executeSkill(skill.skill_id, {})
      if (result.ok) {
        setDryRunResult({ ...dryRunResult, executed: true, run_id: result.run_id })
      } else {
        setExecuteError(result.error || 'Execution failed')
      }
    } catch (err) {
      setExecuteError(err.message)
    }
    setExecuting(false)
  }

  const handleEdit = () => {
    navigate(`/app/workflow-memory/skills?skillId=${skill.skill_id}`)
  }

  return (
    <div className="skill-match-card">
      <div className="skill-match-header">
        <div className="skill-match-name-row">
          <span className="skill-match-icon">⚡</span>
          <span className="skill-match-name">{skill.name}</span>
        </div>
        <div className="skill-match-badges">
          <span className={`badge badge--${isStrong ? 'success' : 'warning'}`}>
            {matchLabel} ({Math.round(confidence * 100)}%)
          </span>
          <span className={`badge badge--${riskLabel === 'high' ? 'danger' : riskLabel === 'medium' ? 'warning' : 'success'}`}>
            {riskLabel}
          </span>
          {needsApproval && <span className="badge badge--warning">Approval Required</span>}
        </div>
      </div>

      {skill.matched_trigger && (
        <div className="skill-match-trigger">
          Matched: "<em>{skill.matched_trigger}</em>"
        </div>
      )}

      {skill.description && (
        <p className="skill-match-desc">{skill.description}</p>
      )}

      {voiceReply && (
        <div className="skill-match-voice-reply">{voiceReply}</div>
      )}

      {/* Steps preview */}
      <div className="skill-match-steps">
        <div className="skill-match-steps-title">{steps.length} step{steps.length !== 1 ? 's' : ''}</div>
        {steps.map((step, i) => (
          <div key={i} className="skill-match-step">
            <span className="skill-match-step-num">{step.step_order || (i + 1)}</span>
            <div className="skill-match-step-body">
              <span className={`skill-match-step-type skill-match-step-type--${step.risk_level === 'high' ? 'high' : step.risk_level === 'medium' ? 'medium' : 'low'}`}>
                {step.step_type || step.tool || 'step'}
              </span>
              {step.target && <span className="skill-match-step-target">→ {step.target}</span>}
              <div className="skill-match-step-instruction">{step.instruction || step.expected_result || ''}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Dry-run result */}
      {dryRunResult && !dryRunResult.executed && (
        <div className="alert success" style={{ marginTop: 8 }}>
          ✅ Dry-run completed. {steps.length} steps verified.
        </div>
      )}
      {dryRunError && (
        <div className="alert error" style={{ marginTop: 8 }}>❌ {dryRunError}</div>
      )}
      {executeError && (
        <div className="alert error" style={{ marginTop: 8 }}>❌ {executeError}</div>
      )}
      {dryRunResult?.executed && (
        <div className="alert success" style={{ marginTop: 8 }}>
          ✅ Skill executed successfully (run #{dryRunResult.run_id}).
        </div>
      )}

      {/* Buttons */}
      <div className="skill-match-actions">
        {!dryRunResult && (
          <button className="btn btn--primary btn--sm" onClick={handleDryRun} disabled={dryRunning}>
            {dryRunning ? 'Dry-Running...' : 'Dry-run Skill'}
          </button>
        )}
        {dryRunResult && !dryRunResult.executed && (
          <button className="btn btn--warning btn--sm" onClick={handleExecute} disabled={executing}>
            {executing ? 'Executing...' : 'Approve & Execute'}
          </button>
        )}
        <button className="btn btn--secondary btn--sm" onClick={handleEdit}>
          Edit Skill
        </button>
        <button className="btn btn--secondary btn--sm" onClick={onCreateNewPlan}>
          Create New Plan Instead
        </button>
        <button className="btn btn--danger btn--sm" onClick={onCancel}>
          Cancel
        </button>
      </div>

      <style>{`
        .skill-match-card { padding: 12px; border: 1px solid var(--border, #e2e8f0); border-radius: 12px; background: var(--bg-card, #fff); }
        .skill-match-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
        .skill-match-name-row { display: flex; align-items: center; gap: 6px; }
        .skill-match-icon { font-size: 1.2rem; }
        .skill-match-name { font-weight: 600; font-size: 1rem; }
        .skill-match-badges { display: flex; gap: 4px; flex-wrap: wrap; }
        .skill-match-trigger { font-size: 0.85rem; color: var(--text-muted, #64748b); margin-bottom: 4px; }
        .skill-match-desc { font-size: 0.88rem; color: var(--text-secondary, #475569); margin: 4px 0 8px; }
        .skill-match-voice-reply { background: #f0f4f8; border-radius: 8px; padding: 8px 12px; margin: 8px 0; border-left: 3px solid var(--primary, #2563eb); font-size: 0.85rem; }
        .skill-match-steps { margin: 8px 0; }
        .skill-match-steps-title { font-size: 0.8rem; font-weight: 600; color: var(--text-muted, #64748b); margin-bottom: 6px; }
        .skill-match-step { display: flex; gap: 8px; align-items: flex-start; padding: 4px 0; }
        .skill-match-step-num { width: 20px; height: 20px; border-radius: 50%; background: var(--primary, #2563eb); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; flex-shrink: 0; }
        .skill-match-step-body { flex: 1; }
        .skill-match-step-type { font-size: 10px; padding: 0 6px; border-radius: 8px; font-weight: 600; text-transform: uppercase; }
        .skill-match-step-type--low { background: #dbeafe; color: #1d4ed8; }
        .skill-match-step-type--medium { background: #fef3c7; color: #b45309; }
        .skill-match-step-type--high { background: #fee2e2; color: #dc2626; }
        .skill-match-step-target { font-size: 11px; color: var(--text-muted, #64748b); margin-left: 4px; }
        .skill-match-step-instruction { font-size: 0.82rem; color: var(--text-secondary, #475569); }
        .skill-match-actions { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px; }
      `}</style>
    </div>
  )
}