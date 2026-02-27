# RL Hub V2 — Repository Structure

**For new AI engineers:** This document describes the unified RL Hub repository, including the merged **RL-Env-Studio** React app, Python backend, RL environments, and how everything fits together.

---

## Architecture Overview

RL Hub is a **single monorepo** with:

1. **Python backend** — FastAPI API, RL environments, verifiers, training
2. **Vanilla JS UIs** — Catalog and simulation console (served from `api/static/`)
3. **RL-Env-Studio** — React/Vite SPA (scenarios, verifiers, gym, training UI) merged and served at `/studio`
4. **Workflow definitions** — Jira workflows, mock data (JSON)

```
┌─────────────────────────────────────────────────────────────────┐
│                     RL Hub (port 8000)                           │
├─────────────────────────────────────────────────────────────────┤
│  /           → Catalog (vanilla JS)                              │
│  /test-console → Simulation Console (vanilla JS)                 │
│  /studio      → RL-Env-Studio (React SPA)                        │
│  /environments, /train, /kpis, ... → REST API                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
rl-hub V2/
├── api/                         # FastAPI backend
│   ├── main.py                  # REST API, static file serving
│   └── static/                  # Static assets (served at /static)
│       ├── index.html           # Catalog UI
│       ├── app.js               # Catalog logic
│       ├── simulation-console.html
│       ├── simulation-console.js
│       ├── styles.css
│       └── studio/              # RL-Env-Studio build output (generated)
│           ├── index.html
│           └── assets/
│
├── apps/                        # Applications and definitions
│   ├── RL-Env-Studio/           # React SPA (Dashboard, Scenarios, Verifiers, Gym)
│   │   ├── src/
│   │   │   ├── App.tsx
│   │   │   ├── main.tsx
│   │   │   └── components/      # Dashboard, Scenarios, Verifiers, Training, etc.
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   └── index.html
│   └── workflow_definitions/    # JSON workflow and mock data
│       ├── jira_workflows.json
│       ├── jira_mock_data.json
│       └── MOCK_DATA_CHANGES.md
│
├── environments/                # Gymnasium RL environments
│   ├── __init__.py
│   ├── base_environment.py
│   ├── clinical/                # Treatment pathway, sepsis, ICU, etc.
│   ├── imaging/                 # Imaging order, radiology scheduling
│   ├── jira/                    # Jira workflow envs
│   │   ├── jira_workflow_env.py
│   │   └── __init__.py
│   ├── population_health/
│   ├── revenue_cycle/
│   ├── clinical_trials/
│   ├── hospital_operations/
│   ├── telehealth/
│   ├── interoperability/
│   └── cross_workflow/
│
├── verifiers/                   # Reward verifiers
│   ├── base_verifier.py
│   ├── jira_verifier.py         # Aligns with apps/RL-Env-Studio Verifiers.tsx
│   ├── verifier_registry.py
│   └── ...
│
├── portal/                      # Environment registry
│   ├── environment_registry.py
│   └── environment_registry.json
│
├── policies/                    # RL policies (e.g. Jira SLM)
│   └── jira_slm_policy.py
│
├── observability/               # Reward logging, action traces
├── governance/                  # Safety, risk, compliance
├── orchestration/               # Cross-workflow orchestration
├── simulator/                   # Simulation engines
├── training/                    # Train PPO, DQN (stable-baselines3)
├── docs/                        # Documentation
│   └── TRAINING_FRAMEWORK.md   # Training frameworks (Gymnasium, SB3, SLM)
├── database/                    # PostgreSQL schema
├── models/                      # Trained models (ppo, slm, etc.)
├── tests/                       # pytest tests
├── scripts/
│
├── package.json                 # Root: npm run build:studio
├── requirements.txt
├── Dockerfile                   # Multi-stage: Node build + Python API
├── .github/workflows/ci.yml     # CI: test, install, build-studio, lint
├── README.md
└── REPO_STRUCTURE.md            # This file
```

---

## Key Files and Their Roles

| Path | Role |
|------|------|
| `api/main.py` | FastAPI app; serves `/`, `/test-console`, `/studio`, `/studio/*`, REST API |
| `apps/RL-Env-Studio/` | React SPA source; build output → `api/static/studio/` |
| `apps/workflow_definitions/jira_workflows.json` | Jira tool order, workflows; used by envs + verifiers |
| `apps/workflow_definitions/jira_mock_data.json` | Mock issues, comments; used by simulation console |
| `environments/jira/jira_workflow_env.py` | Jira RL env; uses workflow definitions |
| `verifiers/jira_verifier.py` | Jira reward verifier; aligns with Verifiers.tsx |
| `portal/environment_registry.py` | Registers all envs; `get_environment_class()`, `list_all_environments()` |
| `portal/environment_registry.json` | Env metadata (name, category, system) |
| `docs/TRAINING_FRAMEWORK.md` | Training frameworks (Gymnasium, stable-baselines3, SLM) |

---

## RL-Env-Studio Merge

**Before:** RL-Env-Studio lived as a separate app, typically run with `npm run dev` on port 3000.

**After:** RL-Env-Studio is built and served by the FastAPI API at `/studio`.

### Build Flow

1. `npm run build:studio` (root) → `cd apps/RL-Env-Studio && npm install && npm run build`
2. Vite outputs to `api/static/studio/` (see `vite.config.ts`: `base: '/studio/'`, `outDir: '../../api/static/studio'`)
3. API serves:
   - `GET /studio` → `api/static/studio/index.html`
   - `GET /studio/{path}` → file if exists, else SPA fallback (index.html)

### Development

- **API only:** `python -m api.main` → Catalog at `/`, Simulation at `/test-console`, Studio at `/studio` (if built)
- **Studio dev server:** `npm run dev:studio` → Vite dev on port 3000; API on 8000
- **Full stack:** Run API + Studio dev; point Studio to `http://localhost:8000` for API calls

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Catalog UI (index.html) |
| `GET /test-console` | Simulation console |
| `GET /studio` | RL-Env-Studio SPA |
| `GET /environments` | List environments with metadata |
| `GET /jira-mock-data` | Mock Jira issues and comments |
| `POST /train/{env_name}` | Start training |
| `GET /training/{job_id}` | Training status |
| `GET /kpis/{env_name}` | KPI metrics |
| `GET /validate/{env_name}` | Validate env load/step |

---

## Testing

```bash
pip install -r requirements.txt
python -m pytest tests/ -v --tb=short
```

Tests cover:

- Jira workflow definitions
- Jira environments (reset, step)
- Environment registry
- Integration (Jira + healthcare coexistence)
- API imports

---

## Docker Build

Multi-stage Dockerfile:

1. **Stage 1 (Node):** Build RL-Env-Studio → `api/static/studio/`
2. **Stage 2 (Python):** Copy studio build, run pytest, start API

```bash
docker build -t rl-hub .
docker run -p 8000:8000 rl-hub
```

---

## CI Pipeline

`.github/workflows/ci.yml`:

1. **test** — pytest, env registry validation, Jira env load
2. **install** — deps, server startup
3. **build-studio** — `npm run build:studio`, verify `api/static/studio/index.html`
4. **lint** — black, flake8

---

## Data Flow: Jira Example

1. **Definitions:** `apps/workflow_definitions/jira_workflows.json` (expected tool order)
2. **Mock data:** `apps/workflow_definitions/jira_mock_data.json` (issues, comments)
3. **Environment:** `environments/jira/jira_workflow_env.py` (Gymnasium env)
4. **Verifier:** `verifiers/jira_verifier.py` (reward for correct sequence)
5. **Studio UI:** `apps/RL-Env-Studio/src/components/Scenarios.tsx`, `Verifiers.tsx`
6. **Simulation:** `api/static/simulation-console.js` (loads mock data, runs Jira workflows)
7. **API:** `/jira-mock-data`, `/train/JiraIssueResolution`, `/kpis/JiraIssueResolution`

---

## Quick Start for New Engineers

```bash
# 1. Clone
git clone <repo-url>
cd "rl-hub V2"

# 2. Python backend
pip install -r requirements.txt
python -m pytest tests/ -v --tb=short
python -m api.main

# 3. (Optional) Build RL-Env-Studio
npm run build:studio

# 4. Open
# http://localhost:8000          — Catalog
# http://localhost:8000/test-console — Simulation
# http://localhost:8000/studio   — RL-Env-Studio
```

---

## Common Modifications

| Goal | Where |
|------|-------|
| Add Jira workflow | `apps/workflow_definitions/jira_workflows.json` |
| Add mock Jira data | `apps/workflow_definitions/jira_mock_data.json` |
| Change Jira env logic | `environments/jira/jira_workflow_env.py` |
| Change reward for Jira | `verifiers/jira_verifier.py` |
| Change Studio UI | `apps/RL-Env-Studio/src/components/` |
| Add API endpoint | `api/main.py` |
| Add env to registry | `portal/environment_registry.json` + env module |
