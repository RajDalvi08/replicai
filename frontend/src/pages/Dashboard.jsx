import { useNavigate } from 'react-router-dom'
import { getProject, getSelectedExperiment } from '../data'
import MetricCard from '../components/ui/MetricCard'
import SectionHeader from '../components/ui/SectionHeader'
import BrutalCard from '../components/ui/BrutalCard'
import StatusBadge from '../components/ui/StatusBadge'
import ProgressBar from '../components/ui/ProgressBar'

const pipelineRoutes = {
  paper: '/',
  experiments: '/experiments',
  readiness: '/experiments',
  evidence: '/evidence',
  execution: '/execution',
  comparison: '/results',
  'root-cause': '/root-cause',
  report: '/report',
}

export default function Dashboard() {
  const project = getProject()
  const experiment = getSelectedExperiment()
  const navigate = useNavigate()

  return (
    <section className="page">
      <div className="page-kicker">02 / PROJECT</div>
      <h1 className="page-title">PROJECT / REPLICAI</h1>
      <p className="page-copy">
        {project.experimentCount} experiments detected from {project.paperFile}. Selected target is {experiment.id}.
      </p>

      <div className="grid-metrics" style={{ marginTop: 18 }}>
        <MetricCard label="PAPERS" value={project.papers} />
        <MetricCard label="EXPERIMENTS" value={project.experimentCount} />
        <MetricCard label="READINESS" value={project.readiness} suffix="%" tone="accent" />
        <MetricCard label="REPRODUCED" value={project.reproduced} suffix="%" tone="ok" />
        <MetricCard label="PAPER RESULT" value={project.paperResult} suffix="%" />
        <MetricCard label="GAP" value={project.gap} suffix=" pp" tone="warn" />
      </div>

      <div className="two-col" style={{ marginTop: 8 }}>
        <div>
          <SectionHeader title="PROJECT PIPELINE" meta="CURRENT: ROOT CAUSE" />
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
          <button type="button" className="highlight-card" onClick={() => navigate(`/experiments/${experiment.id}`)}>
            <div className="page-kicker">HIGHLIGHT</div>
            <h2 style={{ margin: '8px 0 12px', fontSize: 28 }}>Experiment {experiment.id}</h2>
            <p className="page-copy">{experiment.name}</p>
            <div className="kv">
              <span>Readiness</span>
              <strong>{experiment.readiness}%</strong>
            </div>
            <ProgressBar value={experiment.readiness} />
            <div className="kv">
              <span>Status</span>
              <strong>
                <StatusBadge status={experiment.status} />
              </strong>
            </div>
            <div className="kv">
              <span>Reproducibility</span>
              <strong>
                <StatusBadge status={experiment.reproducibility || 'UNDER REVIEW'} />
              </strong>
            </div>
          </button>
        </div>
      </div>
    </section>
  )
}
