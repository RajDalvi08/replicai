export default function Input({ label, className = '', ...props }) {
  return (
    <label className={`field ${className}`}>
      {label ? <span>{label}</span> : null}
      <input {...props} />
    </label>
  )
}
