/**
 * Small badge that shows whether an invoice came from a manual upload or
 * an email sync (Phase 2).
 */
export default function SourceBadge({ source, emailImportId }) {
  if (source === 'email') {
    return (
      <span
        className="badge"
        style={{ background: '#e3eaf2', color: '#2855a0' }}
        title={emailImportId ? `Email import #${emailImportId}` : 'Imported from email'}
      >
        Email
      </span>
    )
  }
  return (
    <span
      className="badge"
      style={{ background: '#eef2f7', color: '#5b6472' }}
      title="Manually uploaded"
    >
      Upload
    </span>
  )
}
