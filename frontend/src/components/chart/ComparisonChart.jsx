import { useCallback, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useTheme } from '../../theme'

function buildTooltipContent(palette, active, payload, label) {
  if (!active || !payload || payload.length === 0) return null
  const entry = payload[0]
  const value = Number(entry.value).toFixed(2)
  return (
    <div
      style={{
        background: palette.tooltipBg,
        border: `1px solid ${palette.tooltipBorder}`,
        borderRadius: 0,
        color: palette.tooltipText,
        padding: '8px 10px',
        fontFamily: 'JetBrains Mono, ui-monospace, monospace',
        fontSize: 11,
        pointerEvents: 'none',
        boxShadow: 'none',
      }}
    >
      <div style={{ marginBottom: 2, color: palette.tooltipText, fontSize: 11 }}>{label}</div>
      <div style={{ color: palette.tooltipText, fontSize: 11 }}>
        metric: <strong>{value}%</strong>
      </div>
    </div>
  )
}

export default function ComparisonChart({ data }) {
  const { theme } = useTheme()
  const [activeIndex, setActiveIndex] = useState(null)

  const palette = useMemo(() => {
    void theme
    const styles = getComputedStyle(document.documentElement)
    return {
      tick: styles.getPropertyValue('--chart-tick').trim() || '#c8c8c8',
      axis: styles.getPropertyValue('--chart-axis').trim() || '#8a8a8a',
      grid: styles.getPropertyValue('--chart-grid').trim() || '#2a2a2a',
      tooltipBg: styles.getPropertyValue('--chart-tooltip-bg').trim() || '#111',
      tooltipBorder: styles.getPropertyValue('--chart-tooltip-border').trim() || '#c8c8c8',
      tooltipText: styles.getPropertyValue('--text').trim() || '#fff',
    }
  }, [theme])

  const tooltipContent = useCallback(
    ({ active, payload, label }) => buildTooltipContent(palette, active, payload, label),
    [palette],
  )

  const handleCellEnter = useCallback((index) => {
    setActiveIndex(index)
  }, [])

  const handleCellLeave = useCallback(() => {
    setActiveIndex(null)
  }, [])

  return (
    <div style={{ width: '100%', height: 280 }}>
      <ResponsiveContainer>
        <BarChart
          data={data}
          barSize={42}
          onMouseLeave={handleCellLeave}
        >
          <CartesianGrid stroke={palette.grid} vertical={false} />
          <XAxis
            dataKey="name"
            stroke={palette.axis}
            tick={{ fill: palette.tick, fontSize: 12 }}
          />
          <YAxis
            stroke={palette.axis}
            domain={[80, 90]}
            tick={{ fill: palette.tick, fontFamily: 'JetBrains Mono', fontSize: 11 }}
          />
          <Tooltip
            active={activeIndex !== null}
            content={tooltipContent}
            cursor={false}
            isAnimationActive={false}
          />
          <Bar
            dataKey="value"
            isAnimationActive={false}
            activeBar={false}
            onMouseLeave={handleCellLeave}
          >
            {data.map((entry, index) => (
              <Cell
                key={entry.name}
                fill={entry.fill}
                stroke={activeIndex === index ? palette.tooltipText : 'none'}
                strokeWidth={activeIndex === index ? 2 : 0}
                onMouseEnter={() => handleCellEnter(index)}
                onMouseLeave={handleCellLeave}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
