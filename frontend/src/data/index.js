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
  const first = mockExperiments.find((item) => item.id === id)
  if (first) return first
  return mockExperiments.find((item) => item.id === mockProject.selectedExperimentId) || mockExperiments[0]
}

export function getSelectedExperimentId() {
  return mockProject.selectedExperimentId || 'E2'
}

export function getSelectedExperiment() {
  return getExperiment(getSelectedExperimentId())
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value))
}

function computeRootCause(experiment) {
  const base = mockRootCause
  const hasGap = typeof experiment.gap === 'number' && Number.isFinite(experiment.gap)
  const gapPp = hasGap ? Math.abs(Number(experiment.gap)) : 0
  const paperBatch = Number(experiment.parameters?.batchSize?.paper || experiment.paperConfig?.batchSize || 64)
  const codeBatch = Number(experiment.parameters?.batchSize?.code || experiment.codeConfig?.batchSize || null)

  if (experiment.id === 'E2') {
    return {
      ...base,
      paperValue: paperBatch,
      codeValue: codeBatch,
      confidence: 'HIGH',
      evidence: base.evidence,
      chain: base.chain,
    }
  }

  if (experiment.status === 'FAILED') {
    const paperTied = Boolean(experiment.paperConfig?.tiedEmbeddings)
    const codeTied = Boolean(experiment.codeConfig?.tiedEmbeddings)
    return {
      title: 'Embedding configuration missing',
      finding: experiment.summary || 'Code path diverges from paper claims.',
      impact:
        'This experiment configuration could not be reproduced because a key architecture switch is documented in the paper but missing from the checked-out repository.',
      paperValue: paperTied ? 1 : 0,
      codeValue: codeTied ? 1 : 0,
      confidence: gapPp >= 2 ? 'HIGH' : 'MEDIUM',
      evidence: {
        paper: `tied embeddings = ${paperTied ? 'true' : 'false'}`,
        code: `tied embeddings = ${codeTied ? 'true' : 'false'}`,
      },
      chain: [
        { id: 'c1', label: 'PAPER §3.4 EMBEDDINGS' },
        { id: 'c2', label: 'CODE model.py line 41' },
        { id: 'c3', label: 'PARAMETER MISMATCH' },
        { id: 'c4', label: 'NO RUNS AVAILABLE' },
      ],
    }
  }

  if (experiment.id === 'E3') {
    const paperSmooth = experiment.paperConfig?.labelSmoothing ?? 0.1
    const codeSmooth = experiment.codeConfig?.labelSmoothing ?? 0.0
    return {
      title: 'Label smoothing mismatch',
      finding: experiment.summary || 'Smoothing factor differs between paper and code.',
      impact:
        'Smoothing hyperparameter diverges; reproduced metrics are expected to under-shoot the paper until the code-side value matches the documented setting.',
      paperValue: paperSmooth,
      codeValue: codeSmooth,
      confidence: gapPp >= 2 ? 'HIGH' : 'MEDIUM',
      evidence: {
        paper: `label smoothing = ${paperSmooth}`,
        code: `label smoothing = ${codeSmooth}`,
      },
      chain: [
        { id: 'c1', label: 'PAPER §3 LABEL SMOOTHING' },
        { id: 'c2', label: 'CODE train.py line 89' },
        { id: 'c3', label: 'PARAMETER MISMATCH' },
        { id: 'c4', label: 'ROOT CAUSE LOCKED' },
      ],
    }
  }

  if (experiment.id === 'E4' || experiment.id === 'E6' || experiment.id === 'E1') {
    const paperKey = Object.keys(experiment.paperConfig || {})[0] || 'config'
    const codeKey = Object.keys(experiment.codeConfig || {})[0] || 'config'
    const paperVal = experiment.paperConfig?.[paperKey]
    const codeVal = experiment.codeConfig?.[codeKey]
    const matches =
      paperVal != null && codeVal != null && String(paperVal) === String(codeVal)
    return {
      title: matches ? 'Configuration matches — gap within noise' : 'Minor residual gap',
      finding: experiment.summary || 'Paper and code configuration are largely aligned.',
      impact: matches
        ? 'Remaining gap is within sandbox evaluation noise for this prototype. The experiment is reproducible within a narrow tolerance band.'
        : 'Small divergences remain; the experiment is otherwise reproducible for demo purposes.',
      paperValue: Number(experiment.paperMetric?.toFixed?.(1) ?? experiment.paperMetric),
      codeValue: Number(experiment.reproduced?.toFixed?.(1) ?? experiment.reproduced),
      confidence: gapPp <= 1.7 ? 'MEDIUM' : 'LOW',
      evidence: {
        paper: `${paperKey} = ${paperVal}`,
        code: `${codeKey} = ${codeVal}`,
      },
      chain: [
        { id: 'c1', label: 'PAPER §3 HYPERPARAMETERS' },
        { id: 'c2', label: 'CODE config.yaml' },
        { id: 'c3', label: matches ? 'PARAMETER MATCH' : 'PARAMETER DRIFT' },
        { id: 'c4', label: 'ROOT CAUSE REVIEWED' },
      ],
    }
  }

  return {
    title: base.title,
    finding: experiment.summary || base.finding,
    impact: base.impact,
    paperValue: experiment.paperMetric ?? base.paperValue,
    codeValue: experiment.reproduced ?? base.codeValue,
    confidence: gapPp >= 2 ? 'HIGH' : 'MEDIUM',
    evidence: base.evidence,
    chain: base.chain,
  }
}

export function getRootCause(experimentId) {
  const experiment = getExperiment(experimentId || getSelectedExperimentId())
  return computeRootCause(experiment)
}

function computeRuns(experiment) {
  const runs = mockRuns
  const seed = mockExperiments.indexOf(experiment) || 0
  const hasReproduced = typeof experiment.reproduced === 'number' && Number.isFinite(experiment.reproduced)
  if (!hasReproduced) {
    return {
      experimentId: experiment.id,
      paperResult: Number(experiment.paperMetric),
      runCount: 0,
      mean: 'N/A',
      std: 'N/A',
      gap: 'N/A',
      items: [],
      logLines: [
        `$ docker run replicai/${experiment.id.toLowerCase()}`,
        'repository configuration incomplete.',
        `missing: ${Object.entries(experiment.parameters || {})
          .filter(([, value]) => value === null || value === undefined)
          .map(([key]) => key)
          .join(', ') || 'required parameter switch'}`,
        'cannot start sandbox run.',
      ],
      comparison: [
        { name: 'Paper', value: Number(experiment.paperMetric), fill: 'var(--paper)' },
      ],
    }
  }

  const target = Number(experiment.reproduced)
  const jitter = (n) => {
    const raw = target + ((((seed + 1) * (n + 1) * 37) % 11) - 5) / 10
    return Number(clamp(raw, target - 0.5, target + 0.5).toFixed(1))
  }
  const a = jitter(0)
  const b = jitter(1)
  const c = jitter(2)
  const mean = Number(((a + b + c) / 3).toFixed(2))
  const variance = ((a - mean) ** 2 + (b - mean) ** 2 + (c - mean) ** 2) / 3
  const std = Number(Math.sqrt(variance).toFixed(2))

  return {
    experimentId: experiment.id,
    paperResult: Number(experiment.paperMetric),
    runCount: runs.runCount,
    mean,
    std,
    gap: experiment.gap ?? Number((Number(experiment.paperMetric) - mean).toFixed(2)),
    items: [
      { id: `${experiment.id}-RUN-001`, status: 'COMPLETE', accuracy: `${a}%`, time: '00:42:05' },
      { id: `${experiment.id}-RUN-002`, status: 'COMPLETE', accuracy: `${b}%`, time: '00:42:11' },
      { id: `${experiment.id}-RUN-003`, status: 'COMPLETE', accuracy: `${c}%`, time: '00:42:08' },
    ],
    logLines: [
      `$ docker run replicai/${experiment.id.toLowerCase()}`,
      'booting python sandbox...',
      `loading model ${experiment.parameters?.model || 'Transformer-Base'}`,
      `seed ${experiment.parameters?.seed ?? 42} · ${experiment.parameters?.dataset || 'dataset'}`,
      `accuracy: ${mean}%`,
      'completed.',
    ],
    comparison: [
      { name: 'Paper', value: Number(experiment.paperMetric), fill: 'var(--paper)' },
      { name: 'Run 1', value: a, fill: 'var(--run)' },
      { name: 'Run 2', value: b, fill: 'var(--run)' },
      { name: 'Run 3', value: c, fill: 'var(--run)' },
      { name: 'Mean', value: mean, fill: 'var(--mean)' },
    ],
  }
}

export function getRuns(experimentId) {
  const experiment = getExperiment(experimentId || getSelectedExperimentId())
  if (experiment.id === 'E2') return mockRuns
  return computeRuns(experiment)
}

function remapEvidenceState(value) {
  if (value >= 90) return 'verified'
  if (value >= 60) return 'partial'
  return 'mismatch'
}

function computeEvidence(experiment) {
  const base = mockEvidence
  if (experiment.id === 'E2') return base
  const breakdown = experiment.readinessBreakdown || {}
  const paperState = remapEvidenceState(breakdown.paperEvidence ?? experiment.readiness)
  const codeState = remapEvidenceState(breakdown.codeEvidence ?? experiment.codeMatch)
  const paramState = remapEvidenceState(breakdown.parameterMatch ?? experiment.codeMatch)
  const datasetState = remapEvidenceState(breakdown.datasetMatch ?? experiment.readiness)
  const evalState = remapEvidenceState(breakdown.evaluationMatch ?? experiment.readiness)
  const runState =
    typeof experiment.reproduced === 'number' && experiment.gap !== null
      ? Math.abs(Number(experiment.gap)) <= 2
        ? 'verified'
        : 'partial'
      : 'mismatch'
  const claimState =
    Number(experiment.paperMetric) >= 87 ? 'verified' : Number(experiment.paperMetric) >= 85 ? 'partial' : 'mismatch'

  const stateFor = {
    'PAPER CLAIM': claimState,
    'PAPER §3.1': paperState,
    'REPO MAIN': codeState,
    'CONFIG VALUES': paramState,
    'DATASET SPLIT': datasetState,
    'EVAL SCRIPT': evalState,
    'SANDBOX RUN': runState,
    'FINAL METRIC': runState,
  }

  const metaFor = {
    'PAPER CLAIM': `${experiment.paperMetric.toFixed?.(1) ?? experiment.paperMetric}% BLEU`,
    'PAPER §3.1': `${breakdown.paperEvidence ?? experiment.readiness}% match`,
    'REPO MAIN': `${breakdown.codeEvidence ?? experiment.codeMatch}% match`,
    'CONFIG VALUES': `${breakdown.parameterMatch ?? experiment.codeMatch}% match`,
    'DATASET SPLIT': `${breakdown.datasetMatch ?? experiment.readiness}% match`,
    'EVAL SCRIPT': `${breakdown.evaluationMatch ?? experiment.readiness}% match`,
    'SANDBOX RUN':
      typeof experiment.reproduced === 'number'
        ? `${experiment.reproduced}% reproducible`
        : 'runs unavailable',
    'FINAL METRIC':
      typeof experiment.gap === 'number'
        ? `gap ${experiment.gap} pp`
        : 'gap unavailable',
  }

  const nodes = base.nodes.map((node) => ({
    ...node,
    data: {
      ...node.data,
      state: stateFor[node.data.title] || node.data.state,
      meta: metaFor[node.data.title] || node.data.meta,
    },
  }))

  return {
    legend: base.legend,
    nodes,
    edges: base.edges,
  }
}

export function getEvidence(experimentId) {
  const experiment = getExperiment(experimentId || getSelectedExperimentId())
  return computeEvidence(experiment)
}

export function getReport(experimentId) {
  const experiment = getExperiment(experimentId || getSelectedExperimentId())
  const runs = getRuns(experiment.id)
  const rootCause = getRootCause(experiment.id)
  const project = getProject()
  const hasGap = typeof experiment.gap === 'number' && Number.isFinite(experiment.gap)
  const finalStatus =
    experiment.status === 'FAILED'
      ? 'FAILED — REPRODUCTION BLOCKED'
      : hasGap && Math.abs(experiment.gap) > 2
        ? 'PARTIAL — UNDER REVIEW'
        : hasGap
          ? 'REPRODUCIBLE WITHIN TOLERANCE'
          : 'PENDING EXECUTION'

  return {
    projectSummary: `${project.papers} paper · ${project.experimentCount} experiments · selected ${experiment.id}`,
    paper: project.paperName,
    paperFile: project.paperFile,
    repository: project.repository.url,
    experiment,
    readiness: experiment.readiness,
    executionSummary:
      runs.runCount > 0 ? `${runs.runCount} completed sandbox runs` : 'No sandbox runs available',
    paperResult: Number(experiment.paperMetric),
    reproduced: runs.runCount > 0 ? runs.mean : 'N/A',
    gap: runs.runCount > 0 && hasGap ? experiment.gap : 'N/A',
    rootCause,
    evidence: [
      `Paper: ${rootCause.evidence.paper}`,
      `Code: ${rootCause.evidence.code}`,
    ],
    finalStatus,
  }
}
