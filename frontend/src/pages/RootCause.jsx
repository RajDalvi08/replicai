import { useNavigate } from 'react-router-dom'
import { useExperiment } from '../experiment'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import MetricCard from '../components/ui/MetricCard'
import SectionHeader from '../components/ui/SectionHeader'

function display(value) {
  return value === null || value === undefined || value === '' ? 'Not available' : String(value)
}

export default function RootCause() {
  const { selectedExperimentId, results, codeAnalysis, validation } = useExperiment()
  const navigate = useNavigate()
  const explanations = results?.explanation || []
  const mappings = codeAnalysis?.mappings || []
  const mainFinding = explanations[0] || mappings[0] || null
  const comparison = results?.comparison

  return (
    <section className="page">
      <div className="page-kicker">08 / EXPLANATION</div>
      <h1 className="page-title">{selectedExperimentId || 'EXPERIMENT'} · EXPLANATION</h1>
      <p className="page-copy" style={{ marginBottom: 10 }}>
        Findings below are returned by ReplicAI Code Intelligence and Execution APIs; no frontend-generated cause is substituted.
      </p>
      <div className="grid-metrics">
        <MetricCard label="MAIN FINDING" value={mainFinding ? `${mainFinding.parameter || mainFinding.category || 'Mapping'} · ${mainFinding.status || 'detail'}` : 'Not available'} tone="warn" />
        <MetricCard label="PAPER VALUE" value={display(comparison?.paper_value)} />
        <MetricCard label="REPRODUCED VALUE" value={display(comparison?.reproduced_value)} />
        <MetricCard label="CONFIDENCE" value={mainFinding?.confidence === undefined ? 'Not available' : `${Math.round(mainFinding.confidence * 100)}%`} />
        <MetricCard label="VALIDATION" value={validation?.status || 'Not validated'} />
        <MetricCard label="COMPARISON" value={comparison?.status || 'Not available'} />
      </div>
      <SectionHeader title="BACKEND EXPLANATION" meta={mainFinding?.parameter || 'NOT AVAILABLE'} />
      {explanations.length ? (
        <BrutalCard>
          {explanations.map((item, index) => (
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
      ) : (
        <div className="field-hint">No backend explanation is available. Run validation to generate comparison evidence.</div>
      )}
      <SectionHeader title="MAPPING EVIDENCE" />
      <div className="split">
        {mappings.length ? mappings.map((mapping, index) => (
          <BrutalCard key={`${mapping.paper_field}-${index}`}>
            <div className="metric-label" style={{ color: 'var(--muted)' }}>{mapping.paper_field} · {mapping.status}</div>
            <div className="metric-value" style={{ fontSize: 20, color: 'var(--text)' }}>
              {display(mapping.paper_value)} ↔ {display(mapping.code_value)}
            </div>
            <div className="kv"><span>Reason</span><strong>{display(mapping.reason)}</strong></div>
            <div className="kv"><span>Confidence</span><strong>{Math.round((mapping.confidence || 0) * 100)}%</strong></div>
            {mapping.evidence ? (
              <div className="kv">
                <span>Code evidence</span>
                <strong>
                  {mapping.evidence.file}
                  {mapping.evidence.line_start ? `:${mapping.evidence.line_start}` : ''}
                  {mapping.evidence.quote ? ` · “${mapping.evidence.quote}”` : ''}
                </strong>
              </div>
            ) : null}
          </BrutalCard>
        )) : <div className="field-hint">No repository mapping evidence is available.</div>}
      </div>
      <SectionHeader title="NEXT STEP" meta="09 / REPORT" />
      <BrutalCard>
        <div className="kv" style={{ border: 0, padding: 0 }}>
          <span>Pipeline</span>
          <strong>EXPLANATION → REPORT</strong>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/report')}>OPEN REPORT</Button>
          <Button variant="ghost" onClick={() => navigate('/evidence')}>REVIEW EVIDENCE</Button>
        </div>
      </BrutalCard>
    </section>
  )
}
