# ReplicAI frontend

The frontend uses the ReplicAI backend APIs. Configure the API base URL in
`.env` (copy `.env.example` to `.env` when setting up a new checkout):

```env
VITE_API_URL=http://localhost:8001
```

## Start the ReplicAI backend

In PowerShell:

```powershell
Set-Location "C:\Users\Raj\Downloads\replicai - prototype\replicai-ninad\01 - Paper Intelligence"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8001
```

Use port `8001`; port `8000` may belong to a separate service. Confirm the
backend is available at <http://localhost:8001/health> and inspect its API at
<http://localhost:8001/docs>.

## Start the frontend

In another PowerShell window:

```powershell
Set-Location "C:\Users\Raj\Downloads\replicai - prototype\replicai\frontend"
npm install
npm run dev
```

Vite reads `VITE_API_URL` at startup. Restart the dev server after changing
`.env`.

The UI's primary flow is paper upload and experiment extraction, repository
analysis, readiness and evidence review, execution and polling, three-run
validation, and final results from the ReplicAI backend.

The frontend automatically checks the backend health endpoint on startup and
falls back to the bundled mock dataset if the backend is offline or unreachable.
This keeps the prototype usable in public deployments before the backend is
available. For manual testing, set `VITE_FORCE_DEMO=true` to force mock data,
while the default `VITE_FORCE_DEMO=false` keeps the automatic detection flow.
