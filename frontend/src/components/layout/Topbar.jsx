import { useExperiment } from '../../experiment'
import { useTheme } from '../../theme'
import StatusBadge from '../ui/StatusBadge'

export default function Topbar() {
  const { selectedExperiment, selectedExperimentId, codeAnalysis } = useExperiment()
  const { theme, toggleTheme } = useTheme()
  const reported = selectedExperiment
    ? Object.values(selectedExperiment.reported_results || {})[0]
    : null
  const paperText = reported?.value ?? reported ?? 'Not available'
  const readiness = codeAnalysis?.readiness?.overall_score

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="topbar-title">REPLICAI · TRANSFORMER STUDY</div>
        <span className={`system-chip ${selectedExperiment ? 'ACTIVE' : 'FAILED'}`}>
          {selectedExperiment ? 'ACTIVE' : 'NO PAPER'}
        </span>
        <button type="button" className="theme-toggle" onClick={toggleTheme} aria-label="Toggle color theme">
          {theme === 'dark' ? 'MODE LIGHT' : 'MODE DARK'}
        </button>
      </div>
      <div className="topbar-meta" aria-label="Study status">
        <div className="topbar-stat">
          <span>EXP</span>
          <strong>{selectedExperimentId || '—'}</strong>
        </div>
        <div className="topbar-stat">
          <span>READINESS</span>
          <strong>{readiness === undefined ? '—' : `${readiness.toFixed(1)}%`}</strong>
        </div>
        <div className="topbar-stat">
          <span>PAPER</span>
          <strong>{paperText}</strong>
        </div>
        {selectedExperiment ? <StatusBadge status={codeAnalysis?.repository?.analysis_status || 'EXTRACTED'} /> : null}
      </div>
    </header>
  )
}
