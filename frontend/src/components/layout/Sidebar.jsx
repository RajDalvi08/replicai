import { NavLink } from 'react-router-dom'
import { getProject } from '../../data'

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
  const project = getProject()

  return (
    <aside className="sidebar">
      <NavLink to="/" className="logo">
        <div className="logo-kicker">LAB / CONSOLE</div>
        <div className="logo-name">ReplicAI</div>
        <div className="logo-sub">ML REPRODUCIBILITY</div>
      </NavLink>
      <nav className="nav">
        {links.map((link) => (
          <NavLink key={link.to} to={link.to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <span className="nav-num">{link.num}</span>
            <span>{link.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-foot">
        <div className="status-row">
          <span>Project</span>
          <strong className="status-value ok">{project.projectStatus}</strong>
        </div>
        <div className="status-row">
          <span>Repository</span>
          <strong className="status-value ok">{project.repository.status}</strong>
        </div>
        <div className="status-row">
          <span>System</span>
          <strong className="status-value ok">{project.systemStatus}</strong>
        </div>
      </div>
    </aside>
  )
}
