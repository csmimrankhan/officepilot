import { useEffect, useState, useCallback } from 'react'
import { api } from '../api.js'

export default function DictationHistory() {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modeFilter, setModeFilter] = useState('')
  const [copiedId, setCopiedId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({ limit: '100', offset: '0' })
      if (modeFilter) params.set('mode', modeFilter)
      const res = await fetch(`${api.base}/api/voice-layer/history?${params}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}` },
      })
      const data = await res.json()
      if (data.ok) {
        setItems(data.items || [])
        setTotal(data.total || 0)
      } else {
        setError(data.error || 'Failed to load history')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [modeFilter])

  useEffect(() => { load() }, [load])

  const deleteEntry = async (id) => {
    try {
      const res = await fetch(`${api.base}/api/voice-layer/history/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}` },
      })
      const data = await res.json()
      if (data.ok) load()
    } catch (err) {
      setError(err.message)
    }
  }

  const clearAll = async () => {
    try {
      const res = await fetch(`${api.base}/api/voice-layer/history`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${localStorage.getItem('auth_token') || ''}` },
      })
      const data = await res.json()
      if (data.ok) { setItems([]); setTotal(0) }
    } catch (err) {
      setError(err.message)
    }
  }

  const copyToClipboard = async (text, id) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedId(id)
      setTimeout(() => setCopiedId(null), 2000)
    } catch {}
  }

  return (
    <div>
      <div className="page-header">
        <h2>Dictation History</h2>
        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          {total} entries
        </span>
      </div>
      {error && <div className="alert error">{error}</div>}

      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', alignItems: 'center' }}>
        <select value={modeFilter} onChange={e => setModeFilter(e.target.value)}
          style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid var(--border)' }}>
          <option value="">All modes</option>
          <option value="dictation">Dictation</option>
          <option value="ai_mode">AI Mode</option>
          <option value="agent_command">Agent Command</option>
        </select>
        <button className="btn btn--ghost" onClick={clearAll}
          style={{ marginLeft: 'auto', fontSize: '12px', color: '#dc2626' }}
          disabled={items.length === 0}>
          Clear All
        </button>
      </div>

      {loading ? (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading history...
        </div>
      ) : items.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px' }}>
          No dictation history yet. Start a dictation to see entries here.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {items.map(item => (
            <div key={item.id} className="card" style={{ padding: '12px 16px', fontSize: '13px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span className={`badge ${item.mode === 'ai_mode' ? 'medium' : item.mode === 'agent_command' ? 'primary' : 'subtle'}`}>
                    {item.mode}
                  </span>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {new Date(item.created_at).toLocaleString()}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button className="btn btn--ghost" style={{ fontSize: '11px', padding: '2px 8px' }}
                    onClick={() => copyToClipboard(item.transcript, item.id)}>
                    {copiedId === item.id ? 'Copied!' : 'Copy'}
                  </button>
                  <button className="btn btn--ghost" style={{ fontSize: '11px', padding: '2px 8px', color: '#dc2626' }}
                    onClick={() => deleteEntry(item.id)}>
                    Delete
                  </button>
                </div>
              </div>
              <p style={{ margin: '4px 0', color: 'var(--text)' }}>{item.transcript}</p>
              {item.ai_output && (
                <p style={{ margin: '4px 0', color: '#16a34a', fontSize: '12px' }}>
                  → {item.ai_output}
                </p>
              )}
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Pasted: {item.pasted ? 'Yes' : 'No'}
                {item.target_app && ` | App: ${item.target_app}`}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}