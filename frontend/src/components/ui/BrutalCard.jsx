export default function BrutalCard({ children, className = '', as: Tag = 'div', ...props }) {
  return (
    <Tag className={`brutal-card ${className}`} {...props}>
      {children}
    </Tag>
  )
}
