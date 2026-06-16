import { useState } from 'react'

export default function EmailSearchPreviewCard({
  messages = [],
  resultCount = 0,
  query = '',
  selectedIds = [],
  onSelectionChange,
  onApproveDownload,
  loading,
}) {
  const [checked, setChecked] = useState(selectedIds)
  const [expandedId, setExpandedId] = useState(null)

  if (!messages || messages.length === 0) return null

  const handleToggle = (msgId) => {
    const next = checked.includes(msgId)
      ? checked.filter(id => id !== msgId)
      : [...checked, msgId]
    setChecked(next)
    if (onSelectionChange) onSelectionChange(next)
  }

  const handleSelectAll = () => {
    const all = messages.map(m => m.message_id)
    const next = checked.length === all.length ? [] : all
    setChecked(next)
    if (onSelectionChange) onSelectionChange(next)
  }

  return (
    <div className="card" style={{ padding: '14px', background: '#181825', borderRadius: '12px', borderLeft: '3px solid #a6e3a1' }}>
      <style>{`
        .email-preview-card { font-size: 13px; color: #cdd6f4; }
        .email-preview-title { font-weight: 600; font-size: 14px; margin: 0 0 4px 0; color: #a6e3a1; }
        .email-preview-subtitle { font-size: 12px; color: #a6adc8; margin: 0 0 10px 0; }
        .email-preview-msg { padding: 8px 10px; margin: 6px 0; background: #1e1e2e; border-radius: 8px; cursor: pointer; border: 1px solid transparent; transition: all 0.15s; }
        .email-preview-msg:hover { border-color: #45475a; }
        .email-preview-msg.selected { border-color: #a6e3a1; background: #1e1e2e; }
        .email-preview-msg-header { display: flex; align-items: flex-start; gap: 8px; }
        .email-preview-msg-checkbox { margin-top: 2px; accent-color: #a6e3a1; }
        .email-preview-msg-from { font-weight: 500; color: #89b4fa; }
        .email-preview-msg-subject { font-weight: 500; }
        .email-preview-msg-snippet { font-size: 12px; color: #a6adc8; margin-top: 2px; }
        .email-preview-msg-date { font-size: 11px; color: #6c7086; }
        .email-preview-attachments { margin-top: 6px; padding-top: 6px; border-top: 1px solid #313244; }
        .email-preview-att-title { font-size: 11px; color: #a6adc8; margin-bottom: 4px; }
        .email-preview-att-item { display: flex; align-items: center; gap: 6px; padding: 3px 0; font-size: 12px; }
        .email-preview-att-icon { color: #f9e2af; }
        .email-preview-att-name { color: #cdd6f4; }
        .email-preview-att-size { color: #6c7086; font-size: 11px; }
        .email-preview-badge { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-left: 6px; }
        .email-preview-badge.has-att { background: #a6e3a1; color: #1e1e2e; }
        .email-preview-badge.no-att { background: #45475a; color: #a6adc8; }
        .email-preview-select-all { display: flex; align-items: center; gap: 6px; padding: 4px 0; cursor: pointer; font-size: 12px; color: #89b4fa; }
        .email-preview-select-all input { accent-color: #89b4fa; }
        .email-preview-actions { display: flex; gap: 6px; margin-top: 12px; }
        .email-preview-btn { background: #45475a; color: #cdd6f4; border: none; padding: 8px 14px; border-radius: 8px; cursor: pointer; font-size: 13px; }
        .email-preview-btn:hover { background: #585b70; }
        .email-preview-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .email-preview-btn.primary { background: #a6e3a1; color: #1e1e2e; font-weight: 600; }
        .email-preview-btn.primary:hover { background: #94e2d5; }
      `}</style>
      <div className="email-preview-card">
        <p className="email-preview-title">📧 Email Search Results</p>
        <p className="email-preview-subtitle">{resultCount} message(s) found for query: "{query}"</p>

        <div className="email-preview-select-all" onClick={handleSelectAll}>
          <input type="checkbox" checked={checked.length === messages.length && messages.length > 0} readOnly />
          <span>Select all ({messages.length})</span>
        </div>

        {messages.map((msg) => {
          const isSelected = checked.includes(msg.message_id)
          const isExpanded = expandedId === msg.message_id
          return (
            <div
              key={msg.message_id}
              className={`email-preview-msg ${isSelected ? 'selected' : ''}`}
              onClick={() => setExpandedId(isExpanded ? null : msg.message_id)}
            >
              <div className="email-preview-msg-header">
                <input
                  type="checkbox"
                  className="email-preview-msg-checkbox"
                  checked={isSelected}
                  onClick={(e) => e.stopPropagation()}
                  onChange={() => handleToggle(msg.message_id)}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className="email-preview-msg-from">{msg.from}</span>
                    <span className="email-preview-msg-date">{msg.date ? msg.date.slice(0, 10) : ''}</span>
                  </div>
                  <div className="email-preview-msg-subject">
                    {msg.subject}
                    <span className={`email-preview-badge ${msg.has_attachments ? 'has-att' : 'no-att'}`}>
                      {msg.has_attachments ? `${(msg.attachments || []).length} att` : 'no att'}
                    </span>
                  </div>
                  <div className="email-preview-msg-snippet">{msg.snippet}</div>
                </div>
              </div>
              {isExpanded && msg.attachments && msg.attachments.length > 0 && (
                <div className="email-preview-attachments">
                  <div className="email-preview-att-title">Attachments:</div>
                  {msg.attachments.map((att, i) => (
                    <div key={i} className="email-preview-att-item">
                      <span className="email-preview-att-icon">📎</span>
                      <span className="email-preview-att-name">{att.filename}</span>
                      <span className="email-preview-att-size">({Math.round(att.size / 1024)} KB)</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}

        <div className="email-preview-actions">
          <button
            className="email-preview-btn primary"
            onClick={() => onApproveDownload && onApproveDownload(checked)}
            disabled={checked.length === 0 || loading}
          >
            {loading ? 'Processing...' : `Approve & Download (${checked.length})`}
          </button>
        </div>
      </div>
    </div>
  )
}
