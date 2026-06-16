import { useEffect, useState } from 'react'
import { api, formatDateTime } from '../api.js'

export default function ExportExcel() {
  const [approved, setApproved] = useState([])
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState(false)
  const [lastExport, setLastExport] = useState(null)

  const load = async () => {
    try {
      const data = await api.listInvoices({ status: 'approved', limit: 500 })
      setApproved(data)
    } catch (err) {
      setError(err.message || 'Failed to load approved invoices.')
    }
  }
  useEffect(() => { load() }, [])

  const onExport = async () => {
    setError(''); setDownloading(true)
    try {
      const res = await fetch(api.exportExcelUrl())
      if (!res.ok) {
        let msg = `HTTP ${res.status}`
        try { const j = await res.json(); msg = j.detail || msg } catch (_) {}
        throw new Error(msg)
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `officepilot_approved_${new Date().toISOString().replace(/[:.]/g, '-')}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      setLastExport(new Date())
    } catch (err) {
      setError(err.message || 'Export failed.')
    } finally { setDownloading(false) }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Export to Excel</h2>
      </div>

      {error && <div className="alert error">{error}</div>}
      {lastExport && (
        <div className="alert success">
          Export generated at {formatDateTime(lastExport)}. The download contains only <strong>approved</strong> invoices.
        </div>
      )}

      <div className="card">
        <p>
          Generate a single <code>.xlsx</code> file containing every invoice whose status is
          <strong> approved</strong>. Pending, needs-review, rejected, and duplicate invoices are
          excluded.
        </p>
        <div className="toolbar">
          <button onClick={onExport} disabled={downloading || approved.length === 0}>
            {downloading ? 'Generating…' : `Download Excel (${approved.length} rows)`}
          </button>
          <button className="secondary" onClick={load}>Refresh count</button>
        </div>
        {approved.length === 0 && (
          <div className="alert info" style={{ marginTop: 12 }}>
            No approved invoices yet. Approve one or more invoices on the Review Queue first.
          </div>
        )}
      </div>
    </div>
  )
}
