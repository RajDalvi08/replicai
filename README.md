# ReplicAI — Paper Intelligence + Code Intelligence

This project implements the shortlist-focused reproducibility workflow:
**Paper → Experiment → Execute → Compare → Explain → Prove**

## Part 1 — Paper Intelligence
Accepts a PDF upload, extracts page-aware text, identifies experiment sections, extracts structured parameters, preserves evidence provenance, and exposes a FastAPI API.

### Features
- PDF upload validation and safety checks
- Page-aware text extraction with warnings for empty/image-only pages
- Deterministic experiment detection with LLM-friendly structured prompt
- Pydantic validation and evidence verification
- Database persistence with SQLAlchemy and Alembic
- JSON API for analysis and retrieval

## Part 2 — Code Intelligence
Statically analyzes a GitHub repository, maps paper parameters to code values, reconstructs the training pipeline, and computes a deterministic readiness score.

### Features
- Safe, shallow GitHub HTTPS repository cloning (no code execution)
- Repository structure analysis with file role detection
- Python AST static analysis (imports, functions, classes, CLI args, config, optimizer/scheduler/loss/metric calls)
- Canonical parameter vocabulary with alias normalization (`lr`→`learning_rate`, `bs`→`batch_size`, etc.)
- Training pipeline stage detection (dataset, model, optimizer, training loop, evaluation, metrics, checkpoints)
- Paper↔Code parameter mapping with verifiable evidence (`matched`/`mismatched`/`missing_in_code`/`missing_in_paper`/`uncertain`)
- Deterministic readiness scoring (10 categories, weighted sum = 100, thresholds: 90/75/50/0)
- Evidence verification against actual source files
- Full FastAPI integration with Part 1 experiments

### Security Model
Repository code is **statically analyzed and never executed**. No imports, no dependency installation, no shell commands, no notebooks, no Dockerfiles.

## Environment
Copy `.env.example` to `.env` and adjust values.

Required:
- `DATABASE_URL` — PostgreSQL or SQLite (default: `sqlite:///./replicai.db`)
- `MAX_UPLOAD_BYTES` — max PDF size in bytes
- `LLM_API_KEY` — optional provider key for external model calls
- `LLM_MODEL` — model name when real LLM configured
- `LLM_BASE_URL` — optional provider base URL
- `APP_NAME` — app name for logs

Code Intelligence specific (optional):
- `CODE_ALLOWED_HOSTS` — allowed git hosts (default: `github.com`)
- `CODE_MAX_REPO_BYTES` — max repository size (default: 64MB)
- `CODE_MAX_FILE_COUNT` — max files to analyze (default: 2000)
- `CODE_MAX_FILE_BYTES` — max individual file size (default: 1MB)
- `CODE_MAX_DEPTH` — max directory depth (default: 12)
- `CODE_CLONE_TIMEOUT_SECONDS` — git clone timeout (default: 60s)
- `CODE_MAX_ANALYSIS_SECONDS` — total analysis budget (default: 60s)
- `CODE_LLM_ENABLED` — enable optional LLM assist (default: `true`)

## Setup

Windows:
```
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Linux/macOS:
```
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the API
```
uvicorn backend.main:app --reload
```
Open:
- http://localhost:8000/health
- http://localhost:8000/docs

## Part 1 API Endpoints
- `POST /api/v1/paper/analyze` — upload PDF, get structured analysis
- `GET /api/v1/paper/{paper_id}` — fetch paper metadata
- `GET /api/v1/paper/{paper_id}/experiments` — list experiments
- `GET /api/v1/experiment/{experiment_id}` — fetch experiment + evidence

## Part 2 API Endpoints
- `POST /api/v1/code/analyze` — analyze GitHub repo against Part 1 experiment
  ```json
  { "repository_url": "https://github.com/owner/repo", "experiment_id": "1", "paper_id": "1", "branch": "main" }
  ```
- `GET /api/v1/repository/{repository_id}` — repository summary + entry points
- `GET /api/v1/repository/{repository_id}/files` — all detected files with roles
- `GET /api/v1/repository/{repository_id}/mappings` — paper↔code parameter mappings
- `GET /api/v1/repository/{repository_id}/readiness` — deterministic readiness report
- `GET /api/v1/experiment/{experiment_id}/code-analysis` — combined Part 1 + Part 2 view

Example:
```
curl -X POST "http://localhost:8000/api/v1/code/analyze" \
  -H "Content-Type: application/json" \
  -d '{"repository_url": "https://github.com/owner/repo", "experiment_id": "1"}'
```

## Testing
```
pytest -q
ruff check .
ruff format --check .
mypy backend
```

## Notes
- LLM is optional (Part 1 extraction, Part 2 file role hints) — deterministic fallback always works.
- Evidence values are verified against source (paper pages / code files); nothing is invented.
- Default SQLite for development; PostgreSQL via `DATABASE_URL` for production.
- Readiness score is deterministic, transparent, and explained with blockers/warnings — not a guarantee of reproducibility.

## Architecture
```
Paper Intelligence (Part 1)          Code Intelligence (Part 2)
┌─────────────────────────┐          ┌─────────────────────────┐
│ PDF → Text → LLM/Regex  │          │ GitHub URL → Shallow    │
│ → Experiment + Evidence │          │   Clone → AST Analysis  │
└───────────┬─────────────┘          └───────────┬─────────────┘
            │                                     │
            ▼                                     ▼
    ┌─────────────────────┐              ┌─────────────────────┐
    │   SQLite/PostgreSQL │◄─────────────►│   SQLite/PostgreSQL │
    │  papers, experiments│   mappings   │ repositories,       │
    │  parameters, evidence│              │ readiness, mappings │
    └─────────────────────┘              └─────────────────────┘
```

## Definition of Done (Part 2)
1. ✅ GitHub HTTPS URL submitted
2. ✅ Repository safely cloned (shallow, no exec)
3. ✅ Structure analyzed, roles detected
4. ✅ Python AST analysis (imports, functions, classes, CLI, config, optimizer, scheduler, loss, metrics)
5. ✅ Parameters extracted with canonical vocabulary
6. ✅ Pipeline stages detected
7. ✅ Part 1 experiment loaded
8. ✅ Paper params mapped to code with evidence
9. ✅ Matched/mismatched/missing distinguished
10. ✅ Deterministic readiness score + blockers/warnings
11. ✅ Results persisted to PostgreSQL/SQLite
12. ✅ Alembic migration works
13. ✅ API endpoints functional
14. ✅ All 88 tests pass (15 Part 1 + 73 Part 2)
15. ✅ Ruff check / format / mypy pass