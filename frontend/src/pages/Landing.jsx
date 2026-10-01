import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getProject } from '../data'
import BrutalCard from '../components/ui/BrutalCard'
import Button from '../components/ui/Button'
import Input from '../components/ui/Input'

const GITHUB_PATTERN = /github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+/i

function validateGithub(url) {
  const value = url.trim()
  if (!value) return 'Repository URL is required.'
  if (!GITHUB_PATTERN.test(value)) return 'Enter a valid GitHub repository URL.'
  return ''
}

export default function Landing() {
  const project = getProject()
  const navigate = useNavigate()
  const [paperName, setPaperName] = useState('')
  const [repo, setRepo] = useState(project.repository.url)
  const [repoError, setRepoError] = useState('')
  const [analyze, setAnalyze] = useState('IDLE')
  const timerRef = useRef(0)

  useEffect(() => () => window.clearTimeout(timerRef.current), [])

  const startAnalyze = () => {
    const error = validateGithub(repo)
    setRepoError(error)
    if (error || analyze === 'ANALYZING') return
    setAnalyze('ANALYZING')
    timerRef.current = window.setTimeout(() => {
      setAnalyze('COMPLETE')
      navigate('/dashboard')
    }, 1200)
  }

  return (
    <section className="page">
      <div className="hero">
        <div>
          <div className="page-kicker">01 / START PROJECT</div>
          <h1>REPRODUCE THE PAPER.</h1>
          <p className="page-copy">
            ReplicAI connects research papers, GitHub repositories, experiment configs, and execution
            evidence into a single reproducibility console. Start with a PDF and a repo. Trace the gap.
          </p>
          <div className="workflow">
            {project.workflow.map((step, index) => (
              <span key={step} style={{ display: 'contents' }}>
                <span className="workflow-node">{step}</span>
                {index < project.workflow.length - 1 ? <span className="workflow-arrow">→</span> : null}
              </span>
            ))}
          </div>
        </div>
        <BrutalCard>
          <SectionBlock title="RESEARCH PAPER" meta="PDF">
            <label className={`dropzone ${paperName ? 'active' : ''}`}>
              <input
                type="file"
                accept="application/pdf"
                hidden
                onChange={(event) => setPaperName(event.target.files?.[0]?.name || '')}
              />
              <div>
                <strong>{paperName || 'DRAG & DROP PDF'}</strong>
                <div>or click to select a research paper</div>
              </div>
            </label>
            {paperName ? <div className="field-hint ok">Selected · {paperName}</div> : null}
          </SectionBlock>
          <div style={{ height: 12 }} />
          <Input
            label="GITHUB REPOSITORY"
            value={repo}
            onChange={(event) => {
              const next = event.target.value
              setRepo(next)
              setRepoError(next.trim() ? validateGithub(next) : '')
            }}
            placeholder="https://github.com/org/repo"
          />
          {repoError ? (
            <div className="field-hint error">{repoError}</div>
          ) : repo.trim() ? (
            <div className="field-hint ok">Repository stored · {repo}</div>
          ) : (
            <div className="field-hint">Enter a GitHub repository URL</div>
          )}
          <div style={{ height: 14 }} />
          <Button block onClick={startAnalyze} disabled={analyze === 'ANALYZING'}>
            {analyze === 'IDLE' && 'ANALYZE EXPERIMENT'}
            {analyze === 'ANALYZING' && 'ANALYZING…'}
            {analyze === 'COMPLETE' && 'COMPLETE'}
          </Button>
          <div className="feedback">
            {paperName ? `PAPER ${paperName}` : 'PAPER mock paper.pdf'} · {analyze}
          </div>
        </BrutalCard>
      </div>
    </section>
  )
}

function SectionBlock({ title, meta, children }) {
  return (
    <div>
      <div className="section-header" style={{ marginTop: 0 }}>
        <h2>{title}</h2>
        <span>{meta}</span>
      </div>
      {children}
    </div>
  )
}
