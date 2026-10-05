import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getResults } from '../api/client'
import { useExperiment } from '../experiment'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import SectionHeader from '../components/ui/SectionHeader'

function display(value) {
  return value === null || value === undefined || value === '' ? 'Not available' : String(value)
}

export default function Report() {
  const navigate = useNavigate()
  const {
    paperAnalysis,
    selectedExperiment,
    selectedExperimentId,
    codeAnalysis,
    run,
    validation,
    results,
    setResults,
  } = useExperiment()
  const [phase, setPhase] = useState(results ? 'READY' : 'IDLE')
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState(false)
  const [downloadedExperimentId, setDownloadedExperimentId] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const downloadTimer = useRef(null)

  useEffect(() => () => {
    if (downloadTimer.current) window.clearTimeout(downloadTimer.current)
  }, [])

  useEffect(() => {
    if (!selectedExperimentId || results) return
    let active = true
    getResults(selectedExperimentId)
      .then((response) => {
        if (!active) return
        setResults(response)
        setPhase('READY')
      })
      .catch((requestError) => {
        if (!active) return
        setError(requestError.message || 'Unable to load reproducibility results.')
        setPhase('ERROR')
      })
    return () => {
      active = false
    }
  }, [selectedExperimentId, results, setResults])

  const paper = results?.paper
  const reproduction = results?.reproduction
  const comparison = results?.comparison
  const blocks = [
    ['PAPER', paperAnalysis?.filename || 'Not available'],
    ['PAPER ID', paperAnalysis?.paper_id || 'Not available'],
    ['SELECTED EXPERIMENT', `${selectedExperimentId || 'Not available'} — ${selectedExperiment?.title || 'Not available'}`],
    ['REPOSITORY', codeAnalysis?.repository?.url || 'Not analyzed'],
    ['READINESS', codeAnalysis?.readiness ? `${codeAnalysis.readiness.overall_score.toFixed(1)}% · ${codeAnalysis.readiness.status}` : 'Not available'],
    ['EXECUTION', run ? `${run.run_id} · ${run.status} · exit ${display(run.exit_code)}` : 'Not run'],
    ['VALIDATION', validation ? `${validation.runs?.length || 0} runs · ${validation.status}` : 'Not validated'],
    ['PAPER RESULT', `${display(paper?.metric)} · ${display(paper?.reported_value)}`],
    ['REPRODUCTION', `${display(reproduction?.metric)} · mean ${display(reproduction?.mean)} · std ${display(reproduction?.std)}`],
    ['COMPARISON', comparison ? `${comparison.status} · difference ${display(comparison.absolute_difference)} · relative ${display(comparison.relative_difference_percent)}%` : 'Not available'],
  ]
  const displayedPhase =
    phase === 'IDLE' && selectedExperimentId && !results ? 'LOADING' : phase

  const generate = async () => {
    if (!selectedExperimentId) {
      setError('Analyze a paper and select an experiment before generating results.')
      return
    }
    setError('')
    setPhase('GENERATING')
    try {
      const response = await getResults(selectedExperimentId)
      setResults(response)
      setPhase('READY')
    } catch (requestError) {
      setError(requestError.message || 'Unable to load reproducibility results.')
      setPhase('ERROR')
    }
  }

  const downloadReport = async () => {
    if (!selectedExperiment || downloading) return
    setDownloading(true)
    setDownloadedExperimentId('')
    setDownloadError('')
    try {
      const { downloadExperimentReport } = await import('../utils/reportPdf')
      downloadExperimentReport({
        experiment: selectedExperiment,
        experimentId: selectedExperimentId,
        paperAnalysis,
        codeAnalysis,
        run,
        validation,
        results,
      })
      setDownloadedExperimentId(selectedExperimentId)
      if (downloadTimer.current) window.clearTimeout(downloadTimer.current)
      downloadTimer.current = window.setTimeout(() => setDownloadedExperimentId(''), 2500)
    } catch {
      setDownloadError('Unable to generate the report. Please try again.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <section className="page">
      <div className="page-kicker">09 / EXPORT</div>
      <h1 className="page-title">REPRODUCIBILITY REPORT</h1>
      {error ? <div className="field-hint error">{error}</div> : null}
      <SectionHeader title="PREVIEW" meta={displayedPhase} />
      {blocks.map(([title, body]) => (
        <article className="report-block" key={title}>
          <h3>{title}</h3>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 13 }}>{body}</div>
        </article>
      ))}
      {results?.explanation?.length ? (
        <>
          <SectionHeader title="BACKEND EXPLANATION" />
          <BrutalCard>
            {results.explanation.map((item, index) => (
              <div className="kv" key={`${item.parameter || item.category || 'detail'}-${index}`}>
                <span>{display(item.parameter || item.category)} · {display(item.status)}</span>
                <strong>{display(item.reason || item.message)}</strong>
              </div>
            ))}
          </BrutalCard>
        </>
      ) : null}
      <div className="toolbar" style={{ marginTop: 14 }}>
        <Button onClick={generate} disabled={phase === 'GENERATING' || displayedPhase === 'LOADING'}>
          {phase === 'GENERATING' || displayedPhase === 'LOADING' ? 'LOADING RESULTS…' : phase === 'READY' ? 'REFRESH RESULTS' : 'LOAD FINAL RESULTS'}
        </Button>
        <Button onClick={downloadReport} disabled={!selectedExperiment || downloading}>
          {downloading ? 'GENERATING REPORT…' : downloadedExperimentId && downloadedExperimentId === selectedExperimentId ? 'REPORT DOWNLOADED' : 'DOWNLOAD REPORT'}
        </Button>
      </div>
      {downloadError ? <div className="field-hint error" role="alert">{downloadError}</div> : null}
      {downloadedExperimentId && downloadedExperimentId === selectedExperimentId ? (
        <div className="field-hint ok" role="status" aria-live="polite">Report downloaded successfully.</div>
      ) : null}
      <div className="feedback">{phase === 'READY' ? 'Report populated from ReplicAI backend results.' : phase}</div>
      <SectionHeader title="WORKFLOW END" meta="RETURN / REVIEW" />
      <BrutalCard>
        <div className="kv" style={{ border: 0, padding: 0 }}>
          <span>Shortcuts</span>
          <strong>DASHBOARD · EXPERIMENTS · EVIDENCE</strong>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/dashboard')}>BACK TO DASHBOARD</Button>
          <Button variant="ghost" onClick={() => navigate('/experiments')}>EXPERIMENT INDEX</Button>
          <Button variant="ghost" onClick={() => navigate('/evidence')}>EVIDENCE GRAPH</Button>
        </div>
      </BrutalCard>
    </section>
  )
}
