export default function AgentApprovalCard({ planId, onApprove, onReject, loading }) {
  return (
    <div className="card" style={{ padding: '12px', background: '#181825', borderRadius: '12px' }}>
      <style>{`
        .agent-approval-title { font-size: 13px; font-weight: 600; color: #f9e2af; margin: 0 0 8px; }
        .agent-approval-actions { display: flex; gap: 8px; flex-wrap: wrap; }
        .agent-approval-actions button { padding: 6px 14px; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; }
        .agent-approval-actions button:disabled { opacity: 0.5; cursor: default; }
        .btn-approve-dry { background: #45475a; color: #89b4fa; }
        .btn-approve-dry:hover:not(:disabled) { background: #585b70; }
        .btn-approve-live { background: #a6e3a1; color: #1e1e2e; }
        .btn-approve-live:hover:not(:disabled) { background: #94e2d5; }
        .btn-reject { background: #45475a; color: #f38ba8; }
        .btn-reject:hover:not(:disabled) { background: #585b70; }
      `}</style>

      <p className="agent-approval-title">Review & Approve Plan</p>
      <div className="agent-approval-actions">
        <button className="btn-approve-dry" onClick={() => onApprove(planId, 'dry_run')} disabled={loading}>
          {loading ? '...' : 'Approve (Dry-Run)'}
        </button>
        <button className="btn-approve-live" onClick={() => onApprove(planId, 'live')} disabled={loading}>
          {loading ? '...' : 'Approve & Execute'}
        </button>
        <button className="btn-reject" onClick={() => onReject(planId)} disabled={loading}>
          Reject
        </button>
      </div>
    </div>
  )
}
