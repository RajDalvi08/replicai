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

export default function ComparisonChart({ data }) {
  useTheme()

  const styles = getComputedStyle(document.documentElement)
  const tick = styles.getPropertyValue('--chart-tick').trim() || '#c8c8c8'
  const axis = styles.getPropertyValue('--chart-axis').trim() || '#8a8a8a'
  const grid = styles.getPropertyValue('--chart-grid').trim() || '#2a2a2a'
  const tooltipBg = styles.getPropertyValue('--chart-tooltip-bg').trim() || '#111'
  const tooltipBorder = styles.getPropertyValue('--chart-tooltip-border').trim() || '#c8c8c8'
  const tooltipText = styles.getPropertyValue('--text').trim() || '#fff'

  return (
    <div style={{ width: '100%', height: 280 }}>
      <ResponsiveContainer>
        <BarChart data={data} barSize={42}>
          <CartesianGrid stroke={grid} vertical={false} />
          <XAxis dataKey="name" stroke={axis} tick={{ fill: tick, fontSize: 12 }} />
          <YAxis
            stroke={axis}
            domain={[80, 90]}
            tick={{ fill: tick, fontFamily: 'JetBrains Mono', fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{
              background: tooltipBg,
              border: `1px solid ${tooltipBorder}`,
              borderRadius: 0,
              color: tooltipText,
            }}
            formatter={(value) => [`${Number(value).toFixed(2)}%`, 'metric']}
          />
          <Bar dataKey="value">
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
