import { mockExperiments } from '../data/mockExperiments'
import { mockProject } from '../data/mockProject'

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8001').replace(/\/+$/, '')
const FORCE_DEMO = String(import.meta.env.VITE_FORCE_DEMO ?? '').toLowerCase() === 'true'
const HEALTH_TIMEOUT_MS = 4000

const backendState = {
  checked: false,
  available: false,
  pending: null,
}

function findExperiment(experimentId) {
  const selectedId = experimentId || mockProject.selectedExperimentId || mockExperiments[0]?.id
  return mockExperiments.find((experiment) => experiment.id === selectedId) || mockExperiments[0]
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

function buildMockExperiments() {
  return mockExperiments.map((experiment) => ({
    ...clone(experiment),
    experiment_id: experiment.id,
    experiment_key: experiment.id,
    title: experiment.name,
    description: experiment.summary,
    metric: 'BLEU',
    extraction_confidence: 0.95,
    reported_results: {
      primary: { value: experiment.paperMetric, metric: 'BLEU' },
    },
  }))
}

function buildMockPaperAnalysis() {
  return {
    paper_id: 'mock-paper-1',
    filename: 'paper.pdf',
    page_count: 12,
    warnings: ['Using locally bundled mock data while the backend is unavailable.'],
    experiments: buildMockExperiments(),
  }
}

function buildMockExperimentDetail(experimentId) {
  const experiment = findExperiment(experimentId)
  const fields = [
    ['dataset', experiment.parameters?.dataset || 'WMT 2014 EN-DE'],
    ['model', experiment.parameters?.model || 'Transformer-Base'],
    ['optimizer', experiment.parameters?.optimizer || 'Adam'],
    ['learning_rate', experiment.parameters?.learningRate || '1e-4'],
    ['batch_size', experiment.parameters?.batchSize?.paper ?? experiment.parameters?.batchSize ?? 64],
    ['epochs', experiment.parameters?.epochs || 100000],
    ['scheduler', experiment.parameters?.scheduler || 'Warmup'],
    ['weight_decay', experiment.parameters?.weightDecay || 0.0],
    ['dropout', experiment.parameters?.dropout || experiment.paperConfig?.dropout || 0.1],
    ['random_seed', experiment.parameters?.seed || 42],
    ['metric', experiment.metric || 'BLEU'],
  ]

  return {
    experiment_id: experiment.id,
    experiment_key: experiment.id,
    title: experiment.name,
    description: experiment.summary,
    metric: experiment.metric || 'BLEU',
    extraction_confidence: 0.95,
    reported_results: {
      primary: { value: experiment.paperMetric, metric: experiment.metric || 'BLEU' },
    },
    parameters: fields.map(([field_name, value]) => ({ field_name, value })),
    evidence: [
      {
        field: 'batch_size',
        page: 5,
        confidence: 0.96,
        quote: 'Batch size is set to 64 in the paper training configuration.',
      },
      {
        field: 'model',
        page: 6,
        confidence: 0.94,
        quote: 'Transformer-Base architecture is described in the paper.',
      },
      {
        field: 'learning_rate',
        page: 7,
        confidence: 0.9,
        quote: 'The paper reports a learning rate of 1e-4.',
      },
    ],
  }
}

function buildMockReadiness() {
  return {
    overall_score: 88.4,
    status: 'READY',
    items: [
      {
        category: 'paper_evidence',
        status: 'MATCHED',
        score: 0.94,
        reason: 'The paper provides clear parameter and evaluation evidence.',
      },
      {
        category: 'repository_coverage',
        status: 'MATCHED',
        score: 0.9,
        reason: 'The repository contains the main training and evaluation files.',
      },
      {
        category: 'parameter_alignment',
        status: 'PARTIAL',
        score: 0.72,
        reason: 'One key training parameter diverges from the paper specification.',
      },
    ],
  }
}

function buildMockCodeAnalysis() {
  return {
    repository: {
      id: 'mock-repo-1',
      url: 'github.com/org/replicai-transformer-study',
      analysis_status: 'READY',
      python_file_count: 21,
    },
    readiness: buildMockReadiness(),
    mappings: [
      {
        paper_field: 'batch_size',
        status: 'mismatch',
        confidence: 0.93,
        paper_value: 64,
        code_value: 32,
        reason: 'Paper states a batch size of 64 while the repository config uses 32.',
        evidence: {
          file: 'config.yaml',
          line_start: 12,
          quote: 'batch_size: 32',
        },
      },
      {
        paper_field: 'learning_rate',
        status: 'matched',
        confidence: 0.98,
        paper_value: '1e-4',
        code_value: '1e-4',
        reason: 'The learning rate is present in both the paper and the repository.',
        evidence: {
          file: 'train.py',
          line_start: 88,
          quote: 'learning_rate = 1e-4',
        },
      },
      {
        paper_field: 'optimizer',
        status: 'matched',
        confidence: 0.96,
        paper_value: 'Adam',
        code_value: 'Adam',
        reason: 'Optimizer configuration is aligned between the paper and implementation.',
        evidence: {
          file: 'train.py',
          line_start: 104,
          quote: 'optimizer = Adam',
        },
      },
    ],
    entry_points: [{ path: 'train.py', role: 'training_entrypoint' }],
    code_parameters: [
      { name: 'model', value: 'Transformer-Base' },
      { name: 'optimizer', value: 'Adam' },
      { name: 'learning_rate', value: '1e-4' },
    ],
    pipeline: {
      stages: [
        { name: 'dataset', status: 'ready' },
        { name: 'model', status: 'ready' },
        { name: 'training', status: 'ready' },
        { name: 'evaluation', status: 'ready' },
      ],
    },
    optimizers: [{ name: 'Adam' }],
    schedulers: [{ name: 'Warmup' }],
    loss_functions: [{ name: 'CrossEntropyLoss' }],
    metrics: [{ name: 'BLEU' }],
    repository_url: 'github.com/org/replicai-transformer-study',
  }
}

function buildMockResults(experimentId) {
  const experiment = findExperiment(experimentId)
  const paperValue = Number(experiment?.paperMetric ?? 87.6)
  const reproducedValue = Number(experiment?.reproduced ?? 84.23)
  const absoluteDifference = Number((paperValue - reproducedValue).toFixed(2))
  const relativeDifferencePercent = Number(((absoluteDifference / paperValue) * 100).toFixed(2))

  return {
    paper: {
      metric: 'BLEU',
      reported_value: paperValue,
      metric_evidence: {
        quote: 'The paper reports 87.6 BLEU on the held-out validation split.',
        page: 8,
        confidence: 0.96,
      },
    },
    reproduction: {
      metric: 'BLEU',
      runs: 3,
      mean: reproducedValue,
      std: 0.15,
      metrics: {
        accuracy: {
          mean: reproducedValue,
          std: 0.15,
          min: 84.1,
          max: 84.4,
        },
      },
    },
    comparison: {
      metric: 'BLEU',
      paper_value: paperValue,
      reproduced_value: reproducedValue,
      absolute_difference: absoluteDifference,
      relative_difference_percent: relativeDifferencePercent,
      status: 'UNDER REVIEW',
    },
    explanation: [
      {
        parameter: 'batch_size',
        status: 'mismatch',
        reason: 'The repository config sets batch size to 32, while the paper reports a batch size of 64.',
        paper_value: 64,
        code_value: 32,
        confidence: 0.93,
      },
      {
        parameter: 'warmup',
        status: 'matched',
        reason: 'Both the paper and repository preserve the 4000-step warmup schedule.',
        paper_value: 4000,
        code_value: 4000,
        confidence: 0.91,
      },
    ],
  }
}

async function ensureBackendAvailability() {
  if (FORCE_DEMO) {
    backendState.checked = true
    backendState.available = false
    return false
  }

  if (backendState.checked) {
    return backendState.available
  }

  if (!backendState.pending) {
    backendState.pending = (async () => {
      try {
        const controller = new AbortController()
        const timeout = window.setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS)

        const response = await fetch(`${API_BASE_URL}/health`, {
          method: 'GET',
          signal: controller.signal,
          headers: { Accept: 'application/json' },
        })

        window.clearTimeout(timeout)

        const payload = await response.json().catch(() => null)
        backendState.available = response.ok && payload?.status === 'ok'
      } catch {
        backendState.available = false
      } finally {
        backendState.checked = true
        backendState.pending = null
      }
    })()
  }

  await backendState.pending
  return backendState.available
}

function getMockFallback(path, options = {}) {
  const maybePath = path.split('?')[0]

  if (maybePath === '/health') {
    return { status: 'ok' }
  }

  if (maybePath === '/api/v1/paper/analyze') {
    return buildMockPaperAnalysis()
  }

  if (maybePath.startsWith('/api/v1/paper/') && maybePath.endsWith('/experiments')) {
    return buildMockExperiments()
  }

  if (maybePath.startsWith('/api/v1/paper/')) {
    return buildMockPaperAnalysis()
  }

  if (maybePath.startsWith('/api/v1/experiment/') && maybePath.includes('/results')) {
    const experimentId = maybePath.split('/')[3]
    return buildMockResults(experimentId)
  }

  if (maybePath.startsWith('/api/v1/experiment/run/')) {
    const runId = maybePath.split('/').at(-1)
    return {
      run_id: runId,
      status: 'completed',
      exit_code: 0,
      execution_time_seconds: 124,
      stdout: 'Mock execution completed successfully.\naccuracy: 84.23%',
      metrics: { accuracy: 84.23 },
    }
  }

  if (maybePath === '/api/v1/experiment/run') {
    return {
      run_id: 'mock-run-1',
      status: 'completed',
      exit_code: 0,
      execution_time_seconds: 124,
      stdout: 'Mock execution completed successfully.\naccuracy: 84.23%',
      metrics: { accuracy: 84.23 },
    }
  }

  if (maybePath === '/api/v1/experiment/validate') {
    return {
      status: 'completed',
      runs: [
        { run: 1, status: 'completed', exit_code: 0, execution_time_seconds: 122 },
        { run: 2, status: 'completed', exit_code: 0, execution_time_seconds: 123 },
        { run: 3, status: 'completed', exit_code: 0, execution_time_seconds: 124 },
      ],
    }
  }

  if (maybePath.startsWith('/api/v1/experiment/')) {
    const experimentId = maybePath.split('/')[3]
    return buildMockExperimentDetail(experimentId)
  }

  if (maybePath === '/api/v1/code/analyze') {
    return buildMockCodeAnalysis()
  }

  if (maybePath.startsWith('/api/v1/repository/') && maybePath.includes('/mappings')) {
    return { mappings: buildMockCodeAnalysis().mappings }
  }

  if (maybePath.startsWith('/api/v1/repository/') && maybePath.includes('/readiness')) {
    return { readiness: buildMockReadiness() }
  }

  if (maybePath.startsWith('/api/v1/repository/')) {
    return buildMockCodeAnalysis()
  }

  if (options.method === 'POST') {
    return { ok: true }
  }

  return null
}

async function request(path, options = {}) {
  const backendAvailable = await ensureBackendAvailability()
  if (!backendAvailable || FORCE_DEMO) {
    const fallbackResult = getMockFallback(path, options)
    if (fallbackResult) return fallbackResult
  }

  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options)
  } catch (error) {
    const fallbackResult = getMockFallback(path, options)
    if (fallbackResult) return fallbackResult
    throw new Error(
      `Unable to connect to the ReplicAI backend at ${API_BASE_URL}. Check that it is running and allows this frontend origin.`,
      { cause: error },
    )
  }

  const contentType = response.headers.get('content-type') || ''
  let body = null
  if (contentType.includes('application/json')) {
    try {
      body = await response.json()
    } catch (error) {
      throw new Error('The backend returned invalid JSON.', { cause: error })
    }
  } else {
    const text = await response.text()
    body = text ? { message: text } : null
  }

  if (!response.ok) {
    const detail = body?.detail
    const validationMessage = Array.isArray(detail)
      ? detail.map((item) => [item.loc?.join('.'), item.msg].filter(Boolean).join(': ')).join('; ')
      : ''
    const message =
      body?.message ||
      (typeof detail === 'string' ? detail : detail?.message) ||
      body?.error ||
      validationMessage ||
      `Backend request failed with status ${response.status}.`
    throw new Error(message)
  }

  return body
}

function jsonRequest(method, body) {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }
}

export function analyzePaper(file) {
  const body = new FormData()
  body.append('file', file)
  return request('/api/v1/paper/analyze', { method: 'POST', body })
}

export function getPaper(paperId) {
  return request(`/api/v1/paper/${encodeURIComponent(paperId)}`)
}

export function getExperiments(paperId) {
  return request(`/api/v1/paper/${encodeURIComponent(paperId)}/experiments`)
}

export function getExperiment(experimentId) {
  return request(`/api/v1/experiment/${encodeURIComponent(experimentId)}`)
}

export function analyzeCode(payload) {
  return request('/api/v1/code/analyze', jsonRequest('POST', payload))
}

export function getRepository(repositoryId) {
  return request(`/api/v1/repository/${encodeURIComponent(repositoryId)}`)
}

export function getRepositoryFiles(repositoryId) {
  return request(`/api/v1/repository/${encodeURIComponent(repositoryId)}/files`)
}

export function getMappings(repositoryId, experimentId) {
  const query = experimentId ? `?experiment_id=${encodeURIComponent(experimentId)}` : ''
  return request(`/api/v1/repository/${encodeURIComponent(repositoryId)}/mappings${query}`)
}

export function getReadiness(repositoryId, experimentId) {
  const query = experimentId ? `?experiment_id=${encodeURIComponent(experimentId)}` : ''
  return request(`/api/v1/repository/${encodeURIComponent(repositoryId)}/readiness${query}`)
}

export function getCodeAnalysis(experimentId) {
  return request(`/api/v1/experiment/${encodeURIComponent(experimentId)}/code-analysis`)
}

export function runExperiment(payload) {
  return request('/api/v1/experiment/run', jsonRequest('POST', payload))
}

export function getRun(runId) {
  return request(`/api/v1/experiment/run/${encodeURIComponent(runId)}`)
}

export function validateExperiment(payload) {
  return request('/api/v1/experiment/validate', jsonRequest('POST', payload))
}

export function getResults(experimentId) {
  return request(`/api/v1/experiment/${encodeURIComponent(experimentId)}/results`)
}

export function checkBackendHealth() {
  return ensureBackendAvailability()
}
