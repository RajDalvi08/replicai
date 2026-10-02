import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useExperiment } from '../experiment'
import { getRuns } from '../data'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import MetricCard from '../components/ui/MetricCard'
import SectionHeader from '../components/ui/SectionHeader'
import StatusBadge from '../components/ui/StatusBadge'
import Terminal from '../components/ui/Terminal'

function buildRunLog(run, seed) {
  return [
    `$ docker run replicai/e2 --run ${run.id}`,
    'booting python sandbox...',
    'pulling image replicai/transformer-study:latest',
    'loading dataset WMT 2014 EN-DE...',
    'loading model Transformer-Base (8 heads)...',
    'initializing optimizer Adam (lr=1e-4)...',
    `step 10000 / 100000  loss=2.${40 + seed}1`,
    `step 50000 / 100000  loss=1.${10 + seed}8`,
    `step 90000 / 100000  loss=0.${90 + seed}2`,
    'evaluating on held-out split...',
    `accuracy: ${run.accuracy}%`,
    'completed.',
  ]
}

export default function Execution() {
  const { selectedExperiment } = useExperiment()
  const allRuns = getRuns(selectedExperiment.id)
  const runs = allRuns
  const navigate = useNavigate()
  const [phase, setPhase] = useState('IDLE')
  const [selectedRun, setSelectedRun] = useState(runs.items[0]?.id)
  const timerRef = useRef(0)

  const baseLogs = useMemo(
    () =>
      Object.fromEntries(
        runs.items.map((run, idx) => [run.id, buildRunLog(run, idx)]),
      ),
    [runs.items],
  )

  const [log, setLog] = useState(() => baseLogs[selectedRun] || runs.logLines)

  const pickRun = (runId) => {
    setSelectedRun(runId)
    if (baseLogs[runId]) setLog(baseLogs[runId])
  }

  useEffect(() => () => window.clearTimeout(timerRef.current), [])

  const runExperiment = () => {
    if (phase === 'RUNNING') return
    setPhase('RUNNING')
    const run = runs.items.find((item) => item.id === selectedRun) || runs.items[0]
    const seed = runs.items.indexOf(run)
    const freshLog = buildRunLog(
      { id: `${run.id}+`, accuracy: run.accuracy },
      (seed + 1) % runs.items.length,
    )
    setLog(freshLog)
    timerRef.current = window.setTimeout(() => {
      setPhase('COMPLETED')
    }, 900)
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
            onClick={() => pickRun(run.id)}
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
        <Button
          onClick={runExperiment}
          disabled={phase === 'RUNNING' || runs.runCount === 0}
        >
          {runs.runCount === 0 && phase !== 'RUNNING'
            ? 'RUNS UNAVAILABLE'
            : phase === 'IDLE'
              ? 'RUN EXPERIMENT'
              : phase === 'RUNNING'
                ? 'RUNNING…'
                : 'RUN AGAIN'}
        </Button>
        <div className="feedback">
          {runs.runCount === 0
            ? `${phase} · ${selectedExperiment.id} sandbox run blocked on missing configuration.`
            : `${phase} · sandbox runs reproducible within ±${runs.std.toFixed(2)}% std`}
        </div>
      </div>
      <SectionHeader title="NEXT STEP" meta="07 / COMPARISON" />
      <BrutalCard>
        <div className="kv" style={{ border: 0, padding: 0 }}>
          <span>Pipeline</span>
          <strong>EXECUTION → COMPARISON → ROOT CAUSE → REPORT</strong>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/results')}>VIEW RESULTS</Button>
          <Button variant="ghost" onClick={() => navigate('/root-cause')}>SKIP TO ROOT CAUSE</Button>
        </div>
      </BrutalCard>
    </section>
  )
}
