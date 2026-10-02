import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getReadiness } from '../api/client'
import { useExperiment } from '../experiment'
import MetricCard from '../components/ui/MetricCard'
import SectionHeader from '../components/ui/SectionHeader'
import BrutalCard from '../components/ui/BrutalCard'
import StatusBadge from '../components/ui/StatusBadge'
import ProgressBar from '../components/ui/ProgressBar'

const pipelineRoutes = {
  paper: '/',
  experiments: '/experiments',
  readiness: '/dashboard',
  evidence: '/evidence',
  execution: '/execution',
  comparison: '/results',
  'root-cause': '/root-cause',
  report: '/report',
}

const pipeline = [
  { id: 'paper', label: 'Paper analysis' },
  { id: 'experiments', label: 'Experiments' },
  { id: 'readiness', label: 'Readiness' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'execution', label: 'Execution' },
  { id: 'comparison', label: 'Comparison' },
  { id: 'root-cause', label: 'Explanation' },
  { id: 'report', label: 'Report' },
]

function display(value) {
  return value === null || value === undefined || value === '' ? 'Not available' : String(value)
}

export default function Dashboard() {
  const navigate = useNavigate()
  const {
    paperId,
    paperAnalysis,
    experiments = [],
    selectedExperiment,
    selectedExperimentId,
    selectedExperimentDatabaseId,
    repositoryId,
    codeAnalysis,
    run,
    validation,
  } = useExperiment()
  const [readinessReport, setReadinessReport] = useState(codeAnalysis?.readiness || null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!repositoryId) return
    let active = true
    getReadiness(repositoryId, selectedExperimentDatabaseId)
      .then((response) => {
        if (active) setReadinessReport(response.readiness)
      })
      .catch((requestError) => {
        if (active) setError(requestError.message || 'Unable to load readiness.')
      })
    return () => {
      active = false
    }
  }, [repositoryId, selectedExperimentDatabaseId])

  const reported = selectedExperiment
    ? Object.values(selectedExperiment.reported_results || {})[0]
    : null
  const reportedValue = reported?.value ?? reported
  const readiness = readinessReport?.overall_score
  const currentStep = !paperId ? 'paper' : !experiments.length ? 'experiments' : !repositoryId ? 'readiness' : !validation ? 'execution' : 'comparison'

  return (
    <section className="page">
      <div className="page-kicker">02 / PROJECT</div>
      <h1 className="page-title">PROJECT / REPLICAI</h1>
      <p className="page-copy">
        {paperAnalysis?.filename || 'No paper analyzed'} · {experiments.length} extracted experiments · selected {selectedExperimentId || 'none'}.
      </p>
      {error ? <div className="field-hint error">{error}</div> : null}

      <div className="grid-metrics" style={{ marginTop: 18 }}>
        <MetricCard label="PAPERS" value={paperId ? 1 : 0} />
        <MetricCard label="EXPERIMENTS" value={experiments.length} />
        <MetricCard label="READINESS" value={readiness === undefined ? 'Not available' : `${readiness.toFixed(1)}%`} tone="accent" />
        <MetricCard label="LATEST RUN" value={run?.status || 'Not run'} />
        <MetricCard label="PAPER RESULT" value={display(reportedValue)} />
        <MetricCard label="VALIDATION" value={validation?.status || 'Not validated'} />
      </div>

      <div className="two-col" style={{ marginTop: 8 }}>
        <div>
          <SectionHeader title="PROJECT PIPELINE" meta={`SELECTED: ${selectedExperimentId || 'NONE'}`} />
          <BrutalCard>
            <div className="pipeline">
              {pipeline.map((step) => {
                const completed =
                  step.id === 'paper' ? Boolean(paperId) :
                    step.id === 'experiments' ? experiments.length > 0 :
                      step.id === 'readiness' ? Boolean(readinessReport) :
                        step.id === 'evidence' ? Boolean(codeAnalysis?.mappings?.length) :
                          step.id === 'execution' ? run?.status === 'completed' :
                            step.id === 'comparison' || step.id === 'root-cause' || step.id === 'report'
                              ? Boolean(validation)
                              : false
                return (
                  <button
                    key={step.id}
                    type="button"
                    className={`pipeline-step ${completed ? 'done' : ''} ${step.id === currentStep ? 'current' : ''}`}
                    onClick={() => navigate(pipelineRoutes[step.id])}
                  >
                    <span />
                    <strong>{step.label}</strong>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--muted)' }}>
                      {step.id === currentStep ? 'NOW' : completed ? 'DONE' : 'QUEUED'}
                    </span>
                  </button>
                )
              })}
            </div>
          </BrutalCard>
        </div>
        <div>
          <SectionHeader title="SELECTED EXPERIMENT" meta={`${experiments.length} DETECTED`} />
          {selectedExperiment ? (
            <>
              <button
                type="button"
                className="highlight-card"
                onClick={() => navigate(`/experiments/${selectedExperimentId}`)}
              >
                <div className="page-kicker">{selectedExperimentId}</div>
                <h2 style={{ margin: '8px 0 12px', fontSize: 28 }}>{display(selectedExperiment.title)}</h2>
                <p className="page-copy">{display(selectedExperiment.description)}</p>
                <div className="kv"><span>Readiness</span><strong>{readiness === undefined ? 'Not available' : `${readiness.toFixed(1)}%`}</strong></div>
                {readiness !== undefined ? <ProgressBar value={readiness} /> : null}
                <div className="kv"><span>Repository</span><strong>{codeAnalysis?.repository?.url || 'Not analyzed'}</strong></div>
                <div className="kv"><span>Analysis status</span><strong><StatusBadge status={codeAnalysis?.repository?.analysis_status || 'NOT ANALYZED'} /></strong></div>
                <div className="kv"><span>Paper metric</span><strong>{display(selectedExperiment.metric)}</strong></div>
                <div className="kv"><span>Paper value</span><strong>{display(reportedValue)}</strong></div>
              </button>
              {codeAnalysis ? (
                <>
                  <SectionHeader title="CODE INTELLIGENCE" meta={`${codeAnalysis.repository?.python_file_count ?? 0} PYTHON FILES`} />
                  <BrutalCard>
                    <div className="kv"><span>Entry points</span><strong>{codeAnalysis.entry_points?.map((file) => file.path).join(', ') || 'Not detected'}</strong></div>
                    <div className="kv">
                      <span>Detected model</span>
                      <strong>{display(codeAnalysis.code_parameters?.find((item) => item.name === 'model')?.value)}</strong>
                    </div>
                    <div className="kv">
                      <span>Training pipeline</span>
                      <strong>
                        {codeAnalysis.pipeline?.stages?.map((stage) => `${stage.name}: ${stage.status}`).join(' · ') || 'Not detected'}
                      </strong>
                    </div>
                    <div className="kv"><span>Optimizers</span><strong>{codeAnalysis.optimizers?.map((item) => item.name).join(', ') || 'Not detected'}</strong></div>
                    <div className="kv"><span>Schedulers</span><strong>{codeAnalysis.schedulers?.map((item) => item.name).join(', ') || 'Not detected'}</strong></div>
                    <div className="kv"><span>Loss functions</span><strong>{codeAnalysis.loss_functions?.map((item) => item.name).join(', ') || 'Not detected'}</strong></div>
                    <div className="kv"><span>Metrics</span><strong>{codeAnalysis.metrics?.map((item) => item.name).join(', ') || 'Not detected'}</strong></div>
                    <div className="kv"><span>Dependencies</span><strong>{codeAnalysis.dependencies?.join(', ') || 'Not detected'}</strong></div>
                    {codeAnalysis.warnings?.length ? (
                      <div className="field-hint">{codeAnalysis.warnings.join(' · ')}</div>
                    ) : null}
                  </BrutalCard>
                </>
              ) : null}
            </>
          ) : (
            <BrutalCard>
              <div className="field-hint">Upload and analyze a paper to select an experiment.</div>
            </BrutalCard>
          )}
        </div>
      </div>
    </section>
  )
}
