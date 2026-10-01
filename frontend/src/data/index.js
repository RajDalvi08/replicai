import { mockProject } from './mockProject'
import { mockExperiments } from './mockExperiments'
import { mockEvidence } from './mockEvidence'
import { mockRuns } from './mockRuns'
import { mockRootCause } from './mockRootCause'

export { mockProject, mockExperiments, mockEvidence, mockRuns, mockRootCause }

export function getProject() {
  return mockProject
}

export function getExperiments() {
  return mockExperiments
}

export function getExperiment(id) {
  return mockExperiments.find((item) => item.id === id) ?? mockExperiments.find((item) => item.id === mockProject.selectedExperimentId)
}

export function getSelectedExperiment() {
  return getExperiment(mockProject.selectedExperimentId)
}

export function getEvidence() {
  return mockEvidence
}

export function getRuns() {
  return mockRuns
}

export function getRootCause() {
  return mockRootCause
}

export function getReport() {
  const experiment = getSelectedExperiment()
  const runs = getRuns()
  const rootCause = getRootCause()
  const project = getProject()

  return {
    projectSummary: `${project.papers} paper · ${project.experimentCount} experiments · selected ${experiment.id}`,
    paper: project.paperName,
    paperFile: project.paperFile,
    repository: project.repository.url,
    experiment,
    readiness: experiment.readiness,
    executionSummary: `${runs.runCount} completed sandbox runs`,
    paperResult: project.paperResult,
    reproduced: project.reproduced,
    gap: project.gap,
    rootCause,
    evidence: [
      `Paper: ${rootCause.evidence.paper}`,
      `Code: ${rootCause.evidence.code}`,
    ],
    finalStatus: 'PARTIAL — UNDER REVIEW',
  }
}
