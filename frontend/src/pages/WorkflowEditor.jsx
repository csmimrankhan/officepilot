import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, formatDateTime } from '../api.js'

export default function WorkflowEditor() {
  const { id } = useParams()
  const [workflow, setWorkflow] = useState(null)
  const [steps, setSteps] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState('')

  const load = async () => {
    try {
      const [wf, st] = await Promise.all([
        api.getRecordedWorkflow(id),
        api.getRecordedWorkflowSteps(id),
      ])
      setWorkflow(wf)
      setSteps(st)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [id])

  const saveWorkflow = async () => {
    setBusy(true); setError(''); setSaved('')
    try {
      const updated = await api.updateRecordedWorkflow(id, {
        name: workflow.name,
        description: workflow.description,
        risk_level: workflow.risk_level,
        replay_mode_default: workflow.replay_mode_default,
      })
      setWorkflow(updated)
      setSaved('Workflow saved.')
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  const updateStep = async (stepId, payload) => {
    setBusy(true)
    try {
      const updated = await api.updateRecordedWorkflowStep(id, stepId, payload)
      setSteps((prev) => prev.map((s) => s.id === stepId ? updated : s))
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  const toggleStep = (step) => updateStep(step.id, { enabled: !step.enabled })
  const toggleApproval = (step) => updateStep(step.id, { requires_approval: !step.requires_approval })

  if (!workflow) return <div className="card">Loading workflow…</div>

  return (
    <div>
      <div className="page-header">
        <h2>Workflow Editor</h2>
        <Link to="/recording/workflows" className="subtle">← Back to workflows</Link>
      </div>
      {error && <div className="alert error">{error}</div>}
      {saved && <div className="alert success">{saved}</div>}
      <div className="card">
        <div className="grid-3">
          <div>
            <label>Name</label>
            <input type="text" value={workflow.name} onChange={(e) => setWorkflow((w) => ({ ...w, name: e.target.value }))} />
          </div>
          <div>
            <label>Risk Level</label>
            <select value={workflow.risk_level} onChange={(e) => setWorkflow((w) => ({ ...w, risk_level: e.target.value }))}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
          <div>
            <label>Replay Mode</label>
            <select value={workflow.replay_mode_default} onChange={(e) => setWorkflow((w) => ({ ...w, replay_mode_default: e.target.value }))}>
              <option value="dry_run">Dry Run</option>
              <option value="step_by_step">Step by Step</option>
            </select>
          </div>
        </div>
        <div>
          <label>Description</label>
          <textarea rows={2} value={workflow.description} onChange={(e) => setWorkflow((w) => ({ ...w, description: e.target.value }))} />
        </div>
        <button className="primary" onClick={saveWorkflow} disabled={busy}>Save Workflow</button>
      </div>
      <div className="card">
        <h3>Steps ({steps.length})</h3>
        {steps.length === 0 && <div className="muted">No steps.</div>}
        <table>
          <thead>
            <tr>
              <th style={{ width: 40 }}>#</th>
              <th>Type</th>
              <th>Target</th>
              <th>Value (redacted)</th>
              <th>Risk</th>
              <th style={{ width: 80 }}>Enabled</th>
              <th style={{ width: 100 }}>Approval</th>
            </tr>
          </thead>
          <tbody>
            {steps.map((step) => (
              <tr key={step.id} className={!step.enabled ? 'muted' : ''}>
                <td>{step.step_order}</td>
                <td><code>{step.step_type}</code></td>
                <td>{step.target_description || '-'}</td>
                <td>{step.input_value_redacted || '-'}</td>
                <td><span className={`alert ${step.risk_level === 'high' ? 'danger' : step.risk_level === 'medium' ? 'warning' : 'info'}`} style={{ padding: '1px 6px', fontSize: '0.85em' }}>{step.risk_level}</span></td>
                <td>
                  <input type="checkbox" checked={step.enabled} onChange={() => toggleStep(step)} />
                </td>
                <td>
                  <input type="checkbox" checked={step.requires_approval} onChange={() => toggleApproval(step)} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
