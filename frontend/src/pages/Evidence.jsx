import { getEvidence } from '../data'
import EvidenceGraph from '../components/graph/EvidenceGraph'
import SectionHeader from '../components/ui/SectionHeader'

export default function EvidencePage() {
  const evidence = getEvidence()

  return (
    <section className="page">
      <div className="page-kicker">05 / PROVENANCE</div>
      <h1 className="page-title">EVIDENCE GRAPH</h1>
      <p className="page-copy">
        Paper claims, repository files, configuration values, and execution metrics are linked as a single evidence chain.
      </p>
      <SectionHeader title="E2 TRACE" meta="PAPER → CODE → RUN" />
      <div className="legend">
        {evidence.legend.map((item) => (
          <div className="legend-item" key={item.id}>
            <span className={`swatch ${item.tone}`} />
            {item.label}
          </div>
        ))}
      </div>
      <EvidenceGraph nodes={evidence.nodes} edges={evidence.edges} />
    </section>
  )
}
