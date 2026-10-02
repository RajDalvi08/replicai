import { useNavigate } from 'react-router-dom'
import { useExperiment } from '../experiment'
import { getRuns } from '../data'
import ComparisonChart from '../components/chart/ComparisonChart'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import MetricCard from '../components/ui/MetricCard'
import SectionHeader from '../components/ui/SectionHeader'

function fmt(value, suffix = '') {
  return value === 'N/A' || value === null || value === undefined ? '—' : `${value}${suffix}`
}

export default function Results() {
  const { selectedExperiment } = useExperiment()
  const runs = getRuns(selectedExperiment.id)
  const navigate = useNavigate()
  const runValues = runs.items.map((item) => item.accuracy.replace('%', '')).join(' / ') || '—'

  return (
    <section className="page">
      <div className="page-kicker">07 / COMPARISON</div>
      <h1 className="page-title">{selectedExperiment.id} · PAPER VS REPRODUCED</h1>
      <div className="grid-metrics">
        <MetricCard label="PAPER" value={Number(runs.paperResult).toFixed(2)} suffix="%" />
        <MetricCard label="REPRODUCED" value={fmt(runs.mean, runs.mean === 'N/A' ? '' : '%')} tone={runs.mean === 'N/A' ? '' : 'ok'} />
        <MetricCard label="DIFFERENCE" value={fmt(runs.gap, runs.gap === 'N/A' ? '' : ' pp')} tone={runs.gap === 'N/A' ? '' : 'warn'} />
        <MetricCard label="MEAN" value={fmt(runs.mean, runs.mean === 'N/A' ? '' : '%')} />
        <MetricCard label="STD" value={fmt(runs.std, runs.std === 'N/A' ? '' : '%')} />
        <MetricCard label="RUNS" value={runs.runCount || 0} />
      </div>
      <SectionHeader title="EXECUTION SPREAD" meta={runValues} />
      <BrutalCard>
        <ComparisonChart data={runs.comparison} />
      </BrutalCard>
      <SectionHeader title="NEXT STEP" meta="08 / DEBUG" />
      <BrutalCard>
        <div className="kv" style={{ border: 0, padding: 0 }}>
          <span>Signal</span>
          <strong>Reproduction gap of {runs.gap} pp · inspect root cause before export.</strong>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/root-cause')}>ROOT CAUSE ANALYSIS</Button>
          <Button variant="ghost" onClick={() => navigate('/report')}>SKIP TO REPORT</Button>
        </div>
      </BrutalCard>
    </section>
  )
}
