import { getProject, getSelectedExperiment } from '../../data'
import { useTheme } from '../../theme'
import StatusBadge from '../ui/StatusBadge'

export default function Topbar() {
  const project = getProject()
  const experiment = getSelectedExperiment()
  const { theme, toggleTheme } = useTheme()

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="topbar-title">{project.name}</div>
        <span className={`system-chip ${project.status}`}>{project.status}</span>
        <button type="button" className="theme-toggle" onClick={toggleTheme} aria-label="Toggle color theme">
          {theme === 'dark' ? 'MODE LIGHT' : 'MODE DARK'}
        </button>
      </div>
      <div className="topbar-meta">
        <span>EXP {experiment.id}</span>
        <span>READINESS {experiment.readiness}%</span>
        <span>PAPER {project.paperResult.toFixed(2)}%</span>
        <StatusBadge status={experiment.reproducibility || experiment.status} />
      </div>
    </header>
  )
}
