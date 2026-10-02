import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useExperiment } from '../experiment'
import { getExperiment } from '../data'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import MetricCard from '../components/ui/MetricCard'
import ProgressBar from '../components/ui/ProgressBar'
import SectionHeader from '../components/ui/SectionHeader'
import StatusBadge from '../components/ui/StatusBadge'

function fmt(value, suffix = '') {
  return value === null || value === undefined ? '—' : `${value}${suffix}`
}

export default function ExperimentDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { selectedExperimentId, setSelectedExperimentId } = useExperiment()
  const experiment = getExperiment(id || selectedExperimentId)

  useEffect(() => {
    if (id && id !== selectedExperimentId) {
      setSelectedExperimentId(id)
    }
  }, [id, selectedExperimentId, setSelectedExperimentId])

  const paperBatch = experiment.parameters?.batchSize?.paper ?? experiment.paperConfig?.batchSize ?? null
  const codeBatch = experiment.parameters?.batchSize?.code ?? experiment.codeConfig?.batchSize ?? null
  const mismatch =
    paperBatch !== null && codeBatch !== null && Number(paperBatch) !== Number(codeBatch)

  const breakdownEntries = Object.entries(experiment.readinessBreakdown || {}).map(([key, value]) => {
    const label = key.replace(/([A-Z])/g, ' $1').replace(/^./, (c) => c.toUpperCase())
    return { label, value: Number(value) || 0 }
  })

  const diffKeys = Array.from(
    new Set([
      ...Object.keys(experiment.paperConfig || {}),
      ...Object.keys(experiment.codeConfig || {}),
    ]),
  )
  const primaryDiffKey = diffKeys.find(
    (key) =>
      String(experiment.paperConfig?.[key]) !== String(experiment.codeConfig?.[key]),
  ) || (diffKeys[0] ?? 'batchSize')

  return (
    <section className="page">
      <div className="page-kicker">04 / DETAILS</div>
      <h1 className="page-title">EXPERIMENT {experiment.id}</h1>
      <div className="toolbar">
        <Button variant="ghost" onClick={() => navigate('/experiments')}>
          BACK TO EXPERIMENTS
        </Button>
      </div>
      <div className="grid-metrics">
        <MetricCard label="STATUS" value={experiment.status} tone="ok" />
        <MetricCard label="READINESS" value={experiment.readiness} suffix="%" tone="accent" />
        <MetricCard label="PAPER METRIC" value={fmt(experiment.paperMetric, '%')} />
        <MetricCard label="REPRODUCED" value={fmt(experiment.reproduced, '%')} tone="ok" />
        <MetricCard label="GAP" value={fmt(experiment.gap, ' pp')} tone="warn" />
        <article className="metric-card">
          <div className="metric-label">STATE</div>
          <div style={{ marginTop: 10 }}>
            <StatusBadge status={experiment.reproducibility || experiment.status} />
          </div>
        </article>
      </div>

      <SectionHeader title="EXPERIMENT SUMMARY" meta={experiment.name} />
      <BrutalCard>
        <p className="page-copy" style={{ margin: 0 }}>
          {experiment.summary}
        </p>
      </BrutalCard>

      <div className="split">
        <div>
          <SectionHeader title="PARAMETERS" />
          <BrutalCard>
            <div className="kv"><span>Dataset</span><strong>{experiment.parameters.dataset}</strong></div>
            <div className="kv"><span>Model</span><strong>{experiment.parameters.model}</strong></div>
            <div className="kv"><span>Optimizer</span><strong>{experiment.parameters.optimizer}</strong></div>
            <div className="kv"><span>Learning Rate</span><strong>{experiment.parameters.learningRate}</strong></div>
            <div className="kv"><span>Epochs</span><strong>{experiment.parameters.epochs}</strong></div>
            <div className="kv"><span>Batch Size</span><strong>{fmt(codeBatch)}</strong></div>
            <div className="kv"><span>Seed</span><strong>{experiment.parameters.seed}</strong></div>
          </BrutalCard>
        </div>
        <div>
          <SectionHeader title="READINESS BREAKDOWN" />
          <BrutalCard>
            {breakdownEntries.map((item) => (
              <div key={item.label} style={{ marginBottom: 12 }}>
                <div className="kv" style={{ border: 0, paddingBottom: 4 }}>
                  <span>{item.label}</span>
                  <strong>{item.value}%</strong>
                </div>
                <ProgressBar value={item.value} />
              </div>
            ))}
          </BrutalCard>
        </div>
      </div>

      <SectionHeader title="PAPER CONFIGURATION vs CODE CONFIGURATION" />
      <div className={`diff-row ${mismatch || String(experiment.paperConfig?.[primaryDiffKey]) !== String(experiment.codeConfig?.[primaryDiffKey]) ? 'mismatch' : ''}`}>
        <div>
          <div className="metric-label">FIELD</div>
          <strong>{primaryDiffKey.replace(/([A-Z])/g, ' $1').replace(/^./, (c) => c.toUpperCase())}</strong>
        </div>
        <div>
          <div className="metric-label">PAPER</div>
          <strong>{fmt(experiment.paperConfig?.[primaryDiffKey] ?? paperBatch)}</strong>
        </div>
        <div>
          <div className="metric-label">CODE</div>
          <strong>{experiment.codeConfig?.[primaryDiffKey] === undefined ? (codeBatch === null ? 'MISSING' : codeBatch) : experiment.codeConfig[primaryDiffKey]}</strong>
        </div>
      </div>
      <SectionHeader title="NEXT STEP" meta="05 / PROVENANCE" />
      <BrutalCard>
        <div className="kv" style={{ border: 0, padding: 0 }}>
          <span>Pipeline</span>
          <strong>EXPERIMENT → EVIDENCE → EXECUTION → COMPARISON</strong>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/evidence')}>OPEN EVIDENCE GRAPH</Button>
          <Button variant="ghost" onClick={() => navigate('/execution')}>RUN IN SANDBOX</Button>
        </div>
      </BrutalCard>
    </section>
  )
}
