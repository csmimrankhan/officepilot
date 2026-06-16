// Tiny before/after diff table. Used by the invoice detail page
// and the version history page to show what changed between two
// versions.

export default function BeforeAfterDiff({ diffs, fromVersion, toVersion }) {
  if (!diffs || diffs.length === 0) {
    return (
      <div className="alert subtle">
        No field changes between v{fromVersion} and v{toVersion}.
      </div>
    )
  }
  return (
    <table className="data-table diff-table">
      <thead>
        <tr>
          <th>Field</th>
          <th>From (v{fromVersion})</th>
          <th>To (v{toVersion})</th>
        </tr>
      </thead>
      <tbody>
        {diffs.map((d) => (
          <tr key={d.field}>
            <td className="field-name">{d.field}</td>
            <td className="diff-from">{_render(d.before)}</td>
            <td className="diff-to">{_render(d.after)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function _render(v) {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'object') {
    return <code className="json-block">{JSON.stringify(v)}</code>
  }
  return String(v)
}
