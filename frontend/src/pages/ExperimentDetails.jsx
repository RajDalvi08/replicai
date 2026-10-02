import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getExperiment } from '../api/client'
import { useExperiment } from '../experiment'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import MetricCard from '../components/ui/MetricCard'
import ProgressBar from '../components/ui/ProgressBar'
import SectionHeader from '../components/ui/SectionHeader'

function display(value) {
  return value === null || value === undefined || value === '' ? 'Not available' : String(value)
}

function reportedMetric(experiment) {
  const result = Object.values(experiment?.reported_results || {})[0]
  return result?.value ?? result ?? null
}

export default function ExperimentDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const {
    experiments = [],
    selectedExperiment,
    selectedExperimentDatabaseId,
    selectedExperimentId,
    setSelectedExperimentId,
    codeAnalysis,
  } = useExperiment()
  const [detail, setDetail] = useState(null)
  const [loadedDatabaseId, setLoadedDatabaseId] = useState(null)
  const [requestError, setRequestError] = useState(null)

  useEffect(() => {
    if (id && id !== selectedExperimentId) setSelectedExperimentId(id)
  }, [id, selectedExperimentId, setSelectedExperimentId])

  const databaseId =
    experiments.find((item) => (item.experiment_key || item.experiment_id) === (id || selectedExperimentId))
      ?.experiment_id || selectedExperimentDatabaseId

  useEffect(() => {
    if (!databaseId) return
    let active = true
    getExperiment(databaseId)
      .then((response) => {
        if (active) {
          setRequestError(null)
          setDetail(response)
        }
      })
      .catch((requestError) => {
        if (active) {
          setRequestError({
            databaseId,
            message: requestError.message || 'Unable to load experiment details.',
          })
        }
      })
      .finally(() => {
        if (active) setLoadedDatabaseId(databaseId)
      })
    return () => {
      active = false
    }
  }, [databaseId])

  const experiment = selectedExperiment
  const parameters = useMemo(() => {
    const fromPaper = { ...(experiment || {}) }
    for (const item of detail?.parameters || []) {
      fromPaper[item.field_name] = item.value
    }
    return fromPaper
  }, [experiment, detail])
  const mappings = codeAnalysis?.mappings || []
  const readiness = codeAnalysis?.readiness
  const readinessItems = readiness?.items || []
  const metric = reportedMetric(experiment)
  const loading = Boolean(databaseId && loadedDatabaseId !== databaseId)
  const error = requestError && requestError.databaseId === databaseId ? requestError.message : ''

  if (!experiment) {
    return (
      <section className="page">
        <div className="page-kicker">04 / DETAILS</div>
        <h1 className="page-title">EXPERIMENT DETAILS</h1>
        <div className="field-hint">Analyze a paper and select an experiment first.</div>
        {error ? <div className="field-hint error">{error}</div> : null}
        <Button onClick={() => navigate('/')}>BACK TO PAPER UPLOAD</Button>
      </section>
    )
  }

  return (
    <section className="page">
      <div className="page-kicker">04 / DETAILS</div>
      <h1 className="page-title">EXPERIMENT {id || selectedExperimentId}</h1>
      <div className="toolbar">
        <Button variant="ghost" onClick={() => navigate('/experiments')}>BACK TO EXPERIMENTS</Button>
      </div>
      {loading ? <div className="field-hint">Loading experiment details…</div> : null}
      {error ? <div className="field-hint error">{error}</div> : null}
      <div className="grid-metrics">
        <MetricCard label="EXTRACTION CONFIDENCE" value={display(experiment.extraction_confidence)} />
        <MetricCard label="READINESS" value={readiness ? `${readiness.overall_score.toFixed(1)}%` : 'Not analyzed'} tone="accent" />
        <MetricCard label="METRIC" value={display(experiment.metric)} />
        <MetricCard label="REPORTED VALUE" value={display(metric)} />
        <MetricCard label="EVIDENCE ITEMS" value={detail?.evidence?.length ?? experiment.evidence?.length ?? 0} />
        <MetricCard label="CODE STATUS" value={codeAnalysis?.repository?.analysis_status || 'Not analyzed'} />
      </div>

      <SectionHeader title="EXPERIMENT SUMMARY" meta={experiment.title || 'EXTRACTED FROM PAPER'} />
      <BrutalCard>
        <p className="page-copy" style={{ margin: 0 }}>
          {display(experiment.description)}
        </p>
      </BrutalCard>

      <div className="split">
        <div>
          <SectionHeader title="PAPER PARAMETERS" />
          <BrutalCard>
            {['dataset', 'model', 'optimizer', 'learning_rate', 'batch_size', 'epochs', 'scheduler', 'weight_decay', 'dropout', 'random_seed', 'metric'].map((key) => (
              <div className="kv" key={key}>
                <span>{key.replaceAll('_', ' ')}</span>
                <strong>{display(parameters[key])}</strong>
              </div>
            ))}
          </BrutalCard>
        </div>
        <div>
          <SectionHeader title="READINESS BREAKDOWN" />
          <BrutalCard>
            {readinessItems.length ? readinessItems.map((item) => (
              <div key={item.category} style={{ marginBottom: 12 }}>
                <div className="kv" style={{ border: 0, paddingBottom: 4 }}>
                  <span>{item.category} · {item.status}</span>
                  <strong>{(item.score * 100).toFixed(1)}%</strong>
                </div>
                <ProgressBar value={item.score * 100} />
                <div className="field-hint">{item.reason}</div>
              </div>
            )) : <div className="field-hint">Code analysis is not available yet.</div>}
          </BrutalCard>
        </div>
      </div>

      <SectionHeader title="PAPER ↔ CODE MAPPING" />
      <BrutalCard>
        {mappings.length ? mappings.map((mapping) => (
          <div className="kv" key={`${mapping.paper_field}-${mapping.code_field || ''}`}>
            <span>{mapping.paper_field} · {mapping.status} · {(mapping.confidence * 100).toFixed(0)}%</span>
            <strong>{display(mapping.paper_value)} ↔ {display(mapping.code_value)} · {mapping.reason}</strong>
          </div>
        )) : <div className="field-hint">Code mapping is not available yet.</div>}
      </BrutalCard>

      <SectionHeader title="PAPER EVIDENCE" />
      <BrutalCard>
        {(detail?.evidence || experiment.evidence || []).length ? (detail?.evidence || experiment.evidence).map((item, index) => (
          <div className="kv" key={`${item.field}-${item.page}-${index}`}>
            <span>{item.field} · page {display(item.page)} · confidence {display(item.confidence)}</span>
            <strong>{display(item.quote || item.value)}</strong>
          </div>
        )) : <div className="field-hint">No evidence was returned for this experiment.</div>}
      </BrutalCard>

      <SectionHeader title="NEXT STEP" meta="05 / PROVENANCE" />
      <BrutalCard>
        <div className="kv" style={{ border: 0, padding: 0 }}>
          <span>Pipeline</span>
          <strong>EXPERIMENT → EVIDENCE → EXECUTION → COMPARISON</strong>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/evidence')}>OPEN EVIDENCE GRAPH</Button>
          <Button variant="ghost" onClick={() => navigate('/execution')}>RUN IN SANDBOX</Button>
        </div>
      </BrutalCard>
    </section>
  )
}
