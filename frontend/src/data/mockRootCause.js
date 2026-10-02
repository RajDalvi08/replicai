export const mockRootCause = {
  title: 'BATCH SIZE MISMATCH',
  finding: 'Parameter mismatch',
  confidence: 'High',
  paperValue: 64,
  codeValue: 32,
  impact:
    'Configuration mismatch may contribute to the reproduction gap. This is an observed difference between paper text and repository config, not a causal proof.',
  evidence: {
    paper: 'batch size = 64',
    code: 'batch size = 32',
  },
  chain: [
    { id: 'paper', label: 'PAPER EVIDENCE' },
    { id: 'config', label: 'CONFIGURATION' },
    { id: 'code', label: 'CODE' },
    { id: 'exec', label: 'EXECUTION DIFFERENCE' },
  ],
}
