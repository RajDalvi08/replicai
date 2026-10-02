import { useExperiment } from '../../experiment'
import { useTheme } from '../../theme'
import StatusBadge from '../ui/StatusBadge'

export default function Topbar() {
  const { selectedExperiment } = useExperiment()
  const { theme, toggleTheme } = useTheme()
  const paper = Number(selectedExperiment.paperMetric)
  const paperText = Number.isFinite(paper) ? `${paper.toFixed(2)}%` : 'N/A'

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="topbar-title">REPLICAI · TRANSFORMER STUDY</div>
        <span className={`system-chip ${selectedExperiment.status === 'FAILED' ? 'FAILED' : 'ACTIVE'}`}>
          {selectedExperiment.status === 'FAILED' ? 'BLOCKED' : 'ACTIVE'}
        </span>
        <button type="button" className="theme-toggle" onClick={toggleTheme} aria-label="Toggle color theme">
          {theme === 'dark' ? 'MODE LIGHT' : 'MODE DARK'}
        </button>
      </div>
      <div className="topbar-meta" aria-label="Study status">
        <div className="topbar-stat">
          <span>EXP</span>
          <strong>{selectedExperiment.id}</strong>
        </div>
        <div className="topbar-stat">
          <span>READINESS</span>
          <strong>{selectedExperiment.readiness}%</strong>
        </div>
        <div className="topbar-stat">
          <span>PAPER</span>
          <strong>{paperText}</strong>
        </div>
        <StatusBadge status={selectedExperiment.reproducibility || selectedExperiment.status} />
      </div>
    </header>
  )
}
