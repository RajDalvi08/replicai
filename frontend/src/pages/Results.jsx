import { getRuns } from '../data'
import ComparisonChart from '../components/chart/ComparisonChart'
import MetricCard from '../components/ui/MetricCard'
import SectionHeader from '../components/ui/SectionHeader'
import BrutalCard from '../components/ui/BrutalCard'

export default function Results() {
  const runs = getRuns()

  return (
    <section className="page">
      <div className="page-kicker">07 / COMPARISON</div>
      <h1 className="page-title">PAPER VS REPRODUCED</h1>
      <div className="grid-metrics">
        <MetricCard label="PAPER" value={runs.paperResult} suffix="%" />
        <MetricCard label="REPRODUCED" value={runs.mean} suffix="%" tone="ok" />
        <MetricCard label="DIFFERENCE" value={runs.gap} suffix=" pp" tone="warn" />
        <MetricCard label="MEAN" value={runs.mean} suffix="%" />
        <MetricCard label="STD" value={runs.std} suffix="%" />
        <MetricCard label="RUNS" value={runs.runCount} />
      </div>
      <SectionHeader title="EXECUTION SPREAD" meta="84.1 / 84.4 / 84.2" />
      <BrutalCard>
        <ComparisonChart data={runs.comparison} />
      </BrutalCard>
    </section>
  )
}
