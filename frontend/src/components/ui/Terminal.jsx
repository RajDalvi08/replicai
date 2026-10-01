export default function Terminal({ lines }) {
  return (
    <pre className="terminal">
      {lines.map((line, index) => (
        <div key={`${line}-${index}`} className={line.startsWith('$') ? 'prompt' : ''}>
          {line}
        </div>
      ))}
    </pre>
  )
}
