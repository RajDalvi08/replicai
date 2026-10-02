import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getResults } from '../api/client'
import { useExperiment } from '../experiment'
import ComparisonChart from '../components/chart/ComparisonChart'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import MetricCard from '../components/ui/MetricCard'
import SectionHeader from '../components/ui/SectionHeader'

function display(value, suffix = '') {
  return value === null || value === undefined || value === '' ? 'Not available' : `${value}${suffix}`
}

function evidenceText(evidence) {
  if (!evidence || typeof evidence !== 'object') return 'Not available'
  return [
    evidence.quote,
    evidence.page !== null && evidence.page !== undefined ? `page ${evidence.page}` : null,
    evidence.confidence !== null && evidence.confidence !== undefined
      ? `${Math.round(evidence.confidence * 100)}% confidence`
      : null,
  ].filter(Boolean).join(' · ') || 'Not available'
}

export default function Results() {
  const navigate = useNavigate()
  const { selectedExperimentId, results, setResults } = useExperiment()
  const [loadedExperimentId, setLoadedExperimentId] = useState(null)
  const [requestError, setRequestError] = useState(null)

  useEffect(() => {
    if (!selectedExperimentId) return
    let active = true
    getResults(selectedExperimentId)
      .then((response) => {
        if (active) {
          setRequestError(null)
          setResults(response)
        }
      })
      .catch((requestError) => {
        if (active) {
          setRequestError({
            experimentId: selectedExperimentId,
            message: requestError.message || 'Unable to load experiment results.',
          })
        }
      })
      .finally(() => {
        if (active) setLoadedExperimentId(selectedExperimentId)
      })
    return () => {
      active = false
    }
  }, [selectedExperimentId, setResults])

  const paper = results?.paper
  const reproduction = results?.reproduction
  const comparison = results?.comparison
  const loading = Boolean(selectedExperimentId && loadedExperimentId !== selectedExperimentId)
  const error = requestError && requestError.experimentId === selectedExperimentId ? requestError.message : ''
  const chartData = useMemo(() => {
    if (!comparison) return []
    return [
      { name: 'Paper', value: comparison.paper_value, fill: '#8B5CF6' },
      { name: 'Reproduced', value: comparison.reproduced_value, fill: '#22C55E' },
    ].filter((item) => typeof item.value === 'number' && Number.isFinite(item.value))
  }, [comparison])

  return (
    <section className="page">
      <div className="page-kicker">07 / COMPARISON</div>
      <h1 className="page-title">{selectedExperimentId || 'EXPERIMENT'} · PAPER VS REPRODUCED</h1>
      {loading ? <div className="field-hint">Loading reproducibility results…</div> : null}
      {error ? <div className="field-hint error">{error}</div> : null}
      {!selectedExperimentId ? <div className="field-hint">Analyze a paper and select an experiment first.</div> : null}
      {selectedExperimentId && !results && !loading && !error ? (
        <div className="field-hint">Run and validate the experiment before loading final results.</div>
      ) : null}

      <div className="grid-metrics">
        <MetricCard label="PAPER VALUE" value={display(paper?.reported_value)} />
        <MetricCard label="REPRODUCED MEAN" value={display(reproduction?.mean)} tone={reproduction?.mean == null ? '' : 'ok'} />
        <MetricCard label="ABSOLUTE DIFFERENCE" value={display(comparison?.absolute_difference)} tone={comparison ? 'warn' : ''} />
        <MetricCard label="RELATIVE DIFFERENCE" value={display(comparison?.relative_difference_percent, comparison ? '%' : '')} />
        <MetricCard label="RUNS" value={display(reproduction?.runs)} />
        <MetricCard label="STATUS" value={display(comparison?.status)} />
      </div>

      <SectionHeader title="PAPER RESULT" meta={paper?.metric || 'BACKEND RESULT'} />
      <BrutalCard>
        <div className="kv"><span>Metric</span><strong>{display(paper?.metric)}</strong></div>
        <div className="kv"><span>Reported value</span><strong>{display(paper?.reported_value)}</strong></div>
        <div className="kv"><span>Evidence</span><strong>{evidenceText(paper?.metric_evidence)}</strong></div>
      </BrutalCard>

      <SectionHeader title="REPRODUCTION" meta={reproduction?.metric || 'BACKEND VALIDATION'} />
      <BrutalCard>
        <div className="kv"><span>Runs</span><strong>{display(reproduction?.runs)}</strong></div>
        <div className="kv"><span>Metric</span><strong>{display(reproduction?.metric)}</strong></div>
        <div className="kv"><span>Mean</span><strong>{display(reproduction?.mean)}</strong></div>
        <div className="kv"><span>Standard deviation</span><strong>{display(reproduction?.std)}</strong></div>
        {Object.entries(reproduction?.metrics || {}).map(([name, summary]) => (
          <div className="kv" key={name}>
            <span>{name}</span>
            <strong>
              {Object.entries(summary).map(([key, value]) => `${key}: ${value}`).join(' · ')}
            </strong>
          </div>
        ))}
      </BrutalCard>

      <SectionHeader title="COMPARISON" meta={comparison?.status?.toUpperCase() || 'NOT AVAILABLE'} />
      {comparison ? (
        <BrutalCard>
          <div className="kv"><span>Metric</span><strong>{display(comparison.metric)}</strong></div>
          <div className="kv"><span>Paper value</span><strong>{display(comparison.paper_value)}</strong></div>
          <div className="kv"><span>Reproduced value</span><strong>{display(comparison.reproduced_value)}</strong></div>
          <div className="kv"><span>Absolute difference</span><strong>{display(comparison.absolute_difference)}</strong></div>
          <div className="kv"><span>Relative difference</span><strong>{display(comparison.relative_difference_percent, '%')}</strong></div>
          <div className="kv"><span>Status</span><strong>{display(comparison.status)}</strong></div>
        </BrutalCard>
      ) : <div className="field-hint">The backend did not return a comparable paper/reproduction metric.</div>}

      {chartData.length > 0 ? (
        <>
          <SectionHeader title="PAPER VS REPRODUCED" meta={comparison.metric || ''} />
          <BrutalCard><ComparisonChart data={chartData} /></BrutalCard>
        </>
      ) : null}

      <SectionHeader title="EXPLANATION" />
      {results?.explanation?.length ? (
        <BrutalCard>
          {results.explanation.map((item, index) => (
            <div className="kv" key={`${item.parameter || item.category || 'explanation'}-${index}`}>
              <span>{display(item.parameter || item.category)} · {display(item.status)}</span>
              <strong>
                {display(item.reason || item.message)}
                {item.paper_value !== undefined ? ` · paper ${display(item.paper_value)}` : ''}
                {item.code_value !== undefined ? ` · code ${display(item.code_value)}` : ''}
                {item.confidence !== undefined ? ` · ${Math.round(item.confidence * 100)}% confidence` : ''}
              </strong>
            </div>
          ))}
        </BrutalCard>
      ) : <div className="field-hint">No explanation was returned by the backend.</div>}

      <SectionHeader title="NEXT STEP" meta="08 / REPORT" />
      <BrutalCard>
        <div className="kv" style={{ border: 0, padding: 0 }}>
          <span>Signal</span>
          <strong>{comparison ? `${display(comparison.status)} · ${display(comparison.metric)}` : 'Comparison not available'}</strong>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/root-cause')}>ROOT CAUSE ANALYSIS</Button>
          <Button variant="ghost" onClick={() => navigate('/report')}>OPEN REPORT</Button>
        </div>
      </BrutalCard>
    </section>
  )
}
