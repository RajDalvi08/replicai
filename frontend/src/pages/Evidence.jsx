import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getMappings } from '../api/client'
import { useExperiment } from '../experiment'
import EvidenceGraph from '../components/graph/EvidenceGraph'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import SectionHeader from '../components/ui/SectionHeader'

function graphState(status) {
  if (status === 'matched') return 'verified'
  if (status === 'mismatch' || status === 'mismatched' || status === 'missing_in_code') return 'mismatch'
  return 'partial'
}

function display(value) {
  return value === null || value === undefined || value === '' ? 'Not available' : String(value)
}

export default function EvidencePage() {
  const navigate = useNavigate()
  const {
    paperAnalysis,
    selectedExperiment,
    selectedExperimentId,
    selectedExperimentDatabaseId,
    repositoryId,
    codeAnalysis,
  } = useExperiment()
  const [mappings, setMappings] = useState(codeAnalysis?.mappings || [])
  const [loadedRequestKey, setLoadedRequestKey] = useState(null)
  const [requestError, setRequestError] = useState(null)
  const requestKey = `${repositoryId || ''}:${selectedExperimentDatabaseId || ''}`

  useEffect(() => {
    if (!repositoryId) return
    let active = true
    getMappings(repositoryId, selectedExperimentDatabaseId)
      .then((response) => {
        if (active) {
          setRequestError(null)
          setMappings(response.mappings || [])
        }
      })
      .catch((requestError) => {
        if (active) {
          setRequestError({
            repositoryId,
            message: requestError.message || 'Unable to load paper-to-code mappings.',
          })
        }
      })
      .finally(() => {
        if (active) setLoadedRequestKey(requestKey)
      })
    return () => {
      active = false
    }
  }, [repositoryId, selectedExperimentDatabaseId, requestKey])

  const { nodes, edges } = useMemo(() => {
    const nodes = [
      {
        id: 'paper',
        type: 'evidence',
        position: { x: 80, y: 30 },
        data: {
          kicker: 'RESEARCH PAPER',
          title: paperAnalysis?.filename || 'Paper',
          meta: `${paperAnalysis?.page_count ?? 'Not available'} pages`,
          state: 'verified',
        },
      },
      {
        id: 'experiment',
        type: 'evidence',
        position: { x: 80, y: 200 },
        data: {
          kicker: 'SELECTED EXPERIMENT',
          title: selectedExperiment?.title || selectedExperimentId || 'Experiment',
          meta: selectedExperimentId || 'Not selected',
          state: 'partial',
        },
      },
    ]
    const edges = [{ id: 'paper-experiment', source: 'paper', target: 'experiment', type: 'smoothstep' }]
    mappings.forEach((mapping, index) => {
      const id = `mapping-${index}`
      const col = index % 2
      const row = Math.floor(index / 2)
      const evidence = mapping.evidence
      const source = evidence
        ? `${evidence.file}${evidence.line_start ? `:${evidence.line_start}` : ''}`
        : mapping.reason
      nodes.push({
        id,
        type: 'evidence',
        position: { x: col ? 440 : 80, y: 390 + row * 190 },
        data: {
          kicker: `${mapping.paper_field} · ${mapping.status}`,
          title: `${display(mapping.paper_value)} ↔ ${display(mapping.code_value)}`,
          meta: `${source} · ${Math.round((mapping.confidence || 0) * 100)}% confidence`,
          state: graphState(mapping.status),
        },
      })
      edges.push({ id: `experiment-${id}`, source: 'experiment', target: id, type: 'smoothstep' })
    })
    return { nodes, edges }
  }, [paperAnalysis, selectedExperiment, selectedExperimentId, mappings])
  const loading = Boolean(repositoryId && loadedRequestKey !== requestKey)
  const error = requestError?.repositoryId === repositoryId ? requestError.message : ''

  return (
    <section className="page">
      <div className="page-kicker">05 / PROVENANCE</div>
      <h1 className="page-title">EVIDENCE GRAPH</h1>
      <p className="page-copy">
        Paper claims, repository files, configuration values, and execution metrics are linked as a single evidence chain.
      </p>
      <SectionHeader title={`${selectedExperimentId || 'NO EXPERIMENT'} TRACE`} meta={loading ? 'LOADING…' : 'PAPER → CODE'} />
      {!repositoryId ? <div className="field-hint">Analyze a repository to view real paper-to-code mappings.</div> : null}
      {error ? <div className="field-hint error">{error}</div> : null}
      <div className="legend">
        {[
          { id: 'matched', label: 'MATCHED', tone: 'success' },
          { id: 'uncertain', label: 'UNCERTAIN / NOT AVAILABLE', tone: 'warning' },
          { id: 'mismatch', label: 'MISMATCH / MISSING', tone: 'error' },
        ].map((item) => (
          <div className="legend-item" key={item.id}>
            <span className={`swatch ${item.tone}`} />
            {item.label}
          </div>
        ))}
      </div>
      {mappings.length ? <EvidenceGraph nodes={nodes} edges={edges} /> : null}
      {repositoryId && !mappings.length && !loading ? (
        <div className="field-hint">The backend returned no mappings for this experiment.</div>
      ) : null}
      <SectionHeader title="PAPER ↔ CODE MAPPINGS" meta={`${mappings.length} MAPPINGS`} />
      {mappings.length ? (
        <BrutalCard>
          {mappings.map((mapping, index) => (
            <div className="kv" key={`${mapping.paper_field}-${index}`}>
              <span>{mapping.paper_field} · {mapping.status} · {Math.round((mapping.confidence || 0) * 100)}%</span>
              <strong>
                {display(mapping.paper_value)} ↔ {display(mapping.code_value)} · {mapping.reason}
                {mapping.evidence?.file ? ` · ${mapping.evidence.file}${mapping.evidence.line_start ? `:${mapping.evidence.line_start}` : ''}` : ''}
                {mapping.evidence?.quote ? ` · “${mapping.evidence.quote}”` : ''}
              </strong>
            </div>
          ))}
        </BrutalCard>
      ) : null}
      <SectionHeader title="NEXT STEP" meta="06 / SANDBOX" />
      <BrutalCard>
        <div className="kv" style={{ border: 0, padding: 0 }}>
          <span>Pipeline</span>
          <strong>EVIDENCE → EXECUTION → COMPARISON → ROOT CAUSE</strong>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <Button onClick={() => navigate('/execution')}>RUN EXPERIMENT</Button>
          <Button variant="ghost" onClick={() => navigate('/results')}>VIEW COMPARISON</Button>
        </div>
      </BrutalCard>
    </section>
  )
}
