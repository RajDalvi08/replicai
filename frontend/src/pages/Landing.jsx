import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useExperiment } from '../experiment'
import { getProject, getRootCause, getRuns } from '../data'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import MetricCard from '../components/ui/MetricCard'
import ProgressBar from '../components/ui/ProgressBar'
import SectionHeader from '../components/ui/SectionHeader'
import StatusBadge from '../components/ui/StatusBadge'

const GITHUB_PATTERN = /github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+/i

function validateGithub(url) {
  const value = url.trim()
  if (!value) return 'Repository URL is required.'
  if (!GITHUB_PATTERN.test(value)) return 'Enter a valid GitHub repository URL.'
  return ''
}

function fmt(value, suffix = '') {
  return value === null || value === undefined || value === 'N/A' ? '—' : `${value}${suffix}`
}

export default function Landing() {
  const { selectedExperiment } = useExperiment()
  const project = getProject()
  const runs = getRuns(selectedExperiment.id)
  const root = getRootCause(selectedExperiment.id)
  const navigate = useNavigate()
  const runValues = runs.items.map((item) => item.accuracy.replace('%', '')).join(' / ') || '—'
  const [paperName, setPaperName] = useState('')
  const [repo, setRepo] = useState(project.repository.url)
  const [repoError, setRepoError] = useState('')
  const [analyze, setAnalyze] = useState('IDLE')
  const timerRef = useRef(0)

  const snapshot = useMemo(
    () => [
      { label: 'EXPERIMENT', value: selectedExperiment.id },
      { label: 'RUNS', value: `${runs.runCount} · ${runValues}` },
      { label: 'ROOT CAUSE', value: root.title, tone: 'warn' },
      { label: 'STATUS', value: <StatusBadge status={selectedExperiment.reproducibility || selectedExperiment.status || 'UNDER REVIEW'} /> },
    ],
    [selectedExperiment.id, selectedExperiment.reproducibility, selectedExperiment.status, root.title, runs.runCount, runValues],
  )

  useEffect(() => () => window.clearTimeout(timerRef.current), [])

  const startAnalyze = () => {
    const error = validateGithub(repo)
    setRepoError(error)
    if (error || analyze === 'ANALYZING') return
    setAnalyze('ANALYZING')
    timerRef.current = window.setTimeout(() => {
      setAnalyze('COMPLETE')
      navigate('/dashboard')
    }, 900)
  }

  return (
    <section className="page">
      <div className="hero">
        <div>
          <div className="page-kicker">01 / START PROJECT</div>
          <h1>REPRODUCE THE PAPER.</h1>
          <p className="page-copy">
            ReplicAI connects research papers, GitHub repositories, experiment configs, and execution
            evidence into a single reproducibility console. Start with a PDF and a repo. Trace the gap.
          </p>
          <div className="workflow">
            {project.workflow.map((step, index) => (
              <span key={step} style={{ display: 'contents' }}>
                <span className="workflow-node">{step}</span>
                {index < project.workflow.length - 1 ? <span className="workflow-arrow">→</span> : null}
              </span>
            ))}
          </div>
          <SectionHeader title="CURRENT REPRODUCTION SNAPSHOT" meta="UI DEMO DATA" style={{ marginTop: 22 }} />
          <div className="grid-metrics" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', marginTop: 4 }}>
            {snapshot.map((card) => (
              <MetricCard key={card.label} label={card.label} value={card.value} tone={card.tone || ''} />
            ))}
          </div>
          <BrutalCard style={{ marginTop: 12 }}>
            <div className="kv" style={{ border: 0, paddingTop: 0 }}>
              <span>Readiness</span>
              <strong>{selectedExperiment.readiness}% · {project.papers} paper · {project.experimentCount} experiments</strong>
            </div>
            <ProgressBar value={selectedExperiment.readiness} />
            <div className="split" style={{ marginTop: 12 }}>
              <div>
                <div className="metric-label">PAPER METRIC</div>
                <div className="metric-value" style={{ fontSize: 22 }}>
                  {Number(selectedExperiment.paperMetric).toFixed(2)}%
                </div>
              </div>
              <div>
                <div className="metric-label">REPRODUCED</div>
                <div
                  className="metric-value"
                  style={{
                    fontSize: 22,
                    color: runs.mean === 'N/A' ? 'var(--muted)' : 'var(--success)',
                  }}
                >
                  {fmt(runs.mean, runs.mean === 'N/A' ? '' : '%')}
                </div>
              </div>
            </div>
            <div className="kv" style={{ marginTop: 8 }}>
              <span>Gap</span>
              <strong style={{ color: 'var(--warning)' }}>
                {fmt(typeof runs.gap === 'number' ? runs.gap : null, ' pp')}
                {runs.std !== 'N/A' && typeof runs.std === 'number' ? ` · mean ± ${runs.std.toFixed(2)}% std` : ''}
              </strong>
            </div>
            <div className="kv">
              <span>Root Cause</span>
              <strong>{root.evidence.paper} vs {root.evidence.code}</strong>
            </div>
            <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <Button variant="ghost" onClick={() => navigate('/dashboard')}>
                OPEN DASHBOARD
              </Button>
              <Button variant="ghost" onClick={() => navigate('/evidence')}>
                EVIDENCE GRAPH
              </Button>
              <Button variant="ghost" onClick={() => navigate('/results')}>
                RESULTS
              </Button>
            </div>
          </BrutalCard>
        </div>
        <BrutalCard>
          <SectionBlock title="RESEARCH PAPER" meta="PDF">
            <label className={`dropzone ${paperName ? 'active' : ''}`}>
              <input
                type="file"
                accept="application/pdf"
                hidden
                onChange={(event) => setPaperName(event.target.files?.[0]?.name || '')}
              />
              <div>
                <strong>{paperName || 'DRAG & DROP PDF'}</strong>
                <div>or click to select a research paper</div>
              </div>
            </label>
            {paperName ? <div className="field-hint ok">Selected · {paperName}</div> : null}
          </SectionBlock>
          <div style={{ height: 12 }} />
          <Input
            label="GITHUB REPOSITORY"
            value={repo}
            onChange={(event) => {
              const next = event.target.value
              setRepo(next)
              setRepoError(next.trim() ? validateGithub(next) : '')
            }}
            placeholder="https://github.com/org/repo"
          />
          {repoError ? (
            <div className="field-hint error">{repoError}</div>
          ) : repo.trim() ? (
            <div className="field-hint ok">Repository stored · {repo}</div>
          ) : (
            <div className="field-hint">Enter a GitHub repository URL</div>
          )}
          <div style={{ height: 14 }} />
          <Button block onClick={startAnalyze} disabled={analyze === 'ANALYZING'}>
            {analyze === 'IDLE' && 'ANALYZE EXPERIMENT'}
            {analyze === 'ANALYZING' && 'ANALYZING…'}
            {analyze === 'COMPLETE' && 'COMPLETE'}
          </Button>
          <div className="feedback">
            {paperName ? `PAPER ${paperName}` : `PAPER ${project.paperFile}`} · {analyze}
          </div>
        </BrutalCard>
      </div>
    </section>
  )
}

function SectionBlock({ title, meta, children }) {
  return (
    <div>
      <div className="section-header" style={{ marginTop: 0 }}>
        <h2>{title}</h2>
        <span>{meta}</span>
      </div>
      {children}
    </div>
  )
}
