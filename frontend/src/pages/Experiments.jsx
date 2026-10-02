import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getExperiments as fetchExperiments } from '../api/client'
import { useExperiment } from '../experiment'
import DataTable from '../components/ui/DataTable'
import Input from '../components/ui/Input'
import SectionHeader from '../components/ui/SectionHeader'

function display(value, suffix = '') {
  return value === null || value === undefined || value === '' ? 'Not available' : `${value}${suffix}`
}

function metricValue(experiment) {
  const result = Object.values(experiment.reported_results || {})[0]
  return result?.value ?? result ?? null
}

export default function Experiments() {
  const navigate = useNavigate()
  const {
    paperId,
    experiments,
    selectedExperimentId,
    setExperiments,
    setSelectedExperimentId,
  } = useExperiment()
  const [query, setQuery] = useState('')
  const [loadedPaperId, setLoadedPaperId] = useState(null)
  const [requestError, setRequestError] = useState(null)

  useEffect(() => {
    if (!paperId) return
    let active = true
    fetchExperiments(paperId)
      .then((response) => {
        if (active) {
          setRequestError(null)
          setExperiments(response)
        }
      })
      .catch((requestError) => {
        if (active) setRequestError({ paperId, message: requestError.message || 'Unable to load experiments.' })
      })
      .finally(() => {
        if (active) setLoadedPaperId(paperId)
      })
    return () => {
      active = false
    }
  }, [paperId, setExperiments])

  const rows = useMemo(
    () =>
      (experiments || [])
        .map((item) => ({
          ...item,
          id: item.experiment_key || item.experiment_id,
          name: item.title || item.description || 'Extracted experiment',
        }))
        .filter((item) => `${item.id} ${item.name}`.toLowerCase().includes(query.toLowerCase())),
    [experiments, query],
  )

  const columns = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'NAME' },
    { key: 'confidence', label: 'EXTRACTION CONFIDENCE', render: (row) => display(row.extraction_confidence) },
    { key: 'metric', label: 'METRIC', render: (row) => display(row.metric) },
    { key: 'reported', label: 'REPORTED VALUE', render: (row) => display(metricValue(row)) },
    { key: 'readiness', label: 'READINESS', render: () => 'Not analyzed' },
  ]
  const loading = Boolean(paperId && loadedPaperId !== paperId)
  const error = requestError && requestError.paperId === paperId ? requestError.message : ''

  const handleRowClick = (row) => {
    setSelectedExperimentId(row.experiment_key || row.experiment_id)
    navigate(`/experiments/${row.experiment_key || row.experiment_id}`)
  }

  return (
    <section className="page">
      <div className="page-kicker">03 / EXPERIMENTS</div>
      <h1 className="page-title">EXPERIMENT INDEX</h1>
      <SectionHeader
        title="EXTRACTED EXPERIMENTS"
        meta={loading ? 'LOADING…' : `${rows.length} EXPERIMENTS`}
      />
      {!paperId ? <div className="field-hint">Analyze a research paper to view its experiments.</div> : null}
      {error ? <div className="field-hint error">{error}</div> : null}
      <div className="toolbar">
        <Input
          className="search"
          placeholder="SEARCH ID / NAME"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>
      <DataTable
        columns={columns}
        rows={rows}
        selectedId={selectedExperimentId}
        onRowClick={handleRowClick}
      />
    </section>
  )
}
