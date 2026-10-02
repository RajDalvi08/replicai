import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ExperimentProvider } from './experiment'
import AppLayout from './components/layout/AppLayout'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import Experiments from './pages/Experiments'
import ExperimentDetails from './pages/ExperimentDetails'
import Evidence from './pages/Evidence'
import Execution from './pages/Execution'
import Results from './pages/Results'
import RootCause from './pages/RootCause'
import Report from './pages/Report'

export default function App() {
  return (
    <ExperimentProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Landing />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/experiments" element={<Experiments />} />
            <Route path="/experiments/:id" element={<ExperimentDetails />} />
            <Route path="/evidence" element={<Evidence />} />
            <Route path="/execution" element={<Execution />} />
            <Route path="/results" element={<Results />} />
            <Route path="/root-cause" element={<RootCause />} />
            <Route path="/report" element={<Report />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ExperimentProvider>
  )
}
