import { useEffect, useState } from 'react'

function formatValue(value, suffix) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') {
    const abs = Math.abs(value)
    const text = Number.isInteger(abs) ? String(value) : value.toFixed(2)
    return `${text}${suffix}`
  }
  return `${value}${suffix}`
}

export default function MetricCard({ label, value, suffix = '', tone = '' }) {
  const [shown, setShown] = useState(typeof value === 'number' ? 0 : value)

  useEffect(() => {
    if (typeof value !== 'number') {
      setShown(value)
      return undefined
    }
    const start = performance.now()
    const duration = 420
    let frame = 0
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration)
      const next = Number.isInteger(value) ? Math.round(value * t) : value * t
      setShown(next)
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [value])

  const isNumber = typeof value === 'number'
  const display = isNumber ? formatValue(shown, suffix) : formatValue(value, suffix)

  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={isNumber ? undefined : { fontSize: 16, paddingTop: 8 }}>
        {display}
      </div>
    </article>
  )
}
