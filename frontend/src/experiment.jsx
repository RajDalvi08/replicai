import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'

const STORAGE_KEY = 'replicai-project-state'
const ExperimentContext = createContext(null)

function readState() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    const value = saved ? JSON.parse(saved) : {}
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {}
  } catch {
    return {}
  }
}

function experimentKey(experiment) {
  return experiment?.experiment_key || experiment?.experiment_id || experiment?.id || ''
}

export function ExperimentProvider({ children }) {
  const [state, setState] = useState(readState)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch {
      // Keep the current session usable if browser storage is unavailable.
    }
  }, [state])

  const setPaperAnalysis = useCallback((paperAnalysis) => {
    const experiments = paperAnalysis.experiments || []
    const selectedExperiment = experiments[0] || null
    setState({
      paperId: paperAnalysis.paper_id,
      paperAnalysis,
      experiments,
      selectedExperimentId: experimentKey(selectedExperiment),
      repositoryId: null,
      repositoryUrl: '',
      codeAnalysis: null,
      runId: null,
      run: null,
      validation: null,
      results: null,
    })
  }, [])

  const setExperiments = useCallback((experiments) => {
    setState((current) => ({
      ...current,
      experiments,
      selectedExperimentId:
        current.selectedExperimentId ||
        experimentKey(experiments[0]),
    }))
  }, [])

  const setSelectedExperimentId = useCallback((selectedExperimentId) => {
    setState((current) => {
      if (current.selectedExperimentId === selectedExperimentId) return current
      return {
        ...current,
        selectedExperimentId,
        repositoryId: null,
        repositoryUrl: '',
        codeAnalysis: null,
        runId: null,
        run: null,
        validation: null,
        results: null,
      }
    })
  }, [])

  const setCodeAnalysis = useCallback((codeAnalysis, repositoryUrl) => {
    setState((current) => ({
      ...current,
      repositoryId: codeAnalysis.repository?.id || null,
      repositoryUrl,
      codeAnalysis,
      runId: null,
      run: null,
      validation: null,
      results: null,
    }))
  }, [])

  const setRun = useCallback((runId, run) => {
    setState((current) => ({ ...current, runId, run }))
  }, [])

  const setValidation = useCallback((validation) => {
    setState((current) => ({ ...current, validation }))
  }, [])

  const setResults = useCallback((results) => {
    setState((current) => ({ ...current, results }))
  }, [])

  const reset = useCallback(() => setState({}), [])

  const selectedExperiment =
    state.experiments?.find(
      (item) => experimentKey(item) === state.selectedExperimentId,
    ) || state.paperAnalysis?.experiments?.find(
      (item) => experimentKey(item) === state.selectedExperimentId,
    ) || null

  const selectedExperimentDatabaseId =
    state.experiments?.find(
      (item) => experimentKey(item) === state.selectedExperimentId,
    )?.experiment_id || null

  const value = useMemo(
    () => ({
      ...state,
      selectedExperiment,
      selectedExperimentDatabaseId,
      setPaperAnalysis,
      setExperiments,
      setSelectedExperimentId,
      setCodeAnalysis,
      setRun,
      setValidation,
      setResults,
      reset,
    }),
    [
      state,
      selectedExperiment,
      selectedExperimentDatabaseId,
      setPaperAnalysis,
      setExperiments,
      setSelectedExperimentId,
      setCodeAnalysis,
      setRun,
      setValidation,
      setResults,
      reset,
    ],
  )

  return <ExperimentContext.Provider value={value}>{children}</ExperimentContext.Provider>
}

export function useExperiment() {
  const context = useContext(ExperimentContext)
  if (!context) {
    throw new Error('useExperiment must be used within an ExperimentProvider')
  }
  return context
}
