import { jsPDF } from 'jspdf'

const PAGE_MARGIN = 16
const PAGE_BOTTOM = 279
const PURPLE = [109, 40, 217]
const INK = [22, 22, 22]
const MUTED = [90, 90, 90]
const RULE = [218, 213, 228]

function cleanText(value) {
  return String(value)
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'")
    .replace(/[–—]/g, '-')
    .replace(/[→↔]/g, '->')
    .replace(/[·•]/g, ' | ')
    .replace(/[^\x20-\x7E]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function formatValue(value, depth = 0) {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'string') return cleanText(value)
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : ''
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? '' : value.toLocaleString()
  if (depth > 3) return ''
  if (Array.isArray(value)) {
    return value.map((item) => formatValue(item, depth + 1)).filter(Boolean).join('\n')
  }
  if (typeof value === 'object') {
    return Object.entries(value)
      .map(([key, item]) => {
        const formatted = formatValue(item, depth + 1)
        return formatted ? `${cleanText(key)}: ${formatted}` : ''
      })
      .filter(Boolean)
      .join('\n')
  }
  return ''
}

function valueOrUnavailable(value) {
  return formatValue(value) || 'Not available'
}

function entriesFromObject(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return []
  return Object.entries(value)
    .map(([key, item]) => [cleanText(key.replaceAll('_', ' ')), formatValue(item)])
    .filter(([, item]) => item)
}

function experimentParameters(experiment) {
  const params = experiment?.parameters
  if (Array.isArray(params)) {
    return params
      .filter((item) => item && typeof item === 'object')
      .map((item) => [
        cleanText(item.field_name || item.name || 'Parameter'),
        formatValue(item.value),
      ])
      .filter(([, value]) => value)
  }

  return [
    ...entriesFromObject(params),
    ...entriesFromObject(experiment?.paperConfig).map(([key, value]) => [`Paper ${key}`, value]),
    ...entriesFromObject(experiment?.codeConfig).map(([key, value]) => [`Code ${key}`, value]),
  ]
}

function evidenceRows(experiment, codeAnalysis, results) {
  const rows = []
  const paperEvidence = Array.isArray(experiment?.evidence) ? experiment.evidence : []
  for (const [index, item] of paperEvidence.entries()) {
    rows.push([
      `Paper evidence ${index + 1}`,
      [
        item.field ? `Field: ${item.field}` : '',
        item.page !== undefined && item.page !== null ? `Page: ${item.page}` : '',
        item.confidence !== undefined && item.confidence !== null
          ? `Confidence: ${Math.round(Number(item.confidence) * 100)}%`
          : '',
        item.quote || item.value,
      ].map(formatValue).filter(Boolean).join(' | '),
    ])
  }

  const mappings = Array.isArray(codeAnalysis?.mappings) ? codeAnalysis.mappings : []
  for (const [index, mapping] of mappings.entries()) {
    const evidence = mapping.evidence
    rows.push([
      `Code mapping ${index + 1}: ${mapping.paper_field || 'Mapping'}`,
      [
        mapping.status ? `Status: ${mapping.status}` : '',
        mapping.paper_value !== undefined ? `Paper: ${formatValue(mapping.paper_value)}` : '',
        mapping.code_value !== undefined ? `Code: ${formatValue(mapping.code_value)}` : '',
        mapping.confidence !== undefined && mapping.confidence !== null
          ? `Confidence: ${Math.round(Number(mapping.confidence) * 100)}%`
          : '',
        mapping.reason,
        evidence?.file ? `File: ${evidence.file}${evidence.line_start ? `:${evidence.line_start}` : ''}` : '',
        evidence?.quote,
      ].map(formatValue).filter(Boolean).join(' | '),
    ])
  }

  if (results?.paper?.metric_evidence) {
    rows.push(['Reported metric evidence', formatValue(results.paper.metric_evidence)])
  }

  return rows.filter(([, value]) => value)
}

function recommendationRows(codeAnalysis, results) {
  const candidates = [
    results?.recommendations,
    results?.actions,
    results?.next_steps,
    results?.explanation?.recommendations,
    codeAnalysis?.recommendations,
    codeAnalysis?.actions,
    codeAnalysis?.readiness?.recommendations,
  ]
  const recommendations = candidates.flatMap((candidate) => {
    if (Array.isArray(candidate)) return candidate
    return candidate ? [candidate] : []
  })

  return recommendations
    .map((item, index) => [
      `Recommendation ${index + 1}`,
      typeof item === 'object' ? formatValue(item) : formatValue(item),
    ])
    .filter(([, value]) => value)
}

function getReportSections({
  experiment,
  experimentId,
  paperAnalysis,
  codeAnalysis,
  run,
  validation,
  results,
}) {
  const title = experiment?.title || experiment?.name || 'Selected experiment'
  const status = experiment?.status || ''
  const parameters = experimentParameters(experiment)
  const resultRows = []
  const paper = results?.paper
  const reproduction = results?.reproduction
  const comparison = results?.comparison
  const reportedResults = experiment?.reported_results
  if (reportedResults && typeof reportedResults === 'object') {
    for (const [metric, reported] of Object.entries(reportedResults)) {
      resultRows.push([
        `Paper-reported ${metric}`,
        formatValue(reported?.value ?? reported),
      ])
    }
  }

  if (paper) resultRows.push(['Paper metric', `${valueOrUnavailable(paper.metric)}: ${valueOrUnavailable(paper.reported_value)}`])
  if (reproduction) {
    resultRows.push(['Reproduction metric', valueOrUnavailable(reproduction.metric)])
    resultRows.push(['Runs', valueOrUnavailable(reproduction.runs)])
    resultRows.push(['Mean', valueOrUnavailable(reproduction.mean)])
    resultRows.push(['Standard deviation', valueOrUnavailable(reproduction.std)])
    resultRows.push(...entriesFromObject(reproduction.metrics).map(([key, value]) => [`Metric: ${key}`, value]))
  }
  if (comparison) resultRows.push(...entriesFromObject(comparison))
  if (run) {
    resultRows.push(['Execution status', valueOrUnavailable(run.status)])
    if (run.exit_code !== undefined) resultRows.push(['Exit code', valueOrUnavailable(run.exit_code)])
    if (run.execution_time_seconds !== undefined) {
      resultRows.push(['Execution time (seconds)', valueOrUnavailable(run.execution_time_seconds)])
    }
    if (run.metrics) resultRows.push(...entriesFromObject(run.metrics).map(([key, value]) => [`Run metric: ${key}`, value]))
    if (run.error) resultRows.push(['Execution detail', formatValue(run.error)])
  }
  if (validation) {
    resultRows.push(['Validation status', valueOrUnavailable(validation.status)])
    if (Array.isArray(validation.runs)) {
      validation.runs.forEach((item, index) => {
        resultRows.push([`Validation run ${item.run || index + 1}`, formatValue(item)])
      })
    }
  }

  const explanations = Array.isArray(results?.explanation) ? results.explanation : []
  const mappings = Array.isArray(codeAnalysis?.mappings) ? codeAnalysis.mappings : []
  const findings = explanations.length ? explanations : mappings
  const firstFinding = findings[0]
  const rootCauseRows = firstFinding
    ? [
        ['Finding', firstFinding.parameter || firstFinding.category || firstFinding.paper_field || 'Analysis finding'],
        ['Status', formatValue(firstFinding.status)],
        ['Confidence', firstFinding.confidence === undefined ? '' : `${Math.round(Number(firstFinding.confidence) * 100)}%`],
        ['Explanation', firstFinding.reason || firstFinding.message],
        ['Affected item', firstFinding.evidence?.file || firstFinding.paper_field || ''],
        ...findings.slice(1).map((finding, index) => [
          `Additional finding ${index + 1}`,
          [
            finding.parameter || finding.category || finding.paper_field,
            finding.status,
            finding.reason || finding.message,
          ].map(formatValue).filter(Boolean).join(' | '),
        ]),
      ].filter(([, value]) => formatValue(value))
    : []

  const finalSummary = [
    `${title} (${experimentId || experiment?.experiment_id || experiment?.id || 'ID unavailable'})`,
    status ? `Experiment status: ${formatValue(status)}.` : '',
    run?.status ? `Execution status: ${formatValue(run.status)}.` : '',
    validation?.status ? `Validation status: ${formatValue(validation.status)}.` : '',
    comparison
      ? `Comparison: ${valueOrUnavailable(comparison.paper_value)} paper vs ${valueOrUnavailable(comparison.reproduced_value)} reproduced; ${valueOrUnavailable(comparison.status)}.`
      : '',
    firstFinding
      ? `Primary finding: ${formatValue(firstFinding.reason || firstFinding.message || firstFinding.parameter || firstFinding.paper_field)}`
      : '',
  ].filter(Boolean).join(' ')

  return {
    title,
    status,
    generatedAt: new Date(),
    sections: [
      {
        title: 'Experiment Summary',
        rows: [
          ['Experiment', title],
          ['Experiment ID', experimentId || experiment?.experiment_id || experiment?.id],
          ['Description', experiment?.description || experiment?.summary],
          ['Status', status],
          ['Dataset', experiment?.dataset || experiment?.parameters?.dataset],
          ['Model', experiment?.model || experiment?.parameters?.model],
          ['Paper', paperAnalysis?.filename],
          ['Repository', codeAnalysis?.repository?.url || codeAnalysis?.repository_url],
          ['Readiness', codeAnalysis?.readiness
            ? `${valueOrUnavailable(codeAnalysis.readiness.overall_score)}% | ${valueOrUnavailable(codeAnalysis.readiness.status)}`
            : ''],
          ...parameters,
        ].filter(([, value]) => formatValue(value)),
      },
      { title: 'Results', rows: resultRows },
      { title: 'Evidence', rows: evidenceRows(experiment, codeAnalysis, results) },
      { title: 'Root Cause Analysis', rows: rootCauseRows },
      { title: 'Recommendations', rows: recommendationRows(codeAnalysis, results) },
      { title: 'Final Summary', rows: [['Summary', finalSummary]] },
    ],
  }
}

function addPageFooter(doc) {
  const totalPages = doc.getNumberOfPages()
  for (let page = 1; page <= totalPages; page += 1) {
    doc.setPage(page)
    doc.setDrawColor(...RULE)
    doc.line(PAGE_MARGIN, 284, 194, 284)
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.setTextColor(...MUTED)
    doc.text('ReplicAI | Reproducibility Report', PAGE_MARGIN, 289)
    doc.text(`Page ${page} of ${totalPages}`, 194, 289, { align: 'right' })
  }
}

function drawReport(doc, report) {
  let y = PAGE_MARGIN
  const pageWidth = doc.internal.pageSize.getWidth()
  const usableWidth = pageWidth - PAGE_MARGIN * 2
  const labelWidth = 43
  const valueX = PAGE_MARGIN + labelWidth + 4
  const valueWidth = usableWidth - labelWidth - 4

  const addPage = () => {
    doc.addPage()
    y = PAGE_MARGIN
    doc.setFont('helvetica', 'normal')
    doc.setFontSize(8)
    doc.setTextColor(...MUTED)
    doc.text('REPLICAI | REPRODUCIBILITY REPORT', PAGE_MARGIN, y)
    y += 10
  }

  const ensureSpace = (height) => {
    if (y + height > PAGE_BOTTOM) addPage()
  }

  doc.setFillColor(...PURPLE)
  doc.rect(PAGE_MARGIN, y, usableWidth, 2, 'F')
  y += 11
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(11)
  doc.setTextColor(...PURPLE)
  doc.text('REPLICAI', PAGE_MARGIN, y)
  doc.setFontSize(21)
  doc.setTextColor(...INK)
  doc.text('Reproducibility Report', PAGE_MARGIN, y + 11)
  y += 19
  doc.setFont('helvetica', 'bold')
  doc.setFontSize(13)
  doc.setTextColor(...INK)
  const titleLines = doc.splitTextToSize(cleanText(report.title), usableWidth)
  doc.text(titleLines, PAGE_MARGIN, y)
  y += titleLines.length * 6 + 2
  doc.setFont('helvetica', 'normal')
  doc.setFontSize(9)
  doc.setTextColor(...MUTED)
  doc.text(`Experiment: ${cleanText(report.experimentId || report.title)}`, PAGE_MARGIN, y)
  y += 5
  doc.text(`Generated: ${report.generatedAt.toLocaleString()}`, PAGE_MARGIN, y)
  y += 7
  doc.setDrawColor(...RULE)
  doc.line(PAGE_MARGIN, y, pageWidth - PAGE_MARGIN, y)
  y += 7

  for (const section of report.sections) {
    ensureSpace(15)
    doc.setFillColor(244, 240, 252)
    doc.roundedRect(PAGE_MARGIN, y, usableWidth, 8, 1, 1, 'F')
    doc.setFont('helvetica', 'bold')
    doc.setFontSize(10)
    doc.setTextColor(...PURPLE)
    doc.text(cleanText(section.title).toUpperCase(), PAGE_MARGIN + 3, y + 5.5)
    y += 12

    if (!section.rows.length) {
      const emptyText = section.title === 'Evidence'
        ? 'No additional evidence available.'
        : section.title === 'Recommendations'
          ? 'No recommendations are available in the current analysis.'
          : 'No additional information available.'
      ensureSpace(8)
      doc.setFont('helvetica', 'italic')
      doc.setFontSize(9)
      doc.setTextColor(...MUTED)
      doc.text(emptyText, PAGE_MARGIN + 2, y)
      y += 7
      continue
    }

    for (const [label, rawValue] of section.rows) {
      const cleanLabel = cleanText(label || 'Detail')
      const cleanValue = formatValue(rawValue)
      if (!cleanValue) continue
      const valueLines = cleanValue
        .split('\n')
        .flatMap((line) => doc.splitTextToSize(line, valueWidth))
      let lineIndex = 0
      let firstChunk = true

      while (lineIndex < valueLines.length) {
        if (y + 4.5 > PAGE_BOTTOM) addPage()
        const lineCount = Math.max(1, Math.floor((PAGE_BOTTOM - y - 4) / 4.5))
        const chunk = valueLines.slice(lineIndex, lineIndex + lineCount)
        const rowHeight = Math.max(6, chunk.length * 4.5 + 2)
        ensureSpace(rowHeight)

        doc.setFont('helvetica', firstChunk ? 'bold' : 'normal')
        doc.setFontSize(8.5)
        doc.setTextColor(...(firstChunk ? INK : MUTED))
        if (firstChunk) {
          const labelLines = doc.splitTextToSize(cleanLabel, labelWidth - 2)
          doc.text(labelLines, PAGE_MARGIN + 2, y + 3)
        }
        doc.setFont('helvetica', 'normal')
        doc.setFontSize(9)
        doc.setTextColor(...INK)
        doc.text(chunk, valueX, y + 3)
        y += rowHeight
        lineIndex += chunk.length
        firstChunk = false

        if (lineIndex < valueLines.length) addPage()
      }

      doc.setDrawColor(...RULE)
      doc.line(PAGE_MARGIN, y, pageWidth - PAGE_MARGIN, y)
      y += 2
    }

    y += 3
  }
}

function makeFilename(title) {
  const safeName = cleanText(title)
    .replace(/[<>:"/\\|?*]/g, '')
    .replace(/[^A-Za-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 80)
  return `ReplicAI_${safeName || 'Experiment'}_Report.pdf`
}

export function createExperimentReport(data) {
  const report = getReportSections(data)
  const doc = new jsPDF({ format: 'a4', unit: 'mm', compress: false })
  const experimentId = data.experimentId || data.experiment?.experiment_id || data.experiment?.id || ''
  report.experimentId = experimentId
  doc.setProperties({
    title: `ReplicAI Report - ${report.title}`,
    subject: `Reproducibility report for ${report.title}`,
    author: 'ReplicAI',
    creator: 'ReplicAI',
  })
  drawReport(doc, report)
  addPageFooter(doc)
  return {
    blob: doc.output('blob'),
    filename: makeFilename(report.title),
  }
}

export function downloadExperimentReport(data) {
  const { blob, filename } = createExperimentReport(data)
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.style.display = 'none'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
