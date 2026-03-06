# AgentWork Simulator — Repository Structure

**For new AI engineers:** This document describes the unified AgentWork Simulator repository, including the Python backend, vanilla JS frontend, RL environments, and how everything fits together.

---

## Architecture Overview

AgentWork Simulator is a **single monorepo** with:

1. **Python backend** — FastAPI API, RL environments, verifiers, training
2. **Vanilla JS frontend** — Catalog, simulation console, training console, dashboard (served from `api/static/`)
3. **Workflow definitions** — Jira workflows, mock data (JSON)

```
┌─────────────────────────────────────────────────────────────────┐
│                AgentWork Simulator (port 8000)                   │
├─────────────────────────────────────────────────────────────────┤
│  /              → Landing page                                   │
│  /catalog       → Catalog (vanilla JS)                           │
│  /test-console  → Simulation Console (vanilla JS)                │
│  /training-console → Training Console (vanilla JS)               │
│  /dashboard     → Analytics Dashboard (vanilla JS)               │
│  /environments, /train, /kpis, ... → REST API                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
agentwork-simulator/
├── api/                         # FastAPI backend
│   ├── main.py                  # REST API, static file serving
│   └── static/                  # Static assets (served at /static)
│       ├── index.html           # Catalog UI
│       ├── app.js               # Catalog logic
│       ├── simulation-console.html
│       ├── simulation-console.js
│       ├── training.html        # Training console
│       ├── training.js          # Training logic
│       ├── training.css         # Training styles
│       ├── training-config-data.js  # Training config (hardcoded, future: API)
│       ├── dashboard.html
│       ├── dashboard.js
│       ├── human-eval.html
│       ├── styles.css
│       ├── global-nav.css
│       ├── verifier-data.js     # Verifier definitions
│       └── rollout-comparison.js
│
├── apps/                        # Applications and definitions
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
│   ├── jira_verifier.py
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
├── package.json                 # Root: npm start
├── requirements.txt
├── Dockerfile                   # Python API
├── .github/workflows/ci.yml     # CI: test, install, lint
├── README.md
└── REPO_STRUCTURE.md            # This file
```

---

## Key Files and Their Roles

| Path | Role |
|------|------|
| `api/main.py` | FastAPI app; serves `/catalog`, `/test-console`, `/training-console`, `/dashboard`, REST API |
| `api/static/training.js` | Training console logic (vanilla JS) |
| `api/static/training-config-data.js` | Hardcoded training config (`window.TRAINING_CONFIG`); future: replace with API |
| `apps/workflow_definitions/jira_workflows.json` | Jira tool order, workflows; used by envs + verifiers |
| `apps/workflow_definitions/jira_mock_data.json` | Mock issues, comments; used by simulation console |
| `environments/jira/jira_workflow_env.py` | Jira RL env; uses workflow definitions |
| `verifiers/jira_verifier.py` | Jira reward verifier |
| `portal/environment_registry.py` | Registers all envs; `get_environment_class()`, `list_all_environments()` |
| `portal/environment_registry.json` | Env metadata (name, category, system) |
| `docs/TRAINING_FRAMEWORK.md` | Training frameworks (Gymnasium, stable-baselines3, SLM) |

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Landing page |
| `GET /catalog` | Catalog UI |
| `GET /test-console` | Simulation console |
| `GET /training-console` | Training console |
| `GET /dashboard` | Analytics dashboard |
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

```bash
docker build -t agentwork-simulator .
docker run -p 8000:8000 agentwork-simulator
```

---

## CI Pipeline

`.github/workflows/ci.yml`:

1. **test** — pytest, env registry validation, Jira env load
2. **install** — deps, server startup
3. **lint** — black, flake8

---

## Data Flow: Jira Example

1. **Definitions:** `apps/workflow_definitions/jira_workflows.json` (expected tool order)
2. **Mock data:** `apps/workflow_definitions/jira_mock_data.json` (issues, comments)
3. **Environment:** `environments/jira/jira_workflow_env.py` (Gymnasium env)
4. **Verifier:** `verifiers/jira_verifier.py` (reward for correct sequence)
5. **Frontend:** `api/static/` (catalog, simulation console, training console)
6. **API:** `/jira-mock-data`, `/train/JiraIssueResolution`, `/kpis/JiraIssueResolution`

---

## Quick Start for New Engineers

```bash
# 1. Clone
git clone <repo-url>
cd agentwork-simulator

# 2. Python backend
pip install -r requirements.txt
python -m pytest tests/ -v --tb=short
python -m api.main

# 3. Open
# http://localhost:8000              — Landing page
# http://localhost:8000/catalog      — Catalog
# http://localhost:8000/test-console — Simulation
# http://localhost:8000/training-console — Training
# http://localhost:8000/dashboard    — Dashboard
```

---

## Common Modifications

| Goal | Where |
|------|-------|
| Add Jira workflow | `apps/workflow_definitions/jira_workflows.json` |
| Add mock Jira data | `apps/workflow_definitions/jira_mock_data.json` |
| Change Jira env logic | `environments/jira/jira_workflow_env.py` |
| Change reward for Jira | `verifiers/jira_verifier.py` |
| Change training UI | `api/static/training.js`, `training.html` |
| Change catalog UI | `api/static/app.js`, `index.html` |
| Add API endpoint | `api/main.py` |
| Add env to registry | `portal/environment_registry.json` + env module |
