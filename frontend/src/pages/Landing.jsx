import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyzeCode, analyzePaper, getExperiments } from '../api/client'
import { useExperiment } from '../experiment'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import MetricCard from '../components/ui/MetricCard'
import ProgressBar from '../components/ui/ProgressBar'
import SectionHeader from '../components/ui/SectionHeader'

const WORKFLOW = ['PAPER', 'EXPERIMENT', 'CODE', 'EXECUTION', 'COMPARISON', 'ROOT CAUSE', 'REPORT']
const GITHUB_PATTERN = /github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+/i

function experimentKey(experiment) {
  return experiment?.experiment_key || experiment?.experiment_id || experiment?.id || ''
}

function reportedMetric(experiment) {
  const reported = Object.values(experiment?.reported_results || {})[0]
  return reported?.value ?? reported ?? null
}

function display(value) {
  return value === null || value === undefined || value === '' ? 'Not available' : String(value)
}

export default function Landing() {
  const navigate = useNavigate()
  const {
    paperId,
    paperAnalysis,
    experiments = [],
    selectedExperiment,
    selectedExperimentId,
    setPaperAnalysis,
    setExperiments,
    setSelectedExperimentId,
    setCodeAnalysis,
    codeAnalysis,
  } = useExperiment()
  const [file, setFile] = useState(null)
  const [repo, setRepo] = useState('')
  const [paperError, setPaperError] = useState('')
  const [codeError, setCodeError] = useState('')
  const [paperLoading, setPaperLoading] = useState(false)
  const [codeLoading, setCodeLoading] = useState(false)

  const selectedId = selectedExperimentId || experimentKey(selectedExperiment)
  const metric = reportedMetric(selectedExperiment)
  const readiness = codeAnalysis?.readiness || null
  const summary = useMemo(
    () => [
      { label: 'PAPER', value: paperAnalysis?.filename || 'Not available' },
      { label: 'EXPERIMENT', value: selectedId || 'Not available' },
      {
        label: 'READINESS',
        value: readiness ? `${readiness.overall_score.toFixed(1)}%` : 'Not available',
        tone: 'accent',
      },
      { label: 'REPOSITORY', value: codeAnalysis?.repository?.analysis_status || 'Not analyzed' },
    ],
    [paperAnalysis, selectedId, readiness, codeAnalysis],
  )

  const handlePaperAnalysis = async (event) => {
    event.preventDefault()
    if (!file || paperLoading) return
    setPaperError('')
    setPaperLoading(true)
    try {
      const response = await analyzePaper(file)
      setPaperAnalysis(response)
      try {
        const extractedExperiments = await getExperiments(response.paper_id)
        setExperiments(extractedExperiments)
      } catch (error) {
        setPaperError(`Paper analyzed, but experiments could not be loaded: ${error.message}`)
      }
    } catch (error) {
      setPaperError(error.message || 'Paper analysis failed.')
    } finally {
      setPaperLoading(false)
    }
  }

  const handleCodeAnalysis = async (event) => {
    event.preventDefault()
    setCodeError('')
    if (!paperId) {
      setCodeError('Analyze a research paper before analyzing a repository.')
      return
    }
    if (!selectedId) {
      setCodeError('Select an extracted experiment first.')
      return
    }
    if (!GITHUB_PATTERN.test(repo.trim())) {
      setCodeError('Enter a valid GitHub repository URL.')
      return
    }

    setCodeLoading(true)
    try {
      const response = await analyzeCode({
        repository_url: repo.trim(),
        paper_id: paperId,
        experiment_id: selectedId,
      })
      setCodeAnalysis(response, repo.trim())
      navigate('/dashboard')
    } catch (error) {
      setCodeError(error.message || 'Repository analysis failed.')
    } finally {
      setCodeLoading(false)
    }
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
            {WORKFLOW.map((step, index) => (
              <span key={step} style={{ display: 'contents' }}>
                <span className="workflow-node">{step}</span>
                {index < WORKFLOW.length - 1 ? <span className="workflow-arrow">→</span> : null}
              </span>
            ))}
          </div>
          <SectionHeader title="CURRENT REPRODUCTION SNAPSHOT" meta="REPLICAI BACKEND" style={{ marginTop: 22 }} />
          <div className="grid-metrics" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', marginTop: 4 }}>
            {summary.map((card) => (
              <MetricCard key={card.label} label={card.label} value={card.value} tone={card.tone || ''} />
            ))}
          </div>
          <BrutalCard style={{ marginTop: 12 }}>
            <div className="kv" style={{ border: 0, paddingTop: 0 }}>
              <span>Selected experiment</span>
              <strong>{display(selectedExperiment?.title)}</strong>
            </div>
            <div className="kv">
              <span>Paper metric</span>
              <strong>{display(metric)}</strong>
            </div>
            {readiness ? (
              <>
                <div className="kv">
                  <span>Readiness</span>
                  <strong>{readiness.overall_score.toFixed(1)}% · {readiness.status}</strong>
                </div>
                <ProgressBar value={readiness.overall_score} />
              </>
            ) : (
              <div className="kv"><span>Readiness</span><strong>Not available</strong></div>
            )}
            {paperAnalysis?.warnings?.length ? (
              <div className="field-hint">{paperAnalysis.warnings.join(' · ')}</div>
            ) : null}
            {selectedExperiment ? (
              <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <Button variant="ghost" onClick={() => navigate('/experiments')}>EXPERIMENTS</Button>
                <Button variant="ghost" onClick={() => navigate('/evidence')}>EVIDENCE GRAPH</Button>
                <Button variant="ghost" onClick={() => navigate('/execution')}>EXECUTION</Button>
              </div>
            ) : null}
          </BrutalCard>
        </div>

        <BrutalCard>
          <form onSubmit={handlePaperAnalysis}>
            <SectionBlock title="RESEARCH PAPER" meta="PDF">
              <label className={`dropzone ${file ? 'active' : ''}`}>
                <input
                  type="file"
                  accept="application/pdf,.pdf"
                  hidden
                  onChange={(event) => {
                    setFile(event.target.files?.[0] || null)
                    setPaperError('')
                  }}
                />
                <div>
                  <strong>{file?.name || paperAnalysis?.filename || 'DRAG & DROP PDF'}</strong>
                  <div>or click to select a research paper</div>
                </div>
              </label>
              {paperError ? <div className="field-hint error">{paperError}</div> : null}
              {paperAnalysis ? (
                <div className="field-hint ok">
                  Paper analyzed · {paperAnalysis.page_count} pages · {experiments.length} experiments
                </div>
              ) : null}
            </SectionBlock>
            <div style={{ height: 12 }} />
            <Button block type="submit" disabled={!file || paperLoading}>
              {paperLoading ? 'ANALYZING PAPER…' : 'ANALYZE PAPER'}
            </Button>
          </form>

          {experiments.length > 0 ? (
            <form onSubmit={handleCodeAnalysis}>
              <div style={{ height: 18 }} />
              <SectionBlock title="SELECT EXPERIMENT" meta={`${experiments.length} EXTRACTED`}>
                <label className="field">
                  <span>EXPERIMENT</span>
                  <select
                    value={selectedId}
                    onChange={(event) => setSelectedExperimentId(event.target.value)}
                  >
                    {experiments.map((experiment) => {
                      const key = experimentKey(experiment)
                      return (
                        <option key={key} value={key}>
                          {key} · {experiment.title || experiment.description || 'Extracted experiment'}
                        </option>
                      )
                    })}
                  </select>
                </label>
              </SectionBlock>
              <div style={{ height: 12 }} />
              <Input
                label="GITHUB REPOSITORY"
                value={repo}
                onChange={(event) => setRepo(event.target.value)}
                placeholder="https://github.com/org/repo"
              />
              {codeError ? <div className="field-hint error">{codeError}</div> : null}
              {codeAnalysis ? (
                <div className="field-hint ok">
                  Repository analyzed · {codeAnalysis.repository?.url}
                </div>
              ) : null}
              <div style={{ height: 14 }} />
              <Button block type="submit" disabled={codeLoading}>
                {codeLoading ? 'ANALYZING REPOSITORY…' : 'ANALYZE CODE'}
              </Button>
            </form>
          ) : null}
          <div className="feedback">
            {paperId ? `PAPER ID ${paperId}` : 'Upload a paper to begin the analysis flow.'}
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
