export default function ConfidenceBar({ value }) {
  const v = Math.max(0, Math.min(1, Number(value) || 0))
  const pct = Math.round(v * 100)
  return (
    <span title={`Confidence: ${pct}%`}>
      <span className="confidence-bar"><span style={{ width: `${pct}%` }} /></span>
      {pct}%
    </span>
  )
}
