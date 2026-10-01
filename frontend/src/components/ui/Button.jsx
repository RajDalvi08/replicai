export default function Button({ children, variant = 'primary', block = false, ...props }) {
  const className = `btn ${variant === 'ghost' ? 'ghost' : ''} ${block ? 'block' : ''}`
  return (
    <button type="button" className={className} {...props}>
      {children}
    </button>
  )
}
