import { useState } from 'react'
import { Edit3, Check, X, CloudUpload } from 'lucide-react'
import { api } from '../../api.js'

export default function BackgroundResultCard({ task, onOpenFile, onPushToQuickBooks }) {
  if (!task) return null

  const result = task.result_summary_json
  const command = task.command || ''
  const isDone = task.status === 'completed'
  const isFailed = task.status === 'failed'

  const formatMoney = (val) => {
    if (val == null) return '—'
    const n = Number(val)
    if (Number.isNaN(n)) return String(val)
    try {
      return new Intl.NumberFormat('en-US', {
        style: 'currency', currency: 'USD', maximumFractionDigits: 2,
      }).format(n)
    } catch {
      return `$${n.toFixed(2)}`
    }
  }

  return (
    <div className="card" style={{
      padding: '12px', background: '#f8fafc', borderRadius: 10,
      border: `1px solid ${isDone ? '#bbf7d0' : '#fecaca'}`,
      borderLeft: `3px solid ${isDone ? '#16a34a' : '#dc2626'}`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        {isDone ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        )}
        <span style={{ fontWeight: 600, fontSize: 14, color: '#1e293b' }}>
          {isDone ? 'Background Task Complete' : 'Background Task Failed'}
        </span>
        <span className={`badge badge--${isDone ? 'success' : 'danger'}`} style={{ fontSize: 10 }}>
          {task.status}
        </span>
        {(result?.pivot_rows != null || result?.chart_type != null) && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, fontWeight: 500, padding: '1px 6px', borderRadius: 4, background: '#1e3a5f', color: '#74c7ec' }}>
            Advanced Excel
          </span>
        )}
      </div>

      {command && (
        <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8, fontStyle: 'italic' }}>
          "{command.length > 60 ? command.slice(0, 60) + '...' : command}"
        </div>
      )}

      {isDone && result && (
        <div style={{ fontSize: 13, lineHeight: 1.6, color: '#334155' }}>
          {result.invoice_count != null && (
            <div>Invoices processed: <strong>{result.invoice_count}</strong></div>
          )}
          {result.total_sum != null && (
            <div>Total sum: <strong>{formatMoney(result.total_sum)}</strong></div>
          )}
          {result.average_amount != null && (
            <div>Average: <strong>{formatMoney(result.average_amount)}</strong></div>
          )}
          {result.largest_amount != null && result.largest_vendor && (
            <CorrectThisButton vendor={result.largest_vendor} amount={result.largest_amount} prefix="Largest" />
          )}
          {result.smallest_amount != null && result.smallest_vendor && (
            <CorrectThisButton vendor={result.smallest_vendor} amount={result.smallest_amount} prefix="Smallest" />
          )}
          {result.summary_english && (
            <div style={{ marginTop: 8, fontSize: 12, color: '#475569' }}>{result.summary_english}</div>
          )}
          {result.excel_file_path && (
            <div style={{ marginTop: 8 }}>
              <button
                className="btn btn--sm btn--primary"
                onClick={() => onOpenFile?.(result.excel_file_path)}
                type="button"
              >
                Open Excel File
              </button>
            </div>
          )}
          {(result.total_sum != null || result.total_amount != null) && (
            <div style={{ marginTop: 8 }}>
              <PushToQuickBooksButton
                vendorName={result.largest_vendor || 'Unknown Vendor'}
                totalAmount={result.total_sum ?? result.total_amount ?? 0}
                onPush={onPushToQuickBooks}
              />
            </div>
          )}
        </div>
      )}

      {isFailed && task.error_message && (
        <div style={{ fontSize: 12, color: '#dc2626', marginTop: 4 }}>
          Error: {task.error_message.length > 120 ? task.error_message.slice(0, 120) + '...' : task.error_message}
        </div>
      )}

      {task.completed_at && (
        <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 8 }}>
          Completed: {new Date(task.completed_at).toLocaleString()}
        </div>
      )}
    </div>
  )
}

function CorrectThisButton({ vendor, amount, prefix }) {
  const [showForm, setShowForm] = useState(false)
  const [category, setCategory] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const handleSave = async () => {
    if (!category.trim()) return
    setSaving(true)
    try {
      await api.createCorrection({
        trigger_vendor: vendor,
        correct_category: category.trim(),
        notes: `${prefix} vendor (${formatMoney(amount)})`,
      })
      setSaved(true)
      setTimeout(() => {
        setShowForm(false)
        setSaved(false)
        setCategory('')
      }, 2000)
    } catch {
      // silently fail
    } finally {
      setSaving(false)
    }
  }

  const formatMoney = (val) => {
    const n = Number(val)
    if (Number.isNaN(n)) return String(val)
    try {
      return new Intl.NumberFormat('en-US', {
        style: 'currency', currency: 'USD', maximumFractionDigits: 2,
      }).format(n)
    } catch {
      return `$${n.toFixed(2)}`
    }
  }

  if (saved) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
        <span style={{ fontSize: 13, color: '#334155' }}>
          {prefix}: <strong>{vendor}</strong> — {formatMoney(amount)}
        </span>
        <span style={{ fontSize: 11, color: '#16a34a', fontWeight: 600 }}>Rule saved ✓</span>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
        <span style={{ fontSize: 13, color: '#334155' }}>
          {prefix}: <strong>{vendor}</strong> — {formatMoney(amount)}
        </span>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            type="button"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 3,
              fontSize: 11, color: '#6366f1', background: 'none', border: '1px solid #c7d2fe',
              borderRadius: 5, padding: '1px 6px', cursor: 'pointer',
            }}
          >
            <Edit3 size={12} />
            Correct This
          </button>
        )}
      </div>
      {showForm && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, marginLeft: 0 }}>
          <span style={{ fontSize: 12, color: '#475569', whiteSpace: 'nowrap' }}>
            Correct category for <strong>{vendor}</strong>:
          </span>
          <input
            type="text"
            value={category}
            onChange={e => setCategory(e.target.value)}
            placeholder="e.g. Software"
            style={{
              flex: 1, minWidth: 120, padding: '3px 8px', fontSize: 12,
              border: '1px solid #cbd5e1', borderRadius: 5,
            }}
            onKeyDown={e => { if (e.key === 'Enter') handleSave() }}
          />
          <button
            onClick={handleSave}
            disabled={saving || !category.trim()}
            type="button"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 3,
              fontSize: 11, color: '#fff', background: '#6366f1', border: 'none',
              borderRadius: 5, padding: '3px 8px', cursor: 'pointer', opacity: saving || !category.trim() ? 0.6 : 1,
            }}
          >
            <Check size={12} />
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button
            onClick={() => { setShowForm(false); setCategory('') }}
            type="button"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 3,
              fontSize: 11, color: '#64748b', background: 'none', border: '1px solid #cbd5e1',
              borderRadius: 5, padding: '3px 8px', cursor: 'pointer',
            }}
          >
            <X size={12} />
            Cancel
          </button>
        </div>
      )}
    </div>
  )
}

function PushToQuickBooksButton({ vendorName, totalAmount, onPush }) {
  const [sending, setSending] = useState(false)

  const handleClick = async () => {
    if (!onPush) return
    setSending(true)
    try {
      await onPush({
        vendor_name: vendorName,
        total_amount: totalAmount,
        line_items: [{ description: 'Invoice processing', amount: totalAmount }],
        due_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
      })
    } catch {
    } finally {
      setSending(false)
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={sending}
      type="button"
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        fontSize: 12, color: '#fff', background: '#0b5e9e', border: 'none',
        borderRadius: 6, padding: '6px 12px', cursor: sending ? 'not-allowed' : 'pointer',
        opacity: sending ? 0.6 : 1,
      }}
    >
      <CloudUpload size={14} />
      {sending ? 'Pushing...' : 'Push to QuickBooks'}
    </button>
  )
}
