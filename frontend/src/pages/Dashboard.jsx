import { useNavigate } from 'react-router-dom'
import { useExperiment } from '../experiment'
import { getProject, getRuns } from '../data'
import MetricCard from '../components/ui/MetricCard'
import SectionHeader from '../components/ui/SectionHeader'
import BrutalCard from '../components/ui/BrutalCard'
import StatusBadge from '../components/ui/StatusBadge'
import ProgressBar from '../components/ui/ProgressBar'

const pipelineRoutes = {
  paper: '/dashboard',
  experiments: '/experiments',
  readiness: '/experiments',
  evidence: '/evidence',
  execution: '/execution',
  comparison: '/results',
  'root-cause': '/root-cause',
  report: '/report',
}

function fmtNullable(value, suffix = '') {
  return value === null || value === undefined || value === 'N/A' ? '—' : `${value}${suffix}`
}

export default function Dashboard() {
  const project = getProject()
  const { selectedExperiment } = useExperiment()
  const runs = getRuns(selectedExperiment.id)
  const navigate = useNavigate()
  const hasRepro = typeof selectedExperiment.reproduced === 'number' && Number.isFinite(selectedExperiment.reproduced)
  const gap =
    typeof runs.gap === 'number'
      ? runs.gap
      : typeof selectedExperiment.gap === 'number'
        ? selectedExperiment.gap
        : null

  return (
    <section className="page">
      <div className="page-kicker">02 / PROJECT</div>
      <h1 className="page-title">PROJECT / REPLICAI</h1>
      <p className="page-copy">
        {project.experimentCount} experiments detected from {project.paperFile}. Selected target is {selectedExperiment.id}.
      </p>

      <div className="grid-metrics" style={{ marginTop: 18 }}>
        <MetricCard label="PAPERS" value={project.papers} />
        <MetricCard label="EXPERIMENTS" value={project.experimentCount} />
        <MetricCard label="READINESS" value={selectedExperiment.readiness} suffix="%" tone="accent" />
        <MetricCard
          label="REPRODUCED"
          value={hasRepro ? runs.mean : '—'}
          suffix={hasRepro ? '%' : ''}
          tone={hasRepro ? 'ok' : ''}
        />
        <MetricCard label="PAPER RESULT" value={Number(selectedExperiment.paperMetric).toFixed(2)} suffix="%" />
        <MetricCard
          label="GAP"
          value={gap === null ? '—' : gap}
          suffix={gap === null ? '' : ' pp'}
          tone={gap === null ? '' : 'warn'}
        />
      </div>

      <div className="two-col" style={{ marginTop: 8 }}>
        <div>
          <SectionHeader title="PROJECT PIPELINE" meta={`SELECTED: ${selectedExperiment.id}`} />
          <BrutalCard>
            <div className="pipeline">
              {project.pipeline.map((step) => (
                <button
                  key={step.id}
                  type="button"
                  className={`pipeline-step ${step.complete ? 'done' : ''} ${step.current ? 'current' : ''}`}
                  onClick={() => navigate(pipelineRoutes[step.id] || '/dashboard')}
                >
                  <span />
                  <strong>{step.label}</strong>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted)' }}>
                    {step.current ? 'NOW' : step.complete ? 'DONE' : 'QUEUED'}
                  </span>
                </button>
              ))}
            </div>
          </BrutalCard>
        </div>
        <div>
          <SectionHeader title="SELECTED EXPERIMENT" meta={`${project.experimentCount} DETECTED`} />
          <button
            type="button"
            className="highlight-card"
            onClick={() => navigate(`/experiments/${selectedExperiment.id}`)}
          >
            <div className="page-kicker">HIGHLIGHT</div>
            <h2 style={{ margin: '8px 0 12px', fontSize: 28 }}>Experiment {selectedExperiment.id}</h2>
            <p className="page-copy">{selectedExperiment.name}</p>
            <div className="kv">
              <span>Readiness</span>
              <strong>{selectedExperiment.readiness}%</strong>
            </div>
            <ProgressBar value={selectedExperiment.readiness} />
            <div className="kv">
              <span>Code Match</span>
              <strong>{selectedExperiment.codeMatch}%</strong>
            </div>
            <ProgressBar value={selectedExperiment.codeMatch} />
            <div className="kv">
              <span>Status</span>
              <strong>
                <StatusBadge status={selectedExperiment.status} />
              </strong>
            </div>
            <div className="kv">
              <span>Reproducibility</span>
              <strong>
                <StatusBadge status={selectedExperiment.reproducibility || 'UNDER REVIEW'} />
              </strong>
            </div>
            <div className="kv">
              <span>Paper Metric</span>
              <strong>{Number(selectedExperiment.paperMetric).toFixed(2)}%</strong>
            </div>
            <div className="kv">
              <span>Reproduced</span>
              <strong>{fmtNullable(hasRepro ? runs.mean : null, hasRepro ? '%' : '')}</strong>
            </div>
            <div className="kv">
              <span>Gap</span>
              <strong>{fmtNullable(gap === null ? null : gap, gap === null ? '' : ' pp')}</strong>
            </div>
          </button>
        </div>
      </div>
    </section>
  )
}
