export default function AgentResultCard({ summary, onOpenFile }) {
  if (!summary) return null

  const pnl = summary.pnl_comparison

  return (
    <div className="card" style={{ padding: '12px', background: '#181825', borderRadius: '12px', borderLeft: '3px solid #a6e3a1' }}>
      <style>{`
        .agent-result-title { font-size: 13px; font-weight: 600; color: #a6e3a1; margin: 0 0 8px; }
        .agent-result-text { font-size: 12px; line-height: 1.6; color: #bac2de; margin: 0 0 4px; }
        .agent-result-text.ru { color: #89b4fa; font-size: 11px; }
        .agent-result-stats { display: flex; gap: 16px; margin-top: 8px; flex-wrap: wrap; }
        .agent-result-stat { font-size: 12px; color: #a6adc8; }
        .agent-result-stat strong { color: #cdd6f4; }
        .agent-pnl-table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 12px; }
        .agent-pnl-table td { padding: 4px 8px; color: #bac2de; border-bottom: 1px solid #313244; }
        .agent-pnl-table td:last-child { text-align: right; font-weight: 600; color: #cdd6f4; }
        .agent-pnl-table tr:last-child td { border-bottom: none; }
        .agent-pnl-table .label { color: #a6adc8; }
        .agent-pnl-table .positive { color: #a6e3a1; }
        .agent-pnl-table .negative { color: #f38ba8; }
        .agent-open-file-btn { display: inline-block; margin-top: 8px; padding: 4px 12px; background: #45475a; color: #89b4fa; border: none; border-radius: 6px; font-size: 12px; cursor: pointer; }
        .agent-open-file-btn:hover { background: #585b70; }
      `}</style>

      <p className="agent-result-title">✓ Task Complete</p>

      {summary.summary_english && (
        <p className="agent-result-text">{summary.summary_english}</p>
      )}

      {summary.summary_roman_urdu && (
        <p className="agent-result-text ru">{summary.summary_roman_urdu}</p>
      )}

      {pnl && (
        <table className="agent-pnl-table">
          <tbody>
            <tr>
              <td className="label">Current Month Net Income</td>
              <td>{pnl.current_net_income?.toFixed(2)}</td>
            </tr>
            <tr>
              <td className="label">Previous Month Net Income</td>
              <td>{pnl.previous_net_income?.toFixed(2)}</td>
            </tr>
            <tr>
              <td className="label">Difference</td>
              <td className={pnl.net_income_difference >= 0 ? 'positive' : 'negative'}>
                {pnl.net_income_difference >= 0 ? '+' : ''}{pnl.net_income_difference?.toFixed(2)}
              </td>
            </tr>
            {pnl.net_income_percentage_change != null && (
              <tr>
                <td className="label">Change %</td>
                <td className={pnl.net_income_percentage_change >= 0 ? 'positive' : 'negative'}>
                  {pnl.net_income_percentage_change >= 0 ? '+' : ''}{pnl.net_income_percentage_change?.toFixed(1)}%
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}

      {!pnl && (summary.invoice_count > 0 || summary.total_amount > 0) && (
        <div className="agent-result-stats">
          {summary.invoice_count > 0 && (
            <span className="agent-result-stat">
              Invoices: <strong>{summary.invoice_count}</strong>
            </span>
          )}
          {summary.total_amount > 0 && (
            <span className="agent-result-stat">
              Total: <strong>{summary.total_amount.toFixed(2)}</strong>
            </span>
          )}
        </div>
      )}

      {summary.excel_file_path && (
        <div style={{ marginTop: pnl ? '4px' : '8px' }}>
          <span className="agent-result-stat">
            Excel: <strong style={{ fontSize: '11px', wordBreak: 'break-all' }}>{summary.excel_file_path}</strong>
          </span>
          <button className="agent-open-file-btn" onClick={() => onOpenFile?.(summary.excel_file_path)}>
            Open file
          </button>
        </div>
      )}

      {summary.run && (
        <div style={{ fontSize: '11px', color: '#6c7086', marginTop: '8px' }}>
          {summary.run.completed_at && `Completed: ${new Date(summary.run.completed_at).toLocaleTimeString()}`}
          {summary.run.stopped_at && ` Stopped: ${new Date(summary.run.stopped_at).toLocaleTimeString()}`}
        </div>
      )}
    </div>
  )
}
