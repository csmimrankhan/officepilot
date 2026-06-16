import { useEffect, useState, useCallback } from 'react'
import { api, BROWSER_RISK_LABELS } from '../api.js'
import BrowserPreviewModal from '../components/BrowserPreviewModal.jsx'

/**
 * Voice intents page. Lists every intent the browser layer
 * understands; for the ones that need approval, shows a preview
 * modal so the user can confirm before the action actually runs.
 */
export default function VoiceIntents() {
  const [intents, setIntents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [modalError, setModalError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const rows = await api.listVoiceIntents()
      setIntents(rows)
    } catch (err) {
      setError(err.message || 'Failed to load voice intents.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const dispatch = async (intent) => {
    setError('')
    setMessage('')
    setModalError('')
    try {
      const res = await api.dispatchVoiceIntent({ intent, actor: 'voice' })
      if (res.blocked) {
        setMessage(`Voice intent "${intent}" is blocked in this phase. ${res.message}`)
        return
      }
      setPreview(res)
    } catch (err) {
      setError(err.message || `Failed to dispatch ${intent}.`)
    }
  }

  const approve = async (reason) => {
    if (!preview?.run_id) return
    setBusy(true)
    setModalError('')
    try {
      await api.approveBrowserAction(preview.run_id, { actor: 'voice', reason })
      setMessage(`Voice intent approved and executed (run #${preview.run_id}).`)
      setPreview(null)
    } catch (err) {
      setModalError(err.message || 'Approval failed.')
    } finally {
      setBusy(false)
    }
  }

  const reject = async (reason) => {
    if (!preview?.run_id) {
      setPreview(null)
      return
    }
    setBusy(true)
    setModalError('')
    try {
      await api.rejectBrowserAction(preview.run_id, { actor: 'voice', reason })
      setMessage(`Voice intent rejected.`)
      setPreview(null)
    } catch (err) {
      setModalError(err.message || 'Rejection failed.')
    } finally {
      setBusy(false)
    }
  }

  const cancel = async (reason) => {
    if (!preview?.run_id) {
      setPreview(null)
      return
    }
    setBusy(true)
    setModalError('')
    try {
      await api.cancelBrowserAction(preview.run_id, { actor: 'voice', reason })
      setMessage(`Voice intent cancelled.`)
      setPreview(null)
    } catch (err) {
      setModalError(err.message || 'Cancel failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Voice Intents</h2>
        <span className="subtle">{intents.length} intents</span>
      </div>

      {error && <div className="alert error">{error}</div>}
      {message && <div className="alert success">{message}</div>}

      <p className="subtle">
        Voice commands route through the same preview + approval flow as the UI.
        Read-only intents (e.g. open a Google Sheet) run without prompting.
        Write / submit intents show a preview modal so the user can confirm.
      </p>

      {loading && intents.length === 0 ? (
        <div className="subtle">Loading…</div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Intent</th>
              <th>Action</th>
              <th>Approval?</th>
              <th>Note</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {intents.map((v) => (
              <tr key={v.intent}>
                <td><code className="mono">{v.intent}</code></td>
                <td><code className="mono">{v.action_type || '—'}</code></td>
                <td>
                  {v.blocked
                    ? <span className="badge failed">Blocked</span>
                    : v.needs_approval
                      ? <span className="badge medium">Required</span>
                      : <span className="badge subtle">Not required</span>}
                </td>
                <td className="subtle">{v.note || '—'}</td>
                <td>
                  <button
                    type="button"
                    className="primary"
                    onClick={() => dispatch(v.intent)}
                    disabled={v.blocked}
                    title={v.blocked ? 'Blocked in this phase' : 'Build preview'}
                  >
                    {v.blocked ? 'Blocked' : 'Preview'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <BrowserPreviewModal
        preview={preview}
        onApprove={approve}
        onReject={reject}
        onCancel={cancel}
        onClose={() => setPreview(null)}
        busy={busy}
        errorMessage={modalError}
      />
    </div>
  )
}
