import { useState, useEffect } from 'react'
import { api } from '../api.js'

export default function VoiceCommandCenter() {
  const [history, setHistory] = useState([])
  const [available, setAvailable] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [testText, setTestText] = useState('')

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError('')
    try {
      const [histRes, availRes] = await Promise.all([
        api.getVoiceHistory(),
        api.getAvailableCommands()
      ])
      setHistory(histRes.commands)
      setAvailable(availRes)
    } catch (err) {
      setError(err.message || 'Failed to load data.')
    } finally {
      setLoading(false)
    }
  }

  const handleTestCommand = async () => {
    if (!testText) return
    setError('')
    try {
      const res = await api.parseVoiceCommand(testText)
      // Redirect to modal or just refresh history for now
      setTestText('')
      loadData()
      alert(`Parsed as ${res.domain}:${res.intent}. Preview: ${res.preview_message}`)
    } catch (err) {
      setError(err.message || 'Test failed.')
    }
  }

  return (
    <div className="voice-center">
      <div className="page-header">
        <h2>Voice Command Center</h2>
      </div>

      {error && <div className="alert error">{error}</div>}

      <section className="command-tester card">
        <h3>Try a Command</h3>
        <div className="input-group">
          <input 
            type="text" 
            placeholder="e.g. show pending invoices" 
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleTestCommand()}
          />
          <button className="primary" onClick={handleTestCommand}>Test Parse</button>
        </div>
      </section>

      <div className="voice-grid">
        <section className="available-commands card">
          <h3>What can I say?</h3>
          {loading ? <p>Loading commands...</p> : (
            <div className="categories">
              {available.map(cat => (
                <div key={cat.category} className="command-category">
                  <h4>{cat.category}</h4>
                  <p className="subtle">{cat.description}</p>
                  <ul>
                    {cat.examples.map(ex => (
                      <li key={ex}>"{ex}"</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="command-history card">
          <h3>Recent Commands</h3>
          {loading ? <p>Loading history...</p> : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Command</th>
                  <th>Status</th>
                  <th>Domain</th>
                </tr>
              </thead>
              <tbody>
                {history.map(cmd => (
                  <tr key={cmd.id}>
                    <td>{new Date(cmd.created_at).toLocaleTimeString()}</td>
                    <td>{cmd.raw_text}</td>
                    <td>
                      <span className={`badge ${cmd.status}`}>
                        {cmd.status}
                      </span>
                    </td>
                    <td>{cmd.domain}</td>
                  </tr>
                ))}
                {history.length === 0 && (
                  <tr>
                    <td colSpan="4" className="subtle">No command history yet.</td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  )
}
