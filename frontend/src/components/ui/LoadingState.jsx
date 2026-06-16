export default function LoadingState({ text = 'Loading...' }) {
  return (
    <div className="loading-state">
      <div className="spinner" />
      <p className="subtle">{text}</p>
    </div>
  )
}
