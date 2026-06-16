import { useEffect, useState, useCallback } from 'react'
import { api } from '../api.js'

const MUTABLE_FIELDS = [
  { key: 'agent_host', label: 'Agent host', type: 'text',
    help: 'Bind address. Restart required to take effect.' },
  { key: 'agent_port', label: 'Agent port', type: 'number',
    help: 'Listening port. Restart required to take effect.' },
  { key: 'ocr_enabled', label: 'OCR enabled', type: 'bool',
    help: 'Enable Tesseract/PaddleOCR for image-only PDFs.' },
  { key: 'gmail_allow_real', label: 'Allow real Gmail API calls', type: 'bool',
    help: 'When false, the fake Gmail client is used (safe for offline dev).' },
  { key: 'max_upload_mb', label: 'Max upload size (MB)', type: 'number',
    help: 'Reject uploads larger than this many megabytes.' }
]

export default function StorageSettings() {
  const [settings, setSettings] = useState(null)
  const [status, setStatus] = useState(null)
  const [draft, setDraft] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [lastResult, setLastResult] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [s, st] = await Promise.all([api.localSettings(), api.localStatus()])
      setSettings(s)
      setStatus(st)
      setDraft(s.settings || {})
    } catch (err) {
      setError(err.message || 'Failed to load settings.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const isMutable = (k) => settings && settings.mutable && settings.mutable.includes(k)

  const update = (k, v) => {
    setDraft((d) => ({ ...d, [k]: v }))
  }

  const save = async () => {
    if (!settings) return
    setSaving(true)
    setError('')
    setLastResult(null)
    // Only send keys that (a) are in the mutable allow-list and
    // (b) differ from the current value.
    const patch = {}
    for (const k of settings.mutable || []) {
      const cur = settings.settings[k]
      const newV = draft[k]
      if (newV === undefined) continue
      if (cur === newV) continue
      // Coerce types so the backend can parse them.
      if (typeof cur === 'number') patch[k] = Number(newV)
      else if (typeof cur === 'boolean') patch[k] = newV === true || newV === 'true'
      else patch[k] = String(newV)
    }
    try {
      const res = await api.patchLocalSettings(patch)
      setLastResult(res)
      await load()
    } catch (err) {
      setError(err.message || 'Failed to save settings.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="subtle">Loading…</div>
  if (error && !settings) return <div className="alert error">{error}</div>
  if (!settings) return <div className="muted">No settings.</div>

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Storage &amp; Local Settings</h2>
          <span className="subtle">Phase 7 · local desktop shell</span>
        </div>
        <button type="button" className="secondary" onClick={load} disabled={saving}>
          Refresh
        </button>
      </div>

      <h3>Storage locations (read-only)</h3>
      <p className="subtle">
        These directories are configured by environment variables. To
        change them permanently, edit your <code className="mono">.env</code> file
        and restart the agent. The Tauri shell ships with sensible
        defaults that point to the OS user-data dir.
      </p>
      {status && (
        <table className="data-table">
          <tbody>
            <tr>
              <th>Data directory</th>
              <td><code className="mono">{status.data_dir}</code></td>
            </tr>
            <tr>
              <th>Storage root</th>
              <td><code className="mono">{status.storage_root}</code></td>
            </tr>
            <tr>
              <th>Agent URL</th>
              <td><code className="mono">{status.url}</code></td>
            </tr>
          </tbody>
        </table>
      )}

      <h3>Mutable settings</h3>
      <p className="subtle">
        Changes apply to this running process and are also written to
        <code className="mono"> os.environ</code>. The audit log records
        who made the change.
      </p>

      {error && <div className="alert error">{error}</div>}
      {lastResult && (
        <div className={`alert ${lastResult.rejected && Object.keys(lastResult.rejected).length ? 'warning' : 'success'}`}>
          Applied: <code className="mono">{JSON.stringify(lastResult.applied)}</code>
          {lastResult.rejected && Object.keys(lastResult.rejected).length > 0 && (
            <div>Rejected: <code className="mono">{JSON.stringify(lastResult.rejected)}</code></div>
          )}
        </div>
      )}

      <table className="data-table">
        <thead>
          <tr><th>Key</th><th>Value</th><th>Type</th><th>Mutable</th></tr>
        </thead>
        <tbody>
          {Object.entries(settings.settings).map(([k, v]) => {
            const field = MUTABLE_FIELDS.find((f) => f.key === k)
            const mutable = isMutable(k)
            return (
              <tr key={k}>
                <td>
                  <code className="mono">{k}</code>
                  {field && field.help && (
                    <div className="subtle">{field.help}</div>
                  )}
                </td>
                <td>
                  {mutable ? (
                    field && field.type === 'bool' ? (
                      <select
                        value={String(draft[k])}
                        onChange={(e) => update(k, e.target.value === 'true')}
                      >
                        <option value="true">true</option>
                        <option value="false">false</option>
                      </select>
                    ) : (
                      <input
                        type={field && field.type === 'number' ? 'number' : 'text'}
                        value={String(draft[k] ?? '')}
                        onChange={(e) => update(k, e.target.value)}
                      />
                    )
                  ) : (
                    <code className="mono">{String(v)}</code>
                  )}
                </td>
                <td className="subtle">{field ? field.type : typeof v}</td>
                <td>{mutable ? 'yes' : <span className="subtle">no</span>}</td>
              </tr>
            )
          })}
        </tbody>
      </table>

      <div className="toolbar">
        <button
          type="button"
          className="primary"
          onClick={save}
          disabled={saving}
        >
          {saving ? 'Saving…' : 'Save changes'}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => setDraft(settings.settings)}
          disabled={saving}
        >
          Reset
        </button>
      </div>
    </div>
  )
}
