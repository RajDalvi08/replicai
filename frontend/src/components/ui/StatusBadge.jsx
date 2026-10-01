export default function StatusBadge({ status }) {
  const label = status || 'UNKNOWN'
  return <span className={`badge ${label.split(' ')[0]}`}>{label}</span>
}
