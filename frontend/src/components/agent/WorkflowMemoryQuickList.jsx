export default function WorkflowMemoryQuickList({ workflows = [], onRepeat }) {
  if (!workflows || workflows.length === 0) return null

  return (
    <div className="card" style={{ padding: '12px', background: '#181825', borderRadius: '12px' }}>
      <style>{`
        .wf-quick-title { font-size: 13px; font-weight: 600; color: #f9e2af; margin: 0 0 8px; }
        .wf-quick-item { padding: 8px; background: #1e1e2e; border-radius: 8px; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; gap: 8px; }
        .wf-quick-item-info { flex: 1; min-width: 0; }
        .wf-quick-item-name { font-size: 12px; font-weight: 600; color: #cdd6f4; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .wf-quick-item-meta { font-size: 10px; color: #6c7086; margin-top: 2px; }
        .wf-quick-item-action button { padding: 4px 10px; border: none; border-radius: 4px; font-size: 11px; font-weight: 600; cursor: pointer; background: #45475a; color: #89b4fa; white-space: nowrap; }
        .wf-quick-item-action button:hover { background: #585b70; }
      `}</style>

      <p className="wf-quick-title">Workflow Memory ({workflows.length})</p>

      {workflows.map((wf) => (
        <div key={wf.id} className="wf-quick-item">
          <div className="wf-quick-item-info">
            <div className="wf-quick-item-name">{wf.workflow_name}</div>
            <div className="wf-quick-item-meta">
              {wf.platform_hint || 'Unknown'} · {wf.run_count || 0} run{(wf.run_count || 0) !== 1 ? 's' : ''}
              {wf.last_run_at && ` · Last: ${new Date(wf.last_run_at).toLocaleDateString()}`}
            </div>
          </div>
          <div className="wf-quick-item-action">
            <button onClick={() => onRepeat(wf.id)} title="Repeat workflow">
              Repeat
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
