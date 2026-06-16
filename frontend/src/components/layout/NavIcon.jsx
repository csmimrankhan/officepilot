export default function NavIcon({ icon: Icon, size = 18, strokeWidth = 1.9 }) {
  return (
    <span className="nav-icon">
      <Icon size={size} strokeWidth={strokeWidth} />
    </span>
  )
}