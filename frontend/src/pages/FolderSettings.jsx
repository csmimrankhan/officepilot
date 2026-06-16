import { useEffect, useState } from 'react'
import { api, formatDateTime } from '../api.js'

const DEFAULTS = {
  enabled: true,
  pattern: 'Invoices/{year}/{month}/{vendor}_{invoice_number}_{total}_{currency}.{ext}',
  conflict_strategy: 'suffix',
  move_on_approve: true
}

const TOKEN_HELP = [
  '{year}', '{month}', '{day}', '{date}',
  '{vendor}', '{invoice_number}', '{total}', '{currency}',
  '{source}', '{id}', '{ext}'
]

export default function FolderSettings() {
  const [rules, setRules] = useState(DEFAULTS)
  const [original, setOriginal] = useState(DEFAULTS)
  const [audit, setAudit] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)
  const [actor, setActor] = useState('admin')

  const load = async () => {
    setLoading(true); setError('')
    try {
      const [r, a] = await Promise.all([
        api.getFolderRules(),
        api.folderRulesAudit(50)
      ])
      setRules(r)
      setOriginal(r)
      setAudit(a || [])
    } catch (err) {
      setError(err.message || 'Failed to load settings.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const dirty = JSON.stringify(rules) !== JSON.stringify(original)

  const update = (k, v) => setRules((r) => ({ ...r, [k]: v }))

  const reset = () => setRules(original)

  const save = async () => {
    setSaving(true); setError(''); setSaved(false)
    try {
      const patch = {}
      for (const k of Object.keys(rules)) {
        if (rules[k] !== original[k]) patch[k] = rules[k]
      }
      const updated = await api.updateFolderRules(patch, actor)
      setOriginal(updated)
      setRules(updated)
      setSaved(true)
      // Reload audit
      const a = await api.folderRulesAudit(50)
      setAudit(a || [])
    } catch (err) {
      setError(err.message || 'Save failed.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="card">Loading folder settings…</div>

  return (
    <div>
      <div className="page-header">
        <h2>Folder Rules</h2>
        <span className="subtle">How approved invoice files are renamed and organized.</span>
      </div>

      {error && <div className="alert error">{error}</div>}
      {saved && <div className="alert success">Saved.</div>}

      <div className="card">
        <div className="grid-2">
          <div>
            <label>Enabled</label>
            <div>
              <label className="subtle" style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                <input
                  type="checkbox"
                  checked={rules.enabled}
                  onChange={(e) => update('enabled', e.target.checked)}
                />
                Apply folder rules to the system
              </label>
            </div>
          </div>
          <div>
            <label>Move on approve</label>
            <div>
              <label className="subtle" style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                <input
                  type="checkbox"
                  checked={rules.move_on_approve}
                  onChange={(e) => update('move_on_approve', e.target.checked)}
                />
                Auto-move the file when an invoice is approved
              </label>
            </div>
          </div>
          <div style={{ gridColumn: '1 / -1' }}>
            <label>Pattern</label>
            <input
              type="text"
              value={rules.pattern}
              onChange={(e) => update('pattern', e.target.value)}
              spellCheck={false}
            />
            <div className="subtle" style={{ marginTop: 6 }}>
              Available tokens: {TOKEN_HELP.map((t, i) => (
                <code key={t} style={{ marginRight: 6 }}>{t}</code>
              ))}
            </div>
          </div>
          <div>
            <label>Conflict strategy</label>
            <select
              value={rules.conflict_strategy}
              onChange={(e) => update('conflict_strategy', e.target.value)}
            >
              <option value="suffix">Append suffix (_1, _2, …)</option>
              <option value="skip">Skip if target exists</option>
              <option value="overwrite">Overwrite existing file</option>
            </select>
          </div>
          <div>
            <label>Save as actor</label>
            <input
              type="text"
              value={actor}
              onChange={(e) => setActor(e.target.value)}
              placeholder="e.g. admin"
            />
            <div className="subtle" style={{ marginTop: 6 }}>
              Recorded in the audit log so changes are traceable.
            </div>
          </div>
        </div>
        <div className="toolbar" style={{ marginTop: 12 }}>
          <button onClick={save} disabled={saving || !dirty}>Save changes</button>
          <button className="secondary" onClick={reset} disabled={saving || !dirty}>Reset</button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Change History</h3>
        {audit.length === 0 && <div className="muted">No changes yet — the defaults are still in effect.</div>}
        <ol className="audit-timeline">
          {audit.map((row) => (
            <li key={row.id} className="audit-item">
              <div className="audit-row">
                <div>
                  <div className="audit-action">Updated folder rules</div>
                  <div className="subtle">{formatDateTime(row.created_at)} · by <strong>{row.actor}</strong></div>
                </div>
              </div>
              <div className="audit-diff">
                <div className="grid-2">
                  <div>
                    <div className="subtle">Before</div>
                    <pre style={{ background: 'var(--c-bg-soft)', padding: 8, borderRadius: 4 }}>
                      {row.before ? JSON.stringify(row.before, null, 2) : '—'}
                    </pre>
                  </div>
                  <div>
                    <div className="subtle">After</div>
                    <pre style={{ background: 'var(--c-bg-soft)', padding: 8, borderRadius: 4 }}>
                      {row.after ? JSON.stringify(row.after, null, 2) : '—'}
                    </pre>
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
