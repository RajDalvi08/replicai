export const mockEvidence = {
  legend: [
    { id: 'verified', label: 'VERIFIED', tone: 'success' },
    { id: 'partial', label: 'PARTIAL', tone: 'warning' },
    { id: 'mismatch', label: 'MISMATCH', tone: 'error' },
  ],
  nodes: [
    {
      id: 'paper',
      type: 'evidence',
      position: { x: 60, y: 20 },
      data: {
        kicker: 'RESEARCH PAPER',
        title: 'paper.pdf',
        meta: '12 pages · extracted',
        state: 'verified',
      },
    },
    {
      id: 'experiment',
      type: 'evidence',
      position: { x: 60, y: 200 },
      data: {
        kicker: 'EXPERIMENT',
        title: 'Experiment E2',
        meta: 'multi-head attention',
        state: 'partial',
      },
    },
    {
      id: 'paper-evidence',
      type: 'evidence',
      position: { x: 380, y: 200 },
      data: {
        kicker: 'PAPER EVIDENCE',
        title: 'batch_size = 64',
        meta: '§5.1 training details',
        state: 'verified',
      },
    },
    {
      id: 'code-file',
      type: 'evidence',
      position: { x: 60, y: 390 },
      data: {
        kicker: 'CODE FILE',
        title: 'train.py',
        meta: 'src/train.py:188',
        state: 'verified',
      },
    },
    {
      id: 'config',
      type: 'evidence',
      position: { x: 380, y: 390 },
      data: {
        kicker: 'CONFIGURATION',
        title: 'config.yaml',
        meta: 'batch_size=32',
        state: 'mismatch',
      },
    },
    {
      id: 'evaluate',
      type: 'evidence',
      position: { x: 700, y: 390 },
      data: {
        kicker: 'EVALUATION',
        title: 'evaluate.py',
        meta: 'held-out split',
        state: 'verified',
      },
    },
    {
      id: 'execution',
      type: 'evidence',
      position: { x: 380, y: 580 },
      data: {
        kicker: 'EXECUTION',
        title: 'run-001',
        meta: 'docker sandbox',
        state: 'verified',
      },
    },
    {
      id: 'metric',
      type: 'evidence',
      position: { x: 700, y: 580 },
      data: {
        kicker: 'METRIC',
        title: 'accuracy=84.1%',
        meta: 'vs paper 87.60%',
        state: 'partial',
      },
    },
  ],
  edges: [
    { id: 'e1', source: 'paper', target: 'experiment', type: 'smoothstep' },
    { id: 'e2', source: 'experiment', target: 'paper-evidence', type: 'smoothstep' },
    { id: 'e3', source: 'experiment', target: 'code-file', type: 'smoothstep' },
    { id: 'e4', source: 'code-file', target: 'config', type: 'smoothstep' },
    { id: 'e5', source: 'code-file', target: 'evaluate', type: 'smoothstep' },
    { id: 'e6', source: 'config', target: 'execution', type: 'smoothstep' },
    { id: 'e7', source: 'evaluate', target: 'metric', type: 'smoothstep' },
    { id: 'e8', source: 'execution', target: 'metric', type: 'smoothstep' },
  ],
}
