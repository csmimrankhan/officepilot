import { useState, useEffect, useCallback } from 'react'
import { api } from '../api.js'
import PageHeader from '../components/layout/PageHeader.jsx'
import EmptyState from '../components/layout/EmptyState.jsx'

const DEFAULT_CATEGORIES = [
  'Excel',
  'Browser',
  'Desktop',
  'File',
  'Email',
  'Workflow',
  'All',
]

export default function AccountingSkills() {
  const [skills, setSkills] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [versions, setVersions] = useState([])
  const [runs, setRuns] = useState([])
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All')
  const [sort, setSort] = useState('name')
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({ name: '', description: '', trigger_phrases: '' })
  const [actionMsg, setActionMsg] = useState('')
  const [savePrompt, setSavePrompt] = useState(null)
  const [saveForm, setSaveForm] = useState({ name: '', description: '', trigger_phrases: '' })
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const rows = await api.listSkills()
      setSkills(rows)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function select(id) {
    try {
      const s = await api.getSkill(id)
      setSelected(s)
      setEditMode(false)
      const v = await api.getSkillVersions(id)
      setVersions(v)
      const r = await api.listSkillRuns(id)
      setRuns(r)
    } catch (err) {
      setError(err.message)
    }
  }

  function startEdit() {
    if (!selected) return
    setEditForm({
      name: selected.name,
      description: selected.description || '',
      trigger_phrases: (selected.trigger_phrases || []).join(', '),
    })
    setEditMode(true)
  }

  async function saveEdit() {
    if (!selected) return
    setActionMsg('')
    try {
      const phrases = editForm.trigger_phrases.split(',').map(s => s.trim()).filter(Boolean)
      await api.updateSkill(selected.id, {
        name: editForm.name,
        description: editForm.description,
        trigger_phrases_json: JSON.stringify(phrases),
      })
      setActionMsg('Saved!')
      setEditMode(false)
      select(selected.id)
    } catch (err) {
      setActionMsg(err.message)
    }
  }

  async function handleDryRun(id) {
    setActionMsg('')
    try {
      const res = await api.dryRunSkill(id)
      setActionMsg(`Dry-run complete (run #${res.run_id})`)
      if (selected && selected.id === id) select(id)
    } catch (err) {
      setActionMsg(err.message)
    }
  }

  async function handleExecute(id) {
    setActionMsg('')
    try {
      const res = await api.executeSkill(id, {})
      setActionMsg(`Execution started (run #${res.run_id})`)
      if (selected && selected.id === id) select(id)
    } catch (err) {
      setActionMsg(err.message)
    }
  }

  async function handleArchive(id) {
    setActionMsg('')
    try {
      await api.archiveSkill(id)
      setActionMsg('Archived')
      setSelected(null)
      load()
    } catch (err) {
      setActionMsg(err.message)
    }
  }

  async function handleRestore(version) {
    if (!selected) return
    setActionMsg('')
    try {
      await api.restoreSkillVersion(selected.id, version)
      setActionMsg(`Restored to v${version}`)
      select(selected.id)
    } catch (err) {
      setActionMsg(err.message)
    }
  }

  async function handleSaveFromWorkflow() {
    if (!savePrompt) return
    setCreating(true); setActionMsg('')
    try {
      const phrases = saveForm.trigger_phrases.split(',').map(s => s.trim()).filter(Boolean)
      const body = {
        plan_id: savePrompt.plan_id,
        workflow_memory_id: savePrompt.workflow_memory_id,
        name: saveForm.name || undefined,
        description: saveForm.description || undefined,
        trigger_phrases: phrases.length ? phrases : undefined,
      }
      const res = await api.createSkillFromWorkflow(body)
      setActionMsg(`Skill "${res.name}" created!`)
      setSavePrompt(null)
      load()
    } catch (err) {
      setActionMsg(err.message)
    } finally {
      setCreating(false)
    }
  }

  function inferCategory(skill) {
    const name = (skill.name || '').toLowerCase()
    const desc = (skill.description || '').toLowerCase()
    const triggers = (skill.trigger_phrases || []).join(' ').toLowerCase()
    const text = `${name} ${desc} ${triggers}`
    if (text.includes('excel') || text.includes('spreadsheet') || text.includes('pivot') || text.includes('formula') || text.includes('summary')) return 'Excel'
    if (text.includes('browser') || text.includes('navigate') || text.includes('page') || text.includes('url') || text.includes('web')) return 'Browser'
    if (text.includes('desktop') || text.includes('screen') || text.includes('click') || text.includes('type')) return 'Desktop'
    if (text.includes('file') || text.includes('folder') || text.includes('copy')) return 'File'
    if (text.includes('email') || text.includes('gmail') || text.includes('mail') || text.includes('attachment')) return 'Email'
    if (text.includes('workflow') || text.includes('record') || text.includes('replay')) return 'Workflow'
    return 'Automation'
  }

  function getRiskBadge(skill) {
    const risk = skill.risk_level || 'low'
    if (risk === 'high') return 'badge badge--danger'
    if (risk === 'medium') return 'badge badge--warning'
    return 'badge badge--success'
  }

  function getRiskLabel(skill) {
    return skill.approval_required ? 'Approval' : 'Auto'
  }

  const filtered = skills.filter(s => {
    if (category !== 'All' && inferCategory(s) !== category) return false
    if (!search) return true
    const q = search.toLowerCase()
    return (s.name || '').toLowerCase().includes(q) ||
      (s.description || '').toLowerCase().includes(q) ||
      (s.trigger_phrases || []).some(p => p.toLowerCase().includes(q))
  })

  const sorted = [...filtered].sort((a, b) => {
    if (sort === 'name') return (a.name || '').localeCompare(b.name || '')
    if (sort === 'runs') return (b.run_count || 0) - (a.run_count || 0)
    if (sort === 'recent') {
      const da = a.last_used_at ? new Date(a.last_used_at) : new Date(0)
      const db = b.last_used_at ? new Date(b.last_used_at) : new Date(0)
      return db - da
    }
    return 0
  })

  const lastRun = selected?.last_used_at
    ? new Date(selected.last_used_at).toLocaleDateString()
    : 'Never'

  const totalRuns = selected?.run_count || 0

  return (
    <div className="skills-page">
      <PageHeader
        title="Skills"
        subtitle="Reusable automation workflows for accounting tasks."
        actions={
          <div className="skills-header-actions">
            <div className="skills-search">
              <span className="skills-search-icon">🔍</span>
              <input
                type="text"
                placeholder="Search skills..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="skills-search-input"
              />
            </div>
            <select
              className="skills-filter"
              value={category}
              onChange={e => setCategory(e.target.value)}
            >
              {DEFAULT_CATEGORIES.map(c => (
                <option key={c} value={c}>{c === 'All' ? 'All Categories' : c}</option>
              ))}
            </select>
            <select
              className="skills-filter"
              value={sort}
              onChange={e => {
                setSort(e.target.value);
                setSelected(null)
              }}
            >
              <option value="name">Name</option>
              <option value="runs">Most Used</option>
              <option value="recent">Recently Used</option>
            </select>
          </div>
        }
      />

      {error && <div className="alert alert--error">{error}</div>}
      {actionMsg && <div className="alert alert--success">{actionMsg}</div>}

      {savePrompt && (
        <div className="card skills-save-prompt">
          <h3>Save as Reusable Skill?</h3>
          <p className="skills-save-desc">
            This workflow can be saved as a skill for reuse with similar commands.
          </p>
          <div className="skills-save-form">
            <input
              placeholder="Skill name (auto-generated if empty)"
              value={saveForm.name}
              onChange={e => setSaveForm(f => ({ ...f, name: e.target.value }))}
              className="skills-save-input"
            />
            <input
              placeholder="Description"
              value={saveForm.description}
              onChange={e => setSaveForm(f => ({ ...f, description: e.target.value }))}
              className="skills-save-input"
            />
            <input
              placeholder="Trigger phrases (comma-separated)"
              value={saveForm.trigger_phrases}
              onChange={e => setSaveForm(f => ({ ...f, trigger_phrases: e.target.value }))}
              className="skills-save-input"
            />
            <div className="skills-save-actions">
              <button className="btn btn--primary" onClick={handleSaveFromWorkflow} disabled={creating}>
                {creating ? 'Saving...' : 'Save Skill'}
              </button>
              <button className="btn" onClick={() => setSavePrompt(null)}>Skip</button>
            </div>
          </div>
        </div>
      )}

      <div className="skills-layout">
        <div className="skills-grid">
          {loading && (
            <div className="loading-spinner">
              <div className="spinner" />
              <p>Loading skills...</p>
            </div>
          )}

          {!loading && sorted.length === 0 && (
            <EmptyState
              icon="⚡"
              title="No skills found"
              description={search || category !== 'All' ? 'Try adjusting your search or filters.' : 'Complete a workflow and save it as a reusable skill.'}
            />
          )}

          {!loading && sorted.map(s => (
            <div
              key={s.id}
              className={`skill-card ${selected && selected.id === s.id ? 'skill-card--selected' : ''}`}
              onClick={() => select(s.id)}
            >
              <div className="skill-card-header">
                <h3 className="skill-card-name">{s.name}</h3>
                <span className={getRiskBadge(s)}>{getRiskLabel(s)}</span>
              </div>
              {s.description && (
                <p className="skill-card-desc">{s.description}</p>
              )}
              <div className="skill-card-triggers">
                {(s.trigger_phrases || []).slice(0, 3).map((p, i) => (
                  <span key={i} className="badge badge--info">{p}</span>
                ))}
                {(s.trigger_phrases || []).length > 3 && (
                  <span className="badge badge--default">+{s.trigger_phrases.length - 3}</span>
                )}
              </div>
              <div className="skill-card-meta">
                <span className="skill-card-category">{inferCategory(s)}</span>
                <span className="skill-card-version">v{s.version}</span>
                <span className="skill-card-runs">{s.run_count || 0} runs</span>
              </div>
              <div className="skill-card-actions">
                <button className="btn btn--sm" onClick={e => { e.stopPropagation(); select(s.id) }}>View</button>
                <button className="btn btn--sm btn--primary" onClick={e => { e.stopPropagation(); handleDryRun(s.id) }}>Dry Run</button>
                <button className="btn btn--sm btn--success" onClick={e => { e.stopPropagation(); handleExecute(s.id) }}>Run</button>
              </div>
            </div>
          ))}
        </div>

        <div className="skills-detail">
          {!selected && (
            <EmptyState
              icon="👆"
              title="Select a skill"
              description="Select a skill to preview its steps, triggers, and safety rules."
            />
          )}

          {selected && !editMode && (
            <div className="skill-detail">
              <div className="skill-detail-header">
                <div>
                  <h2 className="skill-detail-name">{selected.name}</h2>
                  {selected.description && (
                    <p className="skill-detail-desc">{selected.description}</p>
                  )}
                </div>
                <div className="skill-detail-badges">
                  <span className={getRiskBadge(selected)}>{getRiskLabel(selected)}</span>
                  <span className="badge badge--default">v{selected.version}</span>
                  <span className="badge badge--default">{inferCategory(selected)}</span>
                </div>
              </div>

              <div className="skill-detail-stats">
                <div className="skill-detail-stat">
                  <span className="skill-detail-stat-value">{totalRuns}</span>
                  <span className="skill-detail-stat-label">Total Runs</span>
                </div>
                <div className="skill-detail-stat">
                  <span className="skill-detail-stat-value">{selected.approval_required ? 'Yes' : 'No'}</span>
                  <span className="skill-detail-stat-label">Approval Required</span>
                </div>
                <div className="skill-detail-stat">
                  <span className="skill-detail-stat-value">{lastRun}</span>
                  <span className="skill-detail-stat-label">Last Run</span>
                </div>
                <div className="skill-detail-stat">
                  <span className="skill-detail-stat-value">{selected.workflow_steps?.length || 0}</span>
                  <span className="skill-detail-stat-label">Steps</span>
                </div>
              </div>

              <div className="skill-detail-section">
                <h4>Trigger Phrases</h4>
                <div className="skill-detail-tags">
                  {(selected.trigger_phrases || []).map((p, i) => (
                    <span key={i} className="badge badge--info">{p}</span>
                  ))}
                  {(!selected.trigger_phrases || selected.trigger_phrases.length === 0) && (
                    <span className="text-muted">No trigger phrases</span>
                  )}
                </div>
              </div>

              <div className="skill-detail-section">
                <h4>Workflow Steps ({selected.workflow_steps?.length || 0})</h4>
                <div className="skill-detail-steps">
                  {(selected.workflow_steps || []).map((step, i) => (
                    <div key={i} className="skill-step">
                      <div className="skill-step-number">{i + 1}</div>
                      <div className="skill-step-info">
                        <div className="skill-step-type">{step.step_type || step.tool || '—'}</div>
                        {step.target && <div className="skill-step-target">{step.target}</div>}
                      </div>
                      <span className={`badge ${(step.risk_level || 'low') === 'high' ? 'badge--danger' : (step.risk_level || 'low') === 'medium' ? 'badge--warning' : 'badge--success'}`}>
                        {step.risk_level || 'low'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="skill-detail-actions">
                <button className="btn btn--primary" onClick={() => handleDryRun(selected.id)}>Dry Run</button>
                <button className="btn btn--success" onClick={() => handleExecute(selected.id)}>Run Skill</button>
                <button className="btn" onClick={startEdit}>Edit</button>
                <button className="btn btn--ghost" onClick={() => handleArchive(selected.id)}>Archive</button>
              </div>

              {(versions.length > 0 || runs.length > 0) && (
                <div className="skill-detail-tabs">
                  {versions.length > 0 && (
                    <div className="skill-detail-section">
                      <h4>Version History</h4>
                      <div className="skill-detail-versions">
                        {versions.map(v => (
                          <div key={v.version} className="skill-version-row">
                            <span className="badge badge--default">v{v.version}</span>
                            <span className="skill-version-name">{v.name}</span>
                            <span className="skill-version-steps">{v.steps_count || '?'} steps</span>
                            <span className="skill-version-date">{new Date(v.created_at).toLocaleDateString()}</span>
                            {v.version < selected.version ? (
                              <button className="btn btn--sm btn--ghost" onClick={() => handleRestore(v.version)}>Restore</button>
                            ) : (
                              <span className="badge badge--success">current</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {runs.length > 0 && (
                    <div className="skill-detail-section">
                      <h4>Recent Runs</h4>
                      <div className="skill-detail-runs">
                        {runs.slice(0, 10).map(r => (
                          <div key={r.id} className="skill-run-row">
                            <span className="text-muted">#{r.id}</span>
                            <span className={`badge ${r.status === 'completed' ? 'badge--success' : r.status === 'running' ? 'badge--warning' : 'badge--default'}`}>{r.status}</span>
                            <span className="skill-run-command">{r.command_text || '—'}</span>
                            <span className="skill-run-date text-muted">{new Date(r.created_at).toLocaleString()}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {selected && editMode && (
            <div className="card skill-edit-form">
              <h3>Edit Skill</h3>
              <div className="form-group">
                <label className="form-label">Name</label>
                <input className="form-input" value={editForm.name} onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Description</label>
                <textarea className="form-textarea" value={editForm.description} onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))} rows={3} />
              </div>
              <div className="form-group">
                <label className="form-label">Trigger Phrases (comma-separated)</label>
                <input className="form-input" value={editForm.trigger_phrases} onChange={e => setEditForm(f => ({ ...f, trigger_phrases: e.target.value }))} />
              </div>
              <div className="form-actions">
                <button className="btn btn--primary" onClick={saveEdit}>Save</button>
                <button className="btn" onClick={() => setEditMode(false)}>Cancel</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}