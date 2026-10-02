import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { useExperiment } from '../../experiment'

const links = [
  { to: '/dashboard', num: '01', label: 'Dashboard' },
  { to: '/experiments', num: '02', label: 'Experiments' },
  { to: '/evidence', num: '03', label: 'Evidence Graph' },
  { to: '/execution', num: '04', label: 'Execution' },
  { to: '/results', num: '05', label: 'Results' },
  { to: '/root-cause', num: '06', label: 'Root Cause' },
  { to: '/report', num: '07', label: 'Report' },
]

export default function Sidebar() {
  const { paperId, repositoryId, codeAnalysis } = useExperiment()
  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebar-collapsed')
    return saved === 'true'
  })

  useEffect(() => {
    localStorage.setItem('sidebar-collapsed', collapsed)
  }, [collapsed])

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <button
        className="sidebar-toggle"
        onClick={() => setCollapsed((prev) => !prev)}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d={collapsed ? 'M6 3L11 8L6 13' : 'M10 3L5 8L10 13'}
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      <NavLink to="/" className="logo">
        <div className="logo-kicker">LAB / CONSOLE</div>
        <div className="logo-name">ReplicAI</div>
        <div className="logo-sub">ML REPRODUCIBILITY</div>
      </NavLink>
      <nav className="nav">
        {links.map((link) => (
          <NavLink key={link.to} to={link.to} data-tooltip={link.label} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-num">{link.num}</span>
            <span className="nav-label">{link.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-foot">
        <div className="status-row">
          <span>Project</span>
          <strong className={`status-value ${paperId ? 'ok' : ''}`}>{paperId ? 'ANALYZED' : 'NOT STARTED'}</strong>
        </div>
        <div className="status-row">
          <span>Repository</span>
          <strong className={`status-value ${repositoryId ? 'ok' : ''}`}>{codeAnalysis?.repository?.analysis_status || 'NOT ANALYZED'}</strong>
        </div>
        <div className="status-row">
          <span>System</span>
          <strong className="status-value">{repositoryId ? `REPO ${repositoryId}` : 'READY'}</strong>
        </div>
      </div>
    </aside>
  )
}
