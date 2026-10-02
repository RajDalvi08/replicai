import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useExperiment } from '../experiment'
import { getReport } from '../data'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import SectionHeader from '../components/ui/SectionHeader'

export default function Report() {
  const { selectedExperiment } = useExperiment()
  const report = getReport(selectedExperiment.id)
  const navigate = useNavigate()
  const [phase, setPhase] = useState('IDLE')
  const timerRef = useRef(0)

  useEffect(() => () => window.clearTimeout(timerRef.current), [])

  const generate = () => {
    if (phase === 'GENERATING') return
    setPhase('GENERATING')
    timerRef.current = window.setTimeout(() => setPhase('READY'), 700)
  }

  const blocks = [
    ['PROJECT SUMMARY', report.projectSummary],
    ['PAPER', `${report.paper} · ${report.paperFile}`],
    ['REPOSITORY', report.repository],
    ['SELECTED EXPERIMENT', `${report.experiment.id} — ${report.experiment.name}`],
    ['READINESS', `${report.readiness}%`],
    ['EXECUTION SUMMARY', report.executionSummary],
    ['PAPER VS REPRODUCED METRICS', `Paper ${report.paperResult}% · Reproduced ${report.reproduced}% · Gap ${report.gap} pp`],
    ['ROOT CAUSE', `${report.rootCause.title} (${report.rootCause.finding})`],
    ['EVIDENCE', report.evidence.join(' · ')],
    ['FINAL REPRODUCIBILITY STATUS', report.finalStatus],
  ]

  return (
    <section className="page">
      <div className="page-kicker">09 / EXPORT</div>
      <h1 className="page-title">REPRODUCIBILITY REPORT</h1>
      <SectionHeader title="PREVIEW" meta={phase} />
      {blocks.map(([title, body]) => (
        <article className="report-block" key={title}>
          <h3>{title}</h3>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 13 }}>{body}</div>
        </article>
      ))}
      <div style={{ marginBottom: 12 }}>
        <Button onClick={generate} disabled={phase === 'GENERATING'}>
          {phase === 'IDLE' && 'GENERATE REPORT'}
          {phase === 'GENERATING' && 'GENERATING…'}
          {phase === 'READY' && 'REPORT READY'}
        </Button>
      </div>
      <div className="feedback">
        {phase === 'READY'
          ? 'Draft marked for export (ui mock) · final status PARTIAL — UNDER REVIEW'
          : phase}
      </div>
      <SectionHeader title="WORKFLOW END" meta="RETURN / REVIEW" />
      <BrutalCard>
        <div className="kv" style={{ border: 0, padding: 0 }}>
          <span>Shortcuts</span>
          <strong>DASHBOARD · EXPERIMENTS · EVIDENCE</strong>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/dashboard')}>BACK TO DASHBOARD</Button>
          <Button variant="ghost" onClick={() => navigate('/experiments')}>
            EXPERIMENT INDEX
          </Button>
          <Button variant="ghost" onClick={() => navigate('/evidence')}>
            EVIDENCE GRAPH
          </Button>
        </div>
      </BrutalCard>
    </section>
  )
}
