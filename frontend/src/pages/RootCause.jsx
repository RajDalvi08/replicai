import { useNavigate } from 'react-router-dom'
import { useExperiment } from '../experiment'
import { getProject, getRootCause, getRuns } from '../data'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import MetricCard from '../components/ui/MetricCard'
import ProgressBar from '../components/ui/ProgressBar'
import SectionHeader from '../components/ui/SectionHeader'
import StatusBadge from '../components/ui/StatusBadge'

export default function RootCause() {
  const { selectedExperiment } = useExperiment()
  const root = getRootCause(selectedExperiment.id)
  const project = getProject()
  const runs = getRuns(selectedExperiment.id)
  const navigate = useNavigate()
  const hasGap = typeof selectedExperiment.gap === 'number' && Number.isFinite(selectedExperiment.gap)

  return (
    <section className="page">
      <div className="page-kicker">08 / DEBUG</div>
      <h1 className="page-title">{selectedExperiment.id} · ROOT CAUSE ANALYSIS</h1>
      <p className="page-copy" style={{ marginBottom: 10 }}>
        {selectedExperiment.summary}
        {' '}
        Reproduction gap between paper ({Number(selectedExperiment.paperMetric).toFixed(2)}%) and reproduced ({runs.mean === 'N/A' ? 'not available' : `${runs.mean}%`})
        is traced to a parameter-level difference between paper claims and checked-out repository configuration.
      </p>
      <div className="grid-metrics">
        <MetricCard label="MAIN FINDING" value={root.title} tone="warn" />
        <MetricCard label="PAPER" value={root.paperValue} />
        <MetricCard label="CODE" value={root.codeValue} tone="warn" />
        <MetricCard label="CONFIDENCE" value={root.confidence} />
        <MetricCard label="GAP" value={hasGap ? `${selectedExperiment.gap} pp` : '—'} />
        <MetricCard label="STATUS" value={<StatusBadge status={selectedExperiment.reproducibility || selectedExperiment.status} />} />
      </div>
      <SectionHeader title="ROOT CAUSE" meta={root.finding} />
      <BrutalCard>
        <p className="page-copy" style={{ margin: 0 }}>
          {root.impact}
        </p>
      </BrutalCard>
      <SectionHeader title="EVIDENCE" />
      <div className="split">
        <BrutalCard>
          <div className="metric-label" style={{ color: 'var(--muted)' }}>PAPER</div>
          <div className="metric-value" style={{ fontSize: 20, color: 'var(--text)' }}>
            {root.evidence.paper}
          </div>
          <ProgressBar value={100} />
          <div className="kv" style={{ marginTop: 8 }}>
            <span>Source</span>
            <strong>{project.paperFile} · §5.1</strong>
          </div>
        </BrutalCard>
        <BrutalCard>
          <div className="metric-label" style={{ color: 'var(--muted)' }}>CODE</div>
          <div className="metric-value" style={{ fontSize: 20, color: 'var(--warning)' }}>
            {root.evidence.code}
          </div>
          <ProgressBar value={50} />
          <div className="kv" style={{ marginTop: 8 }}>
            <span>Source</span>
            <strong>config.yaml · line 17</strong>
          </div>
        </BrutalCard>
      </div>
      <SectionHeader title="EVIDENCE CHAIN" />
      <div className="chain">
        {root.chain.map((item, index) => (
          <span key={item.id} style={{ display: 'contents' }}>
            <button
              type="button"
              className="chain-node"
              style={{ color: 'var(--text)' }}
              onClick={() => navigate('/evidence')}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') navigate('/evidence')
              }}
            >
              {item.label}
            </button>
            {index < root.chain.length - 1 ? <span className="workflow-arrow">↓</span> : null}
          </span>
        ))}
      </div>
      <SectionHeader title="NEXT STEP" meta="09 / EXPORT" />
      <BrutalCard>
        <div className="kv" style={{ border: 0, padding: 0 }}>
          <span>Pipeline</span>
          <strong>ROOT CAUSE → REPORT (EXPORT)</strong>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/report')}>GENERATE REPORT</Button>
          <Button variant="ghost" onClick={() => navigate('/evidence')}>REVIEW EVIDENCE</Button>
        </div>
      </BrutalCard>
    </section>
  )
}
