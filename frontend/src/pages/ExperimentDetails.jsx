import { useNavigate, useParams } from 'react-router-dom'
import { getExperiment } from '../data'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import MetricCard from '../components/ui/MetricCard'
import ProgressBar from '../components/ui/ProgressBar'
import SectionHeader from '../components/ui/SectionHeader'
import StatusBadge from '../components/ui/StatusBadge'

export default function ExperimentDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const experiment = getExperiment(id)
  const paperBatch = experiment.parameters.batchSize.paper
  const codeBatch = experiment.parameters.batchSize.code
  const mismatch = paperBatch !== codeBatch

  const breakdown = [
    { label: 'Paper evidence', value: experiment.readinessBreakdown.paperEvidence },
    { label: 'Code evidence', value: experiment.readinessBreakdown.codeEvidence },
    { label: 'Parameter match', value: experiment.readinessBreakdown.parameterMatch },
    { label: 'Dataset match', value: experiment.readinessBreakdown.datasetMatch },
    { label: 'Evaluation match', value: experiment.readinessBreakdown.evaluationMatch },
  ]

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
        <MetricCard label="PAPER METRIC" value={experiment.paperMetric} suffix="%" />
        <MetricCard label="REPRODUCED" value={experiment.reproduced} suffix="%" />
        <MetricCard label="GAP" value={experiment.gap} suffix=" pp" tone="warn" />
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
            <div className="kv"><span>Batch Size</span><strong>{codeBatch ?? '—'}</strong></div>
            <div className="kv"><span>Seed</span><strong>{experiment.parameters.seed}</strong></div>
          </BrutalCard>
        </div>
        <div>
          <SectionHeader title="READINESS BREAKDOWN" />
          <BrutalCard>
            {breakdown.map((item) => (
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
      <div className={`diff-row ${mismatch ? 'mismatch' : ''}`}>
        <div>
          <div className="metric-label">FIELD</div>
          <strong>Batch Size</strong>
        </div>
        <div>
          <div className="metric-label">PAPER</div>
          <strong>{paperBatch}</strong>
        </div>
        <div>
          <div className="metric-label">CODE</div>
          <strong>{codeBatch ?? 'MISSING'}</strong>
        </div>
      </div>
    </section>
  )
}
