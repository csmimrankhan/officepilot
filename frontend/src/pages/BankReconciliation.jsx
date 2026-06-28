import { useState, useRef, useCallback } from 'react'
import * as api from '../api.js'
import { Download, Upload, CheckCircle, AlertTriangle, Loader } from 'lucide-react'

export default function BankReconciliation() {
  const [transactions, setTransactions] = useState(null)
  const [records, setRecords] = useState(null)
  const [summary, setSummary] = useState(null)
  const [filepath, setFilepath] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(null)
  const fileRef = useRef(null)

  const handleFile = useCallback(async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    setLoading('parsing')
    try {
      const text = await new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = () => resolve(reader.result)
        reader.onerror = () => reject(new Error('Failed to read file'))
        reader.readAsText(file)
      })
      const filename = file.name
      const res = await api.bankParseFeed(text, filename)
      if (res.ok) {
        setTransactions(res.transactions)
      } else {
        setError('Failed to parse bank feed.')
      }
    } catch (err) {
      setError(err.message || 'Failed to parse file.')
    } finally {
      setLoading(null)
    }
  }, [])

  const handleReconcile = useCallback(async () => {
    if (!transactions || transactions.length === 0) return
    setError(null)
    setLoading('reconciling')
    try {
      const res = await api.bankReconcile(transactions)
      if (res.ok) {
        setSummary(res.summary)
        setFilepath(res.filepath)
        setRecords(res.summary?.details || [])
      } else {
        setError(res.error || 'Reconciliation failed.')
      }
    } catch (err) {
      setError(err.message || 'Reconciliation failed.')
    } finally {
      setLoading(null)
    }
  }, [transactions])

  function handleDownload() {
    if (filepath) {
      const a = document.createElement('a')
      a.href = `${import.meta.env.VITE_API_BASE || ''}${filepath}`
      a.download = filepath.split(/[/\\]/).pop()
      a.click()
    }
  }

  function handleReset() {
    setTransactions(null)
    setRecords(null)
    setSummary(null)
    setFilepath(null)
    setError(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Bank Reconciliation</h1>
        <p className="page-subtitle">Upload a CSV or JSON bank feed to automatically reconcile against extracted invoices.</p>
      </div>

      {!transactions && (
        <div className="card">
          <div className="card-body" style={{ padding: '2rem', textAlign: 'center' }}>
            <Upload size={48} strokeWidth={1.5} style={{ color: '#6b7280', marginBottom: '1rem' }} />
            <h3>Upload Bank Feed</h3>
            <p style={{ color: '#6b7280', marginBottom: '1.5rem' }}>
              Supported formats: CSV (date,description,amount,type) or JSON
            </p>
            <label className="btn btn--primary" style={{ cursor: 'pointer', display: 'inline-flex', gap: '0.5rem', alignItems: 'center' }}>
              <Upload size={18} />
              <span>Choose File</span>
              <input ref={fileRef} type="file" accept=".csv,.json,.txt" style={{ display: 'none' }} onChange={handleFile} />
            </label>
          </div>
        </div>
      )}

      {loading === 'parsing' && (
        <div className="card"><div className="card-body" style={{ textAlign: 'center', padding: '2rem' }}><Loader className="spinner" size={24} /><p>Parsing bank feed...</p></div></div>
      )}

      {error && (
        <div className="alert alert--error" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertTriangle size={18} />
          <span>{error}</span>
        </div>
      )}

      {transactions && !summary && (
        <div className="card">
          <div className="card-header"><h3>Parsed Transactions ({transactions.length})</h3></div>
          <div className="card-body" style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Type</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t, i) => (
                  <tr key={i}>
                    <td>{t.date}</td>
                    <td>{t.description}</td>
                    <td style={{ textAlign: 'right' }}>${t.amount?.toFixed(2)}</td>
                    <td><span className={`badge badge--${t.type === 'credit' ? 'success' : 'warning'}`}>{t.type}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="card-footer" style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button className="btn btn--outline" onClick={handleReset}>Cancel</button>
            <button className="btn btn--primary" onClick={handleReconcile} disabled={loading === 'reconciling'}>
              {loading === 'reconciling' ? <><Loader className="spinner" size={16} /> Reconciling...</> : 'Reconcile & Generate Report'}
            </button>
          </div>
        </div>
      )}

      {loading === 'reconciling' && (
        <div className="card"><div className="card-body" style={{ textAlign: 'center', padding: '2rem' }}><Loader className="spinner" size={24} /><p>Reconciling transactions...</p></div></div>
      )}

      {summary && (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle size={20} style={{ color: '#16a34a' }} />
            <h3>Reconciliation Complete</h3>
          </div>
          <div className="card-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
              <div className="stat-card"><div className="stat-value">{summary.total || 0}</div><div className="stat-label">Total Transactions</div></div>
              <div className="stat-card"><div className="stat-value">{summary.matched || 0}</div><div className="stat-label">Matched</div></div>
              <div className="stat-card"><div className="stat-value">{summary.fuzzy || 0}</div><div className="stat-label">Fuzzy Match</div></div>
              <div className="stat-card"><div className="stat-value">{summary.unmatched || 0}</div><div className="stat-label">Unmatched</div></div>
            </div>
          </div>
          <div className="card-footer" style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button className="btn btn--outline" onClick={handleReset}>Start Over</button>
            <button className="btn btn--primary" onClick={handleDownload}><Download size={18} /> Download Excel Report</button>
          </div>
        </div>
      )}
    </div>
  )
}
