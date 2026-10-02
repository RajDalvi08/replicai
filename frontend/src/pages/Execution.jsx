import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getResults, getRun, runExperiment as startRun, validateExperiment as validateRuns } from '../api/client'
import { useExperiment } from '../experiment'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'
import MetricCard from '../components/ui/MetricCard'
import SectionHeader from '../components/ui/SectionHeader'
import StatusBadge from '../components/ui/StatusBadge'
import Terminal from '../components/ui/Terminal'

const FINAL_STATES = new Set(['completed', 'failed', 'timeout'])
const delay = (milliseconds) => new Promise((resolve) => window.setTimeout(resolve, milliseconds))

function display(value, suffix = '') {
  return value === null || value === undefined || value === '' ? 'Not available' : `${value}${suffix}`
}

function runOutput(run) {
  if (!run) return ['Waiting for an execution run.']
  const lines = []
  if (run.stdout) lines.push(...run.stdout.split(/\r?\n/))
  if (run.stderr) lines.push(...run.stderr.split(/\r?\n/).map((line) => `stderr: ${line}`))
  if (run.error) lines.push(`error: ${run.error}`)
  if (!lines.length) lines.push(`Run ${run.run_id}: ${run.status}`)
  return lines
}

export default function Execution() {
  const navigate = useNavigate()
  const {
    selectedExperimentId,
    repositoryId,
    codeAnalysis,
    runId,
    run,
    validation,
    results,
    setRun,
    setValidation,
    setResults,
  } = useExperiment()
  const entryPoint = codeAnalysis?.entry_points?.find((item) => item.role === 'training_entrypoint')
  const suggestedCommand = entryPoint ? `python ${entryPoint.path}` : ''
  const [command, setCommand] = useState(suggestedCommand)
  const [timeoutSeconds, setTimeoutSeconds] = useState(300)
  const [running, setRunning] = useState(false)
  const [validating, setValidating] = useState(false)
  const [error, setError] = useState('')
  const activeRef = useRef(true)

  useEffect(() => {
    activeRef.current = true
    return () => {
      activeRef.current = false
    }
  }, [])

  const metrics = useMemo(() => Object.entries(run?.metrics || {}), [run])
  const validationRuns = validation?.runs || []

  const execute = async () => {
    setError('')
    if (!repositoryId || !selectedExperimentId) {
      setError('Analyze a paper and repository before starting execution.')
      return
    }
    if (!command.trim()) {
      setError('No training entry point was detected. Enter a repository-relative Python script command.')
      return
    }

    setRunning(true)
    try {
      const accepted = await startRun({
        repository_id: Number(repositoryId),
        experiment_id: selectedExperimentId,
        command: command.trim(),
        timeout_seconds: Math.max(1, Math.min(3600, Number(timeoutSeconds) || 300)),
      })
      let current = await getRun(accepted.run_id)
      setRun(accepted.run_id, current)
      const deadline = Date.now() + (Math.max(1, Math.min(3600, Number(timeoutSeconds) || 300)) + 30) * 1000
      while (!FINAL_STATES.has(current.status) && Date.now() < deadline && activeRef.current) {
        await delay(1000)
        current = await getRun(accepted.run_id)
        if (activeRef.current) setRun(accepted.run_id, current)
      }
      if (activeRef.current && !FINAL_STATES.has(current.status)) {
        setError('Run status polling exceeded the configured timeout window.')
      }
    } catch (requestError) {
      if (activeRef.current) setError(requestError.message || 'Experiment execution failed.')
    } finally {
      if (activeRef.current) setRunning(false)
    }
  }

  const validate = async () => {
    setError('')
    if (!repositoryId || !selectedExperimentId || !command.trim()) {
      setError('Analyze a paper and repository, then provide a valid Python script command.')
      return
    }
    setValidating(true)
    try {
      const response = await validateRuns({
        repository_id: Number(repositoryId),
        experiment_id: selectedExperimentId,
        command: command.trim(),
        timeout_seconds: Math.max(1, Math.min(3600, Number(timeoutSeconds) || 300)),
        runs: 3,
      })
      setValidation(response)
      const finalResults = await getResults(selectedExperimentId)
      setResults(finalResults)
    } catch (requestError) {
      setError(requestError.message || 'Experiment validation failed.')
    } finally {
      setValidating(false)
    }
  }

  return (
    <section className="page">
      <div className="page-kicker">06 / SANDBOX</div>
      <h1 className="page-title">EXECUTION / {selectedExperimentId || 'Not selected'}</h1>
      {!repositoryId ? <div className="field-hint">Analyze a repository before running an experiment.</div> : null}
      {error ? <div className="field-hint error">{error}</div> : null}
      <div className="grid-metrics">
        <MetricCard label="REPOSITORY" value={repositoryId || 'Not available'} />
        <MetricCard label="RUN ID" value={runId || 'Not started'} />
        <MetricCard label="STATUS" value={run?.status || 'Not started'} tone={run?.status === 'completed' ? 'ok' : ''} />
        <MetricCard label="EXECUTION TIME" value={display(run?.execution_time_seconds, ' s')} />
      </div>
      <SectionHeader title="EXECUTION COMMAND" meta={entryPoint?.path || 'SELECT A PYTHON ENTRY POINT'} />
      <BrutalCard>
        <Input
          label="REPOSITORY-RELATIVE PYTHON COMMAND"
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          placeholder="python path/to/train.py"
        />
        <div style={{ height: 10 }} />
        <Input
          label="TIMEOUT (SECONDS)"
          type="number"
          min="1"
          max="3600"
          value={timeoutSeconds}
          onChange={(event) => setTimeoutSeconds(event.target.value)}
        />
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={execute} disabled={running || validating || !repositoryId}>
            {running ? 'RUNNING…' : 'RUN EXPERIMENT'}
          </Button>
          <Button variant="ghost" onClick={validate} disabled={running || validating || !repositoryId}>
            {validating ? 'VALIDATING 3 RUNS…' : 'VALIDATE · 3 RUNS'}
          </Button>
        </div>
      </BrutalCard>

      <SectionHeader title="RUN STATUS" meta={run?.status?.toUpperCase() || 'NO RUN'} />
      {run ? (
        <BrutalCard>
          <div className="kv"><span>Run ID</span><strong>{run.run_id}</strong></div>
          <div className="kv"><span>Exit code</span><strong>{display(run.exit_code)}</strong></div>
          <div className="kv"><span>Execution time</span><strong>{display(run.execution_time_seconds, ' seconds')}</strong></div>
          <div className="kv"><span>Status</span><strong><StatusBadge status={run.status} /></strong></div>
          {metrics.map(([name, value]) => (
            <div className="kv" key={name}><span>{name}</span><strong>{value}</strong></div>
          ))}
          {run.error ? <div className="field-hint error">{run.error}</div> : null}
        </BrutalCard>
      ) : null}
      <SectionHeader title="CONSOLE" />
      <Terminal lines={runOutput(run)} />

      <SectionHeader title="VALIDATION · 3 RUNS" meta={validation?.status?.toUpperCase() || 'NOT VALIDATED'} />
      {validation ? (
        <>
          <div className="three-col">
            {validationRuns.map((item) => (
              <BrutalCard key={item.run_id}>
                <div className="page-kicker">RUN {item.run}</div>
                <div className="kv"><span>Status</span><strong>{item.status}</strong></div>
                <div className="kv"><span>Exit code</span><strong>{display(item.exit_code)}</strong></div>
                <div className="kv"><span>Time</span><strong>{display(item.execution_time_seconds, ' s')}</strong></div>
                {Object.entries(item.metrics || {}).map(([name, value]) => (
                  <div className="kv" key={name}><span>{name}</span><strong>{value}</strong></div>
                ))}
              </BrutalCard>
            ))}
          </div>
          <div className="grid-metrics" style={{ marginTop: 14 }}>
            <MetricCard label="METRIC" value={validation.metric || 'Not available'} />
            <MetricCard label="MEAN" value={display(validation.mean)} />
            <MetricCard label="STANDARD DEVIATION" value={display(validation.std)} />
            <MetricCard label="MINIMUM" value={display(validation.min)} />
            <MetricCard label="MAXIMUM" value={display(validation.max)} />
          </div>
          {Object.entries(validation.metrics || {}).map(([name, summary]) => (
            <div className="kv" key={name}>
              <span>{name}</span>
              <strong>
                mean {display(summary.mean)} · std {display(summary.std)} · min {display(summary.min)} · max {display(summary.max)}
              </strong>
            </div>
          ))}
        </>
      ) : <div className="field-hint">No validation results yet.</div>}

      <SectionHeader title="NEXT STEP" meta="07 / COMPARISON" />
      <BrutalCard>
        <div className="kv" style={{ border: 0, padding: 0 }}>
          <span>Pipeline</span>
          <strong>EXECUTION → VALIDATION → COMPARISON → REPORT</strong>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/results')} disabled={!results}>VIEW RESULTS</Button>
          <Button variant="ghost" onClick={() => navigate('/report')} disabled={!results}>VIEW REPORT</Button>
        </div>
      </BrutalCard>
    </section>
  )
}
