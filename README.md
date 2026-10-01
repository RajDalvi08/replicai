# ReplicAI Paper Intelligence

This project contains the paper-analysis prototype for the shortlist-focused reproducibility workflow. It accepts a PDF upload, extracts page-aware text, identifies likely experiment sections, validates structured experiment fields, preserves evidence provenance, stores the result in SQLAlchemy-backed persistence, and exposes a small FastAPI API.

## Features
- PDF upload validation and safety checks
- Page-aware text extraction with warnings for empty or image-only pages
- Deterministic experiment detection with an LLM-friendly structured prompt
- Pydantic validation and evidence verification
- Database persistence with SQLAlchemy and Alembic support
- JSON API for analysis and retrieval

## Environment
Copy `.env.example` to `.env` and adjust the values as needed.

Required environment variables:
- `DATABASE_URL` — PostgreSQL or SQLite connection string; defaults to `sqlite:///./replicai.db`
- `MAX_UPLOAD_BYTES` — maximum uploaded PDF size in bytes
- `LLM_API_KEY` — optional provider key for external model calls
- `LLM_MODEL` — model name to use when a real LLM is configured
- `LLM_BASE_URL` — optional provider base URL
- `APP_NAME` — app name for logs and startup metadata

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

Then open:
- http://localhost:8000/health
- http://localhost:8000/docs

## API endpoints
- `POST /api/v1/paper/analyze` — upload a PDF and receive a structured analysis result
- `GET /api/v1/paper/{paper_id}` — fetch the stored paper metadata
- `GET /api/v1/paper/{paper_id}/experiments` — list experiments for a paper
- `GET /api/v1/experiment/{experiment_id}` — fetch one experiment and its evidence
- `GET /health` — app health check

Example upload with curl:

```
curl -X POST "http://localhost:8000/api/v1/paper/analyze" \
  -F "file=@tests/fixtures/acceptance_paper.pdf"
```

## Testing

Run:

```
pytest -q
ruff check .
mypy backend/paper
```

Optional formatting check:

```
ruff format --check .
```

## Notes
- The module prefers a real LLM when `LLM_API_KEY` and a provider configuration are present, but it safely falls back to deterministic extraction when the environment is not configured.
- Evidence values are always verified against page text when possible, and values are never invented.
- For local development the default SQLite database is used; for production the `DATABASE_URL` can point to PostgreSQL.
