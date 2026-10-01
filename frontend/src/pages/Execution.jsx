import { useEffect, useRef, useState } from 'react'
import { getRuns } from '../data'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import MetricCard from '../components/ui/MetricCard'
import SectionHeader from '../components/ui/SectionHeader'
import StatusBadge from '../components/ui/StatusBadge'
import Terminal from '../components/ui/Terminal'

export default function Execution() {
  const runs = getRuns()
  const [log, setLog] = useState(runs.logLines)
  const [phase, setPhase] = useState('IDLE')
  const [selectedRun, setSelectedRun] = useState(runs.items[0]?.id)
  const timerRef = useRef(0)

  useEffect(() => () => window.clearTimeout(timerRef.current), [])

  const runExperiment = () => {
    if (phase === 'RUNNING') return
    setPhase('RUNNING')
    setLog((current) => [...current, '$ docker run replicai/e2', 'sandbox boot (ui mock)...'])
    timerRef.current = window.setTimeout(() => {
      setLog((current) => [
        ...current,
        'loading dataset...',
        'training...',
        'evaluating...',
        'accuracy: 84.2%',
        'completed.',
      ])
      setPhase('COMPLETED')
    }, 1600)
  }

  return (
    <section className="page">
      <div className="page-kicker">06 / SANDBOX</div>
      <h1 className="page-title">EXECUTION / {runs.experimentId}</h1>
      <div className="grid-metrics">
        <MetricCard label="SANDBOX" value={runs.sandbox} />
        <MetricCard label="RUN COUNT" value={runs.runCount} />
        <MetricCard label="STATUS" value={phase === 'IDLE' ? runs.status : phase} tone="ok" />
        <MetricCard label="MEAN" value={runs.mean} suffix="%" />
      </div>
      <SectionHeader title="RUN CARDS" meta="UI ONLY — NO DOCKER CALLS" />
      <div className="three-col">
        {runs.items.map((run) => (
          <BrutalCard
            key={run.id}
            className={`run-card ${selectedRun === run.id ? 'selected-run' : ''}`}
            onClick={() => setSelectedRun(run.id)}
          >
            <div className="page-kicker">{run.id}</div>
            <div className="metric-value" style={{ fontSize: 24, margin: '10px 0' }}>
              {run.accuracy}%
            </div>
            <StatusBadge status={run.status} />
            <div className="kv" style={{ marginTop: 10 }}>
              <span>Duration</span>
              <strong>{run.duration}</strong>
            </div>
          </BrutalCard>
        ))}
      </div>
      <SectionHeader title="CONSOLE" />
      <Terminal lines={log} />
      <div style={{ marginTop: 12 }}>
        <Button onClick={runExperiment} disabled={phase === 'RUNNING'}>
          {phase === 'IDLE' && 'RUN EXPERIMENT'}
          {phase === 'RUNNING' && 'RUNNING…'}
          {phase === 'COMPLETED' && 'RUN AGAIN'}
        </Button>
        <div className="feedback">{phase}</div>
      </div>
    </section>
  )
}
