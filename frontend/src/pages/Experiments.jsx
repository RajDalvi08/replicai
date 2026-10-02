import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useExperiment } from '../experiment'
import { getExperiments } from '../data'
import DataTable from '../components/ui/DataTable'
import Input from '../components/ui/Input'
import SectionHeader from '../components/ui/SectionHeader'
import StatusBadge from '../components/ui/StatusBadge'

const filters = ['ALL', 'READY', 'WARNING', 'FAILED']

function fmt(value, suffix = '') {
  return value === null || value === undefined ? '—' : `${value}${suffix}`
}

export default function Experiments() {
  const navigate = useNavigate()
  const experiments = getExperiments()
  const { selectedExperimentId, setSelectedExperimentId } = useExperiment()
  const [filter, setFilter] = useState('ALL')
  const [query, setQuery] = useState('')

  const rows = useMemo(() => {
    return experiments.filter((item) => {
      const matchesFilter = filter === 'ALL' || item.status === filter
      const haystack = `${item.id} ${item.name}`.toLowerCase()
      return matchesFilter && haystack.includes(query.toLowerCase())
    })
  }, [experiments, filter, query])

  const columns = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'NAME', render: (row) => row.name },
    { key: 'status', label: 'STATUS', render: (row) => <StatusBadge status={row.status} /> },
    { key: 'readiness', label: 'READINESS', render: (row) => `${row.readiness}%` },
    { key: 'codeMatch', label: 'CODE MATCH', render: (row) => `${row.codeMatch}%` },
    { key: 'paperMetric', label: 'PAPER METRIC', render: (row) => `${row.paperMetric}%` },
    { key: 'reproduced', label: 'REPRODUCED', render: (row) => fmt(row.reproduced, '%') },
    { key: 'gap', label: 'GAP', render: (row) => fmt(row.gap, ' pp') },
  ]

  const handleRowClick = (row) => {
    setSelectedExperimentId(row.id)
    navigate(`/experiments/${row.id}`, { replace: false })
  }

  return (
    <section className="page">
      <div className="page-kicker">03 / EXPERIMENTS</div>
      <h1 className="page-title">EXPERIMENT INDEX</h1>
      <SectionHeader title="DETECTED RUNS" meta={`${experiments.length} EXPERIMENTS · SELECTED ${selectedExperimentId}`} />
      <div className="toolbar">
        <div className="filters">
          {filters.map((item) => (
            <button
              key={item}
              className={`filter-chip ${filter === item ? 'active' : ''}`}
              onClick={() => setFilter(item)}
              type="button"
            >
              {item}
            </button>
          ))}
        </div>
        <Input
          className="search"
          placeholder="SEARCH ID / NAME"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
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
