import { useEffect, useState, useCallback } from 'react'
import { api } from '../api.js'

/**
 * Browser automation settings page. Toggle the master switch,
 * edit the domain allowlist / blocklist, choose whether
 * screenshots and approval-for-write/submit are required, and
 * see the live adapter status.
 */
export default function BrowserSettings() {
  const [policy, setPolicy] = useState(null)
  const [status, setStatus] = useState(null)
  const [voices, setVoices] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [allowedText, setAllowedText] = useState('')
  const [blockedText, setBlockedText] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [p, s, v] = await Promise.all([
        api.getBrowserPolicies(),
        api.getBrowserStatus(),
        api.listVoiceIntents()
      ])
      setPolicy(p)
      setStatus(s)
      setVoices(v)
      setAllowedText((p.allowed_domains || []).join('\n'))
      setBlockedText((p.blocked_domains || []).join('\n'))
    } catch (err) {
      setError(err.message || 'Failed to load browser settings.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async (overrides = {}) => {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const allowed = allowedText
        .split(/[\n,]+/)
        .map((s) => s.trim().toLowerCase())
        .filter(Boolean)
      const blocked = blockedText
        .split(/[\n,]+/)
        .map((s) => s.trim().toLowerCase())
        .filter(Boolean)
      const patch = {
        ...overrides,
        allowed_domains: allowed,
        blocked_domains: blocked
      }
      const next = await api.updateBrowserPolicies(patch)
      setPolicy(next)
      setAllowedText((next.allowed_domains || []).join('\n'))
      setBlockedText((next.blocked_domains || []).join('\n'))
      setMessage('Browser policy saved.')
    } catch (err) {
      setError(err.message || 'Failed to save browser policy.')
    } finally {
      setSaving(false)
    }
  }

  const onToggle = (key) => async (ev) => {
    const value = ev.target.checked
    setPolicy((p) => ({ ...p, [key]: value }))
    await save({ [key]: value })
  }

  const stop = async () => {
    setError('')
    setMessage('')
    try {
      await api.stopBrowser()
      setMessage('Browser adapter stopped.')
      await load()
    } catch (err) {
      setError(err.message || 'Failed to stop browser.')
    }
  }

  if (loading || !policy) {
    return (
      <div>
        <div className="page-header">
          <h2>Browser Automation</h2>
        </div>
        {error ? <div className="alert error">{error}</div> : <div className="subtle">Loading…</div>}
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <h2>Browser Automation</h2>
        <span className="subtle">
          {policy.enabled
            ? 'Enabled — approved actions run automatically.'
            : 'Disabled — previews and actions will be blocked.'}
        </span>
      </div>

      {error && <div className="alert error">{error}</div>}
      {message && <div className="alert success">{message}</div>}

      <div className="card">
        <h3>Master switch</h3>
        <label className="field-row">
          <input
            type="checkbox"
            checked={policy.enabled}
            onChange={onToggle('enabled')}
            disabled={saving}
          />
          <span>Enable browser automation (default-deny; off is safest)</span>
        </label>
        <label className="field-row">
          <input
            type="checkbox"
            checked={policy.headless}
            onChange={onToggle('headless')}
            disabled={saving}
          />
          <span>Run Chromium headless (no visible window)</span>
        </label>
        <label className="field-row">
          <input
            type="checkbox"
            checked={policy.screenshots_enabled}
            onChange={onToggle('screenshots_enabled')}
            disabled={saving}
          />
          <span>Capture screenshots before / after each step</span>
        </label>
      </div>

      <div className="card">
        <h3>Approvals</h3>
        <label className="field-row">
          <input
            type="checkbox"
            checked={policy.require_approval_for_write}
            onChange={onToggle('require_approval_for_write')}
            disabled={saving}
          />
          <span>Require approval before writing to a form field</span>
        </label>
        <label className="field-row">
          <input
            type="checkbox"
            checked={policy.require_approval_for_submit}
            onChange={onToggle('require_approval_for_submit')}
            disabled={saving}
          />
          <span>Require approval before clicking submit / save</span>
        </label>
      </div>

      <div className="card">
        <h3>Domain allowlist</h3>
        <p className="subtle">
          One domain per line. Subdomains are matched automatically (e.g. <code>sheets.google.com</code> allows <code>docs.google.com</code>). Bank, payment, password manager, and tax domains are blocked by default.
        </p>
        <textarea
          rows={8}
          value={allowedText}
          onChange={(e) => setAllowedText(e.target.value)}
          style={{ width: '100%', fontFamily: 'monospace' }}
        />
        <h3 style={{ marginTop: 16 }}>Domain blocklist</h3>
        <textarea
          rows={6}
          value={blockedText}
          onChange={(e) => setBlockedText(e.target.value)}
          style={{ width: '100%', fontFamily: 'monospace' }}
        />
        <div className="toolbar" style={{ marginTop: 8 }}>
          <button type="button" className="primary" onClick={() => save()} disabled={saving}>
            {saving ? 'Saving…' : 'Save lists'}
          </button>
        </div>
      </div>

      <div className="card">
        <h3>Live adapter</h3>
        {status ? (
          <table className="data-table">
            <tbody>
              <tr>
                <th>Adapter mode</th>
                <td>
                  <span className={`badge ${status.adapter_mode === 'playwright' ? 'ok' : 'subtle'}`}>
                    {status.adapter_mode}
                  </span>
                </td>
              </tr>
              <tr>
                <th>Live?</th>
                <td>{status.live ? 'Yes' : 'No (dry-run fallback)'}</td>
              </tr>
              <tr>
                <th>Last URL</th>
                <td><code className="mono">{status.last_url || '—'}</code></td>
              </tr>
              <tr>
                <th>Last title</th>
                <td>{status.last_title || '—'}</td>
              </tr>
            </tbody>
          </table>
        ) : (
          <div className="subtle">No status available.</div>
        )}
        <div className="toolbar">
          <button type="button" className="secondary" onClick={stop}>
            Stop adapter
          </button>
          <button type="button" className="secondary" onClick={load}>
            Refresh
          </button>
        </div>
      </div>

      <div className="card">
        <h3>Voice intents</h3>
        <p className="subtle">These are the intents the voice layer can dispatch. Anything that would write / submit still requires explicit UI approval.</p>
        <table className="data-table">
          <thead>
            <tr>
              <th>Intent</th>
              <th>Action</th>
              <th>Default URL</th>
              <th>Approval?</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {voices.map((v) => (
              <tr key={v.intent}>
                <td><code className="mono">{v.intent}</code></td>
                <td>{v.action_type || '—'}</td>
                <td className="mono">{v.default_url || '—'}</td>
                <td>
                  {v.blocked
                    ? <span className="badge failed">Blocked</span>
                    : v.needs_approval
                      ? <span className="badge medium">Required</span>
                      : <span className="badge subtle">Not required</span>}
                </td>
                <td className="subtle">{v.note || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Test form</h3>
        <p className="subtle">
          A safe local page for practicing browser automation. Open it in another tab and point a preview at its URL.
        </p>
        <a className="primary" href={api.testFormUrl()} target="_blank" rel="noreferrer" style={{ padding: '8px 12px' }}>
          Open local test form
        </a>
      </div>
    </div>
  )
}
