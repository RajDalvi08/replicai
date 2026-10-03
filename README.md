# 🧬 ReplicAI

### Paper Intelligence × Code Intelligence for ML Reproducibility

<p align="center">
  <strong>Paper → Experiment → Execute → Compare → Explain → Prove</strong>
</p>

<p align="center">
  <em>Turn an ML research paper and its implementation into a verifiable reproducibility report.</em>
</p>

---

## 🚀 What is ReplicAI?

**ReplicAI** is a reproducibility intelligence platform that connects what an ML paper **claims** with what its implementation **actually does**.

Instead of manually reading a paper, searching through a GitHub repository, finding training parameters, and comparing everything by hand, ReplicAI builds a structured connection between:

```text
Research Paper
      ↓
Experiment Reconstruction
      ↓
GitHub Repository
      ↓
Static Code Analysis
      ↓
Paper ↔ Code Mapping
      ↓
Readiness Analysis
      ↓
Evidence-backed Report
```

### The core idea

> **Don't just ask whether a paper is reproducible.
> Show the evidence behind the answer.**

---

# 🎯 The Problem

Reproducing an ML paper usually requires manually answering questions such as:

* What dataset was used?
* Which model architecture?
* What learning rate?
* What batch size?
* Which optimizer?
* Which scheduler?
* How many epochs?
* What loss function?
* Which evaluation metrics?
* Where is the training loop?
* Does the GitHub implementation actually contain these values?
* Which paper parameters are missing from the code?
* Which code parameters contradict the paper?

This information is often distributed across:

```text
📄 Research Paper
💻 GitHub Repository
⚙️ Configuration Files
🐍 Training Scripts
📊 Evaluation Code
📝 Documentation
```

ReplicAI connects these sources automatically.

---

# 🧠 Core Workflow

```text
              ┌──────────────────┐
              │   Research PDF   │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Paper Intelligence│
              │                  │
              │ • PDF extraction │
              │ • Experiments    │
              │ • Parameters     │
              │ • Evidence       │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Experiment Model │
              └────────┬─────────┘
                       │
                       │ Paper ↔ Code
                       │
                       ▼
              ┌──────────────────┐
              │ Code Intelligence│
              │                  │
              │ • GitHub clone   │
              │ • AST analysis   │
              │ • Parameters     │
              │ • Pipeline       │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Evidence Mapping │
              │                  │
              │ MATCHED          │
              │ MISMATCHED       │
              │ MISSING          │
              │ UNCERTAIN        │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Readiness Score  │
              │      /100        │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Explain + Prove  │
              │                  │
              │ Blockers         │
              │ Warnings         │
              │ Evidence         │
              └──────────────────┘
```

---

# ✨ Key Features

## 📄 1. Paper Intelligence

ReplicAI converts an ML research paper into a structured experiment representation.

### PDF Processing

* PDF upload validation
* File-size and safety checks
* Page-aware text extraction
* Empty/image-only page detection
* Experiment section identification
* Structured parameter extraction
* Evidence provenance preservation

### Structured Experiment

Parameters are converted into a canonical representation such as:

```json
{
  "learning_rate": 0.001,
  "batch_size": 32,
  "optimizer": "Adam",
  "epochs": 50,
  "loss_function": "CrossEntropyLoss",
  "metric": "accuracy"
}
```

Each extracted value retains its **source evidence**.

That means ReplicAI does not simply say:

> Learning rate = 0.001

It can also identify **where that value came from in the paper**.

---

# 💻 2. Code Intelligence

ReplicAI analyzes the implementation associated with the research paper.

The repository is:

```text
GitHub URL
    ↓
Safe HTTPS Clone
    ↓
Repository Structure Analysis
    ↓
Python AST Analysis
    ↓
Parameter Extraction
    ↓
Training Pipeline Detection
```

### Static Analysis

ReplicAI analyzes Python source code without executing it.

It detects:

* Imports
* Functions
* Classes
* CLI arguments
* Configuration values
* Dataset usage
* Model definitions
* Optimizers
* Learning-rate schedulers
* Loss functions
* Training loops
* Evaluation
* Metrics
* Checkpoints

---

# 🔗 3. Paper ↔ Code Intelligence

This is the core of ReplicAI.

The platform maps parameters extracted from the paper against parameters discovered in the implementation.

### Example

```text
                 PAPER                    CODE

Learning Rate    0.001  ───────────────►  0.001
Batch Size       32     ───────────────►  32
Optimizer        Adam   ───────────────►  Adam

Epochs           100    ───────────────►  50
                                      ↑
                                  MISMATCH

Scheduler        Cosine ───────────────► ❌ Missing
                                      ↑
                                  BLOCKER
```

Every mapping is classified as:

| Status                | Meaning                                                  |
| --------------------- | -------------------------------------------------------- |
| 🟢 `matched`          | Paper and code agree                                     |
| 🔴 `mismatched`       | Both exist but values differ                             |
| 🟠 `missing_in_code`  | Paper specifies it, code does not expose it              |
| 🔵 `missing_in_paper` | Code contains it, paper does not specify it              |
| 🟡 `uncertain`        | Evidence is insufficient to establish a reliable mapping |

---

# 🔍 4. Evidence-Backed Analysis

ReplicAI is designed around **verifiable evidence**.

### Paper evidence

```text
Paper
 └── Page 7
      └── Training Details
           └── Learning Rate = 0.001
```

### Code evidence

```text
train.py
 └── Line 42
      └── Adam(...)
           └── lr = 0.001
```

The system verifies extracted evidence against the actual source instead of blindly trusting generated output.

> **Evidence first. Conclusions second.**

---

# 🧩 5. Training Pipeline Reconstruction

ReplicAI detects the major stages of an ML training pipeline:

```text
Dataset
   ↓
Preprocessing
   ↓
Model
   ↓
Optimizer
   ↓
Training Loop
   ↓
Scheduler
   ↓
Evaluation
   ↓
Metrics
   ↓
Checkpoint
```

This provides a high-level understanding of how the implementation actually trains and evaluates the model.

---

# 📊 6. Deterministic Readiness Score

ReplicAI computes a transparent **reproducibility readiness score out of 100**.

```text
                    Readiness
                       /100
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   Parameters        Pipeline         Evidence
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
                  Final Readiness
```

The score is based on **10 analysis categories** with a deterministic weighted sum.

### Thresholds

|    Score | Interpretation    |
| -------: | ----------------- |
| `90–100` | High readiness    |
|  `75–89` | Good readiness    |
|  `50–74` | Partial readiness |
|    `<50` | Low readiness     |

The score is accompanied by:

```text
✓ Matched parameters
✗ Mismatched parameters
⚠ Missing information
⚠ Uncertain mappings
🚧 Reproducibility blockers
```

### Important

The readiness score is **not a guarantee that an experiment will reproduce successfully**.

It is a transparent measurement of how well the available paper and implementation information aligns.

---

# 🛡️ Security-First Code Analysis

ReplicAI deliberately **does not execute repository code**.

The analysis pipeline follows:

```text
GitHub
  │
  ▼
HTTPS Repository
  │
  ▼
Shallow Clone
  │
  ▼
Static Inspection
  │
  ├── File structure
  ├── Python AST
  ├── Parameters
  ├── Pipeline stages
  └── Evidence
```

### 🚫 Never executed

ReplicAI does **not**:

* Import repository code
* Install repository dependencies
* Execute Python files
* Execute notebooks
* Execute shell commands
* Execute Dockerfiles
* Run training jobs

This allows the platform to inspect unfamiliar repositories while maintaining a strong separation between **analysis** and **execution**.

---

# 🏗️ System Architecture

## High-Level Architecture

```text
                         ┌──────────────────────┐
                         │       USER           │
                         └──────────┬───────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
             ┌─────────────┐                 ┌─────────────┐
             │ Research PDF│                 │ GitHub Repo │
             └──────┬──────┘                 └──────┬──────┘
                    │                               │
                    ▼                               ▼
        ┌─────────────────────┐          ┌─────────────────────┐
        │ Paper Intelligence  │          │ Code Intelligence   │
        │                     │          │                     │
        │ PDF Extraction      │          │ Safe Clone          │
        │ Experiment Detect   │          │ File Analysis       │
        │ Parameter Extract   │          │ Python AST           │
        │ Evidence            │          │ Parameter Extract   │
        └──────────┬──────────┘          │ Pipeline Detection  │
                   │                     └──────────┬──────────┘
                   │                                │
                   └──────────────┬─────────────────┘
                                  ▼
                    ┌──────────────────────────┐
                    │   Paper ↔ Code Mapper    │
                    │                          │
                    │ matched                  │
                    │ mismatched               │
                    │ missing_in_code          │
                    │ missing_in_paper         │
                    │ uncertain                │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │   Evidence Verification  │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Deterministic Readiness  │
                    │         Score /100       │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Explain • Blockers       │
                    │ Warnings • Evidence      │
                    └──────────────────────────┘
```

---

# 🗄️ Data Architecture

```text
                         ┌──────────────┐
                         │    Papers    │
                         └──────┬───────┘
                                │
                                ▼
                       ┌────────────────┐
                       │  Experiments   │
                       └───────┬────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        Parameters         Evidence       Code Analysis
              │                │                │
              │                │        ┌───────┴────────┐
              │                │        │                │
              ▼                │        ▼                ▼
       Paper Values            │   Repository       Pipeline
                               │   Files             Stages
                               │        │                │
                               └────────┬┴────────────────┘
                                        ▼
                                ┌───────────────┐
                                │    Mappings   │
                                └───────┬───────┘
                                        │
                                        ▼
                                ┌───────────────┐
                                │   Readiness   │
                                │      /100     │
                                └───────────────┘
```

---

# 🔄 End-to-End Execution Flow

```text
1. Upload Paper
       ↓
2. Extract page-aware text
       ↓
3. Detect experiment sections
       ↓
4. Extract structured parameters
       ↓
5. Validate + verify evidence
       ↓
6. Persist experiment
       ↓
7. Submit GitHub repository
       ↓
8. Shallow clone repository
       ↓
9. Detect repository structure
       ↓
10. Analyze Python AST
       ↓
11. Extract canonical parameters
       ↓
12. Reconstruct training pipeline
       ↓
13. Load Part 1 experiment
       ↓
14. Map paper ↔ code
       ↓
15. Verify code evidence
       ↓
16. Calculate readiness
       ↓
17. Generate blockers + warnings
       ↓
18. Present reproducibility evidence
```

---

# 🧠 Canonical Parameter Intelligence

Different implementations often use different names for the same concept.

ReplicAI normalizes aliases into a canonical vocabulary.

```text
lr
learning_rate
learningRate
LR
       │
       ▼
learning_rate
```

Similarly:

```text
bs
batch
batch_size
batchSize
       │
       ▼
batch_size
```

This makes Paper ↔ Code comparison more robust.

---

# 🔌 API

## Paper Intelligence

### Analyze Paper

```http
POST /api/v1/paper/analyze
```

Upload a research PDF and create a structured paper analysis.

### Get Paper

```http
GET /api/v1/paper/{paper_id}
```

### Get Experiments

```http
GET /api/v1/paper/{paper_id}/experiments
```

### Get Experiment

```http
GET /api/v1/experiment/{experiment_id}
```

Returns experiment information together with its evidence.

---

## Code Intelligence

### Analyze Repository

```http
POST /api/v1/code/analyze
```

Example:

```json
{
  "repository_url": "https://github.com/owner/repo",
  "experiment_id": "1",
  "paper_id": "1",
  "branch": "main"
}
```

### Repository Summary

```http
GET /api/v1/repository/{repository_id}
```

### Repository Files

```http
GET /api/v1/repository/{repository_id}/files
```

### Paper ↔ Code Mappings

```http
GET /api/v1/repository/{repository_id}/mappings
```

### Readiness Report

```http
GET /api/v1/repository/{repository_id}/readiness
```

### Combined Analysis

```http
GET /api/v1/experiment/{experiment_id}/code-analysis
```

This provides a combined view of:

```text
Paper
+
Experiment
+
Repository
+
Parameters
+
Mappings
+
Pipeline
+
Readiness
+
Evidence
```

---

# 🧰 Tech Stack

| Layer             | Technology                 |
| ----------------- | -------------------------- |
| API               | FastAPI                    |
| Language          | Python 3.11                |
| Validation        | Pydantic                   |
| Database          | SQLite / PostgreSQL        |
| ORM               | SQLAlchemy                 |
| Migrations        | Alembic                    |
| PDF Processing    | Page-aware PDF extraction  |
| Code Analysis     | Python AST                 |
| Repository Source | GitHub HTTPS               |
| LLM               | Optional external provider |
| Testing           | Pytest                     |
| Linting           | Ruff                       |
| Type Checking     | Mypy                       |

---

# ⚙️ Environment Configuration

Copy:

```bash
.env.example
```

to:

```bash
.env
```

### Core Configuration

```env
DATABASE_URL=sqlite:///./replicai.db
MAX_UPLOAD_BYTES=...
LLM_API_KEY=...
LLM_MODEL=...
LLM_BASE_URL=...
APP_NAME=ReplicAI
```

### Code Intelligence

```env
CODE_ALLOWED_HOSTS=github.com
CODE_MAX_REPO_BYTES=67108864
CODE_MAX_FILE_COUNT=2000
CODE_MAX_FILE_BYTES=1048576
CODE_MAX_DEPTH=12
CODE_CLONE_TIMEOUT_SECONDS=60
CODE_MAX_ANALYSIS_SECONDS=60
CODE_LLM_ENABLED=true
```

---

# 🚀 Getting Started

## Windows

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Linux / macOS

```bash
python3.11 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

# ▶️ Run ReplicAI

```bash
uvicorn backend.main:app --reload
```

Then open:

### Health

```text
http://localhost:8000/health
```

### Swagger API

```text
http://localhost:8000/docs
```

---

# 🧪 Testing & Quality

ReplicAI includes automated validation across both Paper Intelligence and Code Intelligence.

```bash
pytest -q
```

Current test coverage includes:

```text
Part 1 — 15 tests
Part 2 — 73 tests
──────────────────
Total  — 88 tests
```

Additional quality checks:

```bash
ruff check .
ruff format --check .
mypy backend
```

### Current Definition of Done

```text
✅ GitHub HTTPS submission
✅ Safe shallow repository cloning
✅ Repository structure analysis
✅ File-role detection
✅ Python AST analysis
✅ Parameter extraction
✅ Canonical parameter normalization
✅ Training pipeline detection
✅ Part 1 experiment integration
✅ Paper ↔ Code parameter mapping
✅ Matched / mismatched / missing classification
✅ Evidence verification
✅ Deterministic readiness scoring
✅ Blocker / warning generation
✅ SQLite / PostgreSQL persistence
✅ Alembic migrations
✅ FastAPI integration
✅ 88 automated tests
✅ Ruff validation
✅ Ruff formatting validation
✅ Mypy validation
```

---

# 🔐 Design Principles

### 1. Evidence over assumptions

Every important extracted value should be traceable to its source.

### 2. Static analysis over execution

Repository code is inspected, not executed.

### 3. Deterministic over opaque

The readiness score and mapping logic are designed to be reproducible.

### 4. Explainability over a single number

ReplicAI does not stop at:

```text
Readiness: 72/100
```

It also explains:

```text
72/100

✓ 7 parameters matched
✗ 2 parameters mismatched
⚠ 1 parameter missing
⚠ Scheduler evidence uncertain

Blockers:
• Reported scheduler not found in implementation
```

### 5. LLM-assisted, not LLM-dependent

LLMs can improve extraction and interpretation, but deterministic fallbacks remain available.

---

# 🧪 Example Reproducibility Scenario

Imagine a research paper reports:

```text
Dataset       CIFAR-10
Optimizer     Adam
Learning Rate 0.001
Batch Size    64
Epochs        100
Metric        Accuracy
```

The associated repository contains:

```python
optimizer = Adam(model.parameters(), lr=0.001)

train_loader = DataLoader(
    dataset,
    batch_size=64
)

for epoch in range(50):
    train(...)
```

ReplicAI can surface:

```text
                    PAPER        CODE       STATUS

Dataset             CIFAR-10     CIFAR-10    ✓ MATCHED
Optimizer           Adam         Adam        ✓ MATCHED
Learning Rate       0.001        0.001       ✓ MATCHED
Batch Size          64           64          ✓ MATCHED
Epochs              100          50          ✗ MISMATCHED
Metric              Accuracy     Accuracy    ✓ MATCHED
```

Instead of manually searching through the repository, the researcher immediately sees **what aligns, what differs, and where the evidence comes from**.

---

# 🏆 Why ReplicAI?

Traditional reproducibility workflows often require:

```text
Read Paper
    ↓
Search GitHub
    ↓
Find Training Script
    ↓
Search Parameters
    ↓
Read Configs
    ↓
Compare Manually
    ↓
Make Notes
    ↓
Decide Whether It Looks Reproducible
```

ReplicAI transforms that into:

```text
             PAPER
               │
               ▼
          EXPERIMENT
               │
               ▼
            GITHUB
               │
               ▼
         CODE ANALYSIS
               │
               ▼
        PAPER ↔ CODE
               │
               ▼
           EVIDENCE
               │
               ▼
       READINESS /100
               │
               ▼
       EXPLAIN + PROVE
```

---

# 🧬 ReplicAI Architecture at a Glance

```text
┌──────────────────────────────────────────────────────────────┐
│                         ReplicAI                             │
│                                                              │
│  ┌────────────────────┐          ┌────────────────────────┐  │
│  │  PAPER INTELLIGENCE│          │    CODE INTELLIGENCE   │  │
│  │                    │          │                        │  │
│  │ PDF                │          │ GitHub URL             │  │
│  │ ↓                  │          │ ↓                      │  │
│  │ Text Extraction    │          │ Safe Clone              │  │
│  │ ↓                  │          │ ↓                      │  │
│  │ Experiment Detect  │          │ Structure Analysis      │  │
│  │ ↓                  │          │ ↓                      │  │
│  │ Parameter Extract  │          │ Python AST              │  │
│  │ ↓                  │          │ ↓                      │  │
│  │ Evidence           │          │ Parameters + Pipeline   │  │
│  └─────────┬──────────┘          └───────────┬────────────┘  │
│            │                                 │               │
│            └──────────────┬──────────────────┘               │
│                           ▼                                  │
│                 ┌────────────────────┐                       │
│                 │ PAPER ↔ CODE       │                       │
│                 │ MAPPING ENGINE     │                       │
│                 └─────────┬──────────┘                       │
│                           ▼                                  │
│                 ┌────────────────────┐                       │
│                 │ EVIDENCE VERIFIER  │                       │
│                 └─────────┬──────────┘                       │
│                           ▼                                  │
│                 ┌────────────────────┐                       │
│                 │ READINESS ENGINE   │                       │
│                 │       /100         │                       │
│                 └─────────┬──────────┘                       │
│                           ▼                                  │
│                 ┌────────────────────┐                       │
│                 │ EXPLAIN + PROVE    │                       │
│                 │                    │                       │
│                 │ Evidence           │                       │
│                 │ Blockers           │                       │
│                 │ Warnings           │                       │
│                 │ Mappings           │                       │
│                 └────────────────────┘                       │
└──────────────────────────────────────────────────────────────┘
```

---

# 📈 Project Status

## Part 1 — Paper Intelligence

**Status: ✅ Complete**

```text
PDF Processing              ✅
Experiment Detection        ✅
Parameter Extraction        ✅
Evidence Provenance         ✅
Pydantic Validation         ✅
Database Persistence        ✅
Alembic                     ✅
FastAPI API                 ✅
```

## Part 2 — Code Intelligence

**Status: ✅ Complete**

```text
Safe Repository Clone       ✅
Structure Analysis          ✅
Python AST Analysis         ✅
Parameter Normalization     ✅
Pipeline Detection          ✅
Paper ↔ Code Mapping        ✅
Evidence Verification       ✅
Readiness Scoring           ✅
Persistence                 ✅
API Integration             ✅
Testing                     ✅
```

---

# 🔮 Future Direction

ReplicAI's current system focuses on **analysis and reproducibility readiness**.

Possible future extensions include:

```text
                 Current
                    │
                    ▼
          Paper ↔ Code Analysis
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
    Execution Layer      Dataset Layer
          │                   │
          ▼                   ▼
    Reproduce Run       Dataset Verification
          │                   │
          └─────────┬─────────┘
                    ▼
             Result Comparison
                    │
                    ▼
             Explain Differences
                    │
                    ▼
              Reproducibility
                  Report
```

Future versions could therefore extend the workflow from:

> **"Does the implementation appear aligned with the paper?"**

toward:

> **"Can we execute the experiment and quantitatively compare the reproduced result with the reported result?"**

---

# 📜 Philosophy

ReplicAI is built around one principle:

> ### **Reproducibility should be inspectable, explainable, and evidence-backed.**

A paper should not be treated as a collection of claims.

A repository should not be treated as a black box.

ReplicAI connects the two.

---

<p align="center">

### 🧬 ReplicAI

**Paper → Experiment → Execute → Compare → Explain → Prove**

*Making ML reproducibility easier to inspect, understand, and verify.*

</p>
