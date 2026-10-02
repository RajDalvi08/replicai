import { useNavigate } from 'react-router-dom'
import { useExperiment } from '../experiment'
import { getEvidence } from '../data'
import EvidenceGraph from '../components/graph/EvidenceGraph'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import SectionHeader from '../components/ui/SectionHeader'

export default function EvidencePage() {
  const { selectedExperiment } = useExperiment()
  const evidence = getEvidence(selectedExperiment.id)
  const navigate = useNavigate()

  return (
    <section className="page">
      <div className="page-kicker">05 / PROVENANCE</div>
      <h1 className="page-title">EVIDENCE GRAPH</h1>
      <p className="page-copy">
        Paper claims, repository files, configuration values, and execution metrics are linked as a single evidence chain.
      </p>
      <SectionHeader title={`${selectedExperiment.id} TRACE`} meta="PAPER → CODE → RUN" />
      <div className="legend">
        {evidence.legend.map((item) => (
          <div className="legend-item" key={item.id}>
            <span className={`swatch ${item.tone}`} />
            {item.label}
          </div>
        ))}
      </div>
      <EvidenceGraph nodes={evidence.nodes} edges={evidence.edges} />
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
