import { useState, useEffect } from 'react'
import { Cpu, Database, AlertCircle, Trash2, RefreshCw } from 'lucide-react'
import { getSystemResources, optimizeClearMemory, optimizeKillExcel } from '../api.js'

function colorForValue(value, thresholds) {
  if (value >= thresholds.red) return 'var(--status-danger, #dc2626)'
  if (value >= thresholds.yellow) return 'var(--status-warning, #f59e0b)'
  return 'var(--status-success, #16a34a)'
}

function StatCard({ title, value, unit, icon: Icon, color, children }) {
  return (
    <div className="resource-card">
      <div className="resource-card-header">
        <div className="resource-card-icon" style={{ color }}>
          <Icon size={22} strokeWidth={1.5} />
        </div>
        <div className="resource-card-title">{title}</div>
      </div>
      <div className="resource-card-value" style={{ color }}>
        {value}
        <span className="resource-card-unit">{unit}</span>
      </div>
      <div className="resource-card-bar">
        <div className="resource-card-bar-fill" style={{ width: `${Math.min(value / 10, 100)}%`, background: color }} />
      </div>
      {children && <div className="resource-card-actions">{children}</div>}
    </div>
  )
}

export default function ResourceMonitor() {
  const [resources, setResources] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionMsg, setActionMsg] = useState('')

  function fetchResources() {
    setLoading(true)
    setError('')
    getSystemResources()
      .then(setResources)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchResources() }, [])

  function handleClearMemory() {
    if (!window.confirm('This will clear the semantic search cache. Invoices will be re-indexed as they are processed. Continue?')) return
    setActionMsg('')
    optimizeClearMemory()
      .then(() => {
        setActionMsg('Semantic memory cache cleared successfully')
        fetchResources()
      })
      .catch(err => setActionMsg('Error: ' + err.message))
  }

  function handleKillExcel() {
    if (!window.confirm('This will close Excel windows that have been idle for over 5 minutes. Continue?')) return
    setActionMsg('')
    optimizeKillExcel()
      .then(res => {
        setActionMsg(res.detail || `Terminated ${res.status} process(es)`)
        fetchResources()
      })
      .catch(err => setActionMsg('Error: ' + err.message))
  }

  if (loading && !resources) {
    return (
      <div className="page-container">
        <div className="page-header"><h1>Resource Monitor</h1></div>
        <div className="loading-state"><div className="spinner" /><p>Loading system resources...</p></div>
      </div>
    )
  }

  if (error && !resources) {
    return (
      <div className="page-container">
        <div className="page-header"><h1>Resource Monitor</h1></div>
        <div className="error-state"><p>{error}</p></div>
      </div>
    )
  }

  const ramColor = colorForValue(resources.python_memory_mb, { yellow: 500, red: 1000 })
  const vectorColor = colorForValue(resources.vector_store_mb, { yellow: 100, red: 500 })

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Resource Monitor</h1>
        <button className="btn btn--icon" onClick={fetchResources} title="Refresh">
          <RefreshCw size={16} strokeWidth={1.5} />
        </button>
      </div>

      {actionMsg && (
        <div className="resource-toast">
          <AlertCircle size={16} strokeWidth={1.5} />
          <span>{actionMsg}</span>
        </div>
      )}

      <div className="resource-grid">
        <StatCard title="App Memory" value={resources.python_memory_mb} unit="MB" icon={Cpu} color={ramColor}>
          <button className="btn btn--outline btn--sm" onClick={handleClearMemory}>
            <Trash2 size={14} strokeWidth={1.5} />
            Clear Vector Memory
          </button>
        </StatCard>

        <StatCard title="Vector DB Size" value={resources.vector_store_mb} unit="MB" icon={Database} color={vectorColor} />

        <StatCard
          title="Orphaned Excel"
          value={resources.orphaned_excel_count}
          unit={resources.orphaned_excel_count === 1 ? 'process' : 'processes'}
          icon={AlertCircle}
          color={resources.orphaned_excel_count > 0 ? 'var(--status-warning, #f59e0b)' : 'var(--status-success, #16a34a)'}
        >
          <button className="btn btn--outline btn--sm" onClick={handleKillExcel} disabled={resources.orphaned_excel_count === 0}>
            <Trash2 size={14} strokeWidth={1.5} />
            Kill Orphaned Excel
          </button>
        </StatCard>
      </div>
    </div>
  )
}
