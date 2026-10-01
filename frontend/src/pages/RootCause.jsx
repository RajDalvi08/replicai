import { useNavigate } from 'react-router-dom'
import { getRootCause } from '../data'
import BrutalCard from '../components/ui/BrutalCard'
import MetricCard from '../components/ui/MetricCard'
import SectionHeader from '../components/ui/SectionHeader'

export default function RootCause() {
  const root = getRootCause()
  const navigate = useNavigate()

  return (
    <section className="page">
      <div className="page-kicker">08 / DEBUG</div>
      <h1 className="page-title">ROOT CAUSE ANALYSIS</h1>
      <div className="grid-metrics">
        <MetricCard label="MAIN FINDING" value={root.title} tone="warn" />
        <MetricCard label="PAPER" value={root.paperValue} />
        <MetricCard label="CODE" value={root.codeValue} tone="warn" />
        <MetricCard label="CONFIDENCE" value={root.confidence} />
      </div>
      <SectionHeader title="ROOT CAUSE" meta={root.finding} />
      <BrutalCard>
        <p className="page-copy" style={{ margin: 0 }}>
          {root.impact}
        </p>
      </BrutalCard>
      <SectionHeader title="EVIDENCE" />
      <div className="split">
        <BrutalCard>
          <div className="metric-label">PAPER</div>
          <div className="metric-value" style={{ fontSize: 20 }}>
            {root.evidence.paper}
          </div>
        </BrutalCard>
        <BrutalCard>
          <div className="metric-label">CODE</div>
          <div className="metric-value" style={{ fontSize: 20, color: 'var(--warning)' }}>
            {root.evidence.code}
          </div>
        </BrutalCard>
      </div>
      <SectionHeader title="EVIDENCE CHAIN" />
      <div className="chain">
        {root.chain.map((item, index) => (
          <span key={item.id} style={{ display: 'contents' }}>
            <span className="chain-node" onClick={() => navigate('/evidence')} onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') navigate('/evidence')
            }} role="link" tabIndex={0}>{item.label}</span>
            {index < root.chain.length - 1 ? <span className="workflow-arrow">↓</span> : null}
          </span>
        ))}
      </div>
    </section>
  )
}
