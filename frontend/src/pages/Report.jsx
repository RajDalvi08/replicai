import { useEffect, useRef, useState } from 'react'
import { getReport } from '../data'
import Button from '../components/ui/Button'
import SectionHeader from '../components/ui/SectionHeader'

export default function Report() {
  const report = getReport()
  const [phase, setPhase] = useState('IDLE')
  const timerRef = useRef(0)

  useEffect(() => () => window.clearTimeout(timerRef.current), [])

  const generate = () => {
    if (phase === 'GENERATING') return
    setPhase('GENERATING')
    timerRef.current = window.setTimeout(() => setPhase('READY'), 1200)
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
      <Button onClick={generate} disabled={phase === 'GENERATING'}>
        {phase === 'IDLE' && 'GENERATE REPORT'}
        {phase === 'GENERATING' && 'GENERATING…'}
        {phase === 'READY' && 'REPORT READY'}
      </Button>
      <div className="feedback">{phase === 'READY' ? 'Draft marked for export (ui mock)' : phase}</div>
    </section>
  )
}
