import { useState } from 'react'

const CHECKLIST_STEPS = [
  { key: 'select_folder', label: 'Select local invoice folder' },
  { key: 'dry_run', label: 'Run dry-run simulation' },
  { key: 'preview_files', label: 'Preview detected invoice files' },
  { key: 'approve', label: 'Approve file list' },
  { key: 'create_excel', label: 'Create Daily Invoices Excel' },
  { key: 'verify_total', label: 'Verify calculated total' },
  { key: 'save_workflow', label: 'Save as repeatable workflow' },
]

export default function RealDataTestMode({ onClose }) {
  const [completed, setCompleted] = useState([])
  const [folder, setFolder] = useState('')
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState(null)

  const toggleStep = (key) => {
    setCompleted((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    )
  }

  const handleScan = async () => {
    if (!folder.trim()) return
    setScanning(true)
    try {
      const { api } = await import('../../api.js')
      const result = await api.folderInvoiceScan({ path: folder })
      setScanResult(result)
      setCompleted((prev) => {
        if (!prev.includes('select_folder')) return [...prev, 'select_folder']
        return prev
      })
    } catch (err) {
      setScanResult({ error: err.message })
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="card" style={{ marginBottom: '16px', border: '2px solid var(--warning)', background: '#fffbe6' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
        <div>
          <h3 style={{ margin: 0, color: '#92400e' }}>Real Data Test Mode</h3>
          <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#92400e' }}>
            Real data mode: OfficePilot will process local files only. No external apps will be changed.
          </p>
        </div>
        {onClose && (
          <button className="btn btn--ghost" onClick={onClose} style={{ fontSize: '12px' }}>✕</button>
        )}
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        <input
          type="text"
          className="input"
          placeholder="C:\Users\...\Invoices"
          value={folder}
          onChange={(e) => setFolder(e.target.value)}
          style={{ flex: 1 }}
        />
        <button className="btn btn--primary" onClick={handleScan} disabled={scanning || !folder.trim()}>
          {scanning ? 'Scanning…' : 'Scan Folder'}
        </button>
      </div>

      {scanResult && (
        <div style={{ marginBottom: '12px', padding: '8px 12px', background: '#fef9c3', borderRadius: '6px', fontSize: '13px' }}>
          {scanResult.error ? (
            <span style={{ color: '#dc2626' }}>Error: {scanResult.error}</span>
          ) : (
            <span>Found <strong>{scanResult.file_count || 0}</strong> files in <strong>{scanResult.invoice_count || 0}</strong> invoices</span>
          )}
        </div>
      )}

      <div>
        <p style={{ fontSize: '12px', color: '#92400e', marginBottom: '8px', fontWeight: 600 }}>Test Checklist</p>
        {CHECKLIST_STEPS.map((step) => (
          <label key={step.key} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px 0', fontSize: '13px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={completed.includes(step.key)}
              onChange={() => toggleStep(step.key)}
            />
            <span style={{ textDecoration: completed.includes(step.key) ? 'line-through' : 'none', color: completed.includes(step.key) ? '#6b7280' : '#374151' }}>
              {step.label}
            </span>
          </label>
        ))}
      </div>

      <div style={{ marginTop: '12px', padding: '8px 12px', borderRadius: '6px', fontSize: '12px', color: '#6b7280', background: '#f3f4f6' }}>
        Progress: {completed.length} / {CHECKLIST_STEPS.length} steps
        {completed.length === CHECKLIST_STEPS.length && (
          <span style={{ color: '#16a34a', fontWeight: 600, marginLeft: '8px' }}>✓ All steps completed!</span>
        )}
      </div>
    </div>
  )
}