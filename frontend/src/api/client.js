const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8001').replace(/\/+$/, '')

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, options)
  } catch (error) {
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
