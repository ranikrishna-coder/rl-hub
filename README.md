# AgentWork Simulator

A platform for designing, simulating, and training reinforcement learning agents across **113 Gymnasium-compatible environments** spanning healthcare, enterprise, and HR/payroll workflows.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Frontend** | Vanilla HTML/JS/CSS (no build step) |
| **RL Framework** | Gymnasium, Stable-Baselines3, PyTorch |
| **Data** | MariaDB (environments, scenarios, verifiers, contact); in-memory (training jobs, rollouts) |
| **Deployment** | Docker, Azure |

### Backend / API

| Framework | Purpose |
|-----------|---------|
| FastAPI | Web API framework |
| Uvicorn | ASGI server |
| Pydantic | Request/response validation and schemas |

### Reinforcement Learning / ML

| Framework | Purpose |
|-----------|---------|
| Gymnasium | RL environment API (successor to OpenAI Gym) |
| Stable-Baselines3 | RL algorithms (PPO, DQN, A2C, etc.) |
| PyTorch | Deep learning backend for SB3 |

### Data & Computation

| Framework | Purpose |
|-----------|---------|
| NumPy | Numerical computing |
| SciPy | Scientific computing |
| Pandas | Data processing |

### Database & Persistence

| Framework | Purpose |
|-----------|---------|
| MariaDB | Persistence for environments, scenarios, verifiers, contact form (configure via MARIADB_* env vars) |
| PyMySQL | MariaDB/MySQL driver |
| SQLAlchemy | ORM and DB abstractions (optional) |

### Frontend

| Technology | Purpose |
|------------|---------|
| Vanilla JavaScript | UI logic (no React/Vue/Angular) |
| HTML5 / CSS3 | Structure and styling |

### Other

| Framework | Purpose |
|-----------|---------|
| TensorBoard | Training and metrics visualization |
| Matplotlib / Seaborn | Plots and charts |
| pytest / httpx | Tests and API testing |
| requests | HTTP client (e.g. Jira API) |

## Quick Start

```bash
# Clone and setup
git clone git@github.com:CentificProduct/AgentWork-Simulator.git
cd AgentWork-Simulator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# (Optional) Configure Jira integration
cp .env.example .env   # Edit with your Jira credentials

# Run
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/catalog` | Environment catalog with industry journey (fin-sim, healthcare-sim, Enterprise-sim, HR-sim) |
| `/training-console` | Configure, run, and monitor RL training; Rollouts tab for browsing episodes |
| `/test-console` | Interactive simulation console |
| `/human-eval` | Human-in-the-loop evaluation |
| `/contact` | Feedback form |

## Architecture

```
agentwork-simulator/
├── api/                        # FastAPI backend + static frontend
│   ├── main.py                 # REST API, training loop, rollout store
│   ├── persistence.py          # MariaDB stores (EnvironmentStore, ScenarioStore, VerifierStore)
│   ├── data/                   # Local data dir (gitignored; legacy JSON migration)
│   └── static/                 # Frontend (6 HTML pages, 7 JS, 7 CSS)
│       ├── app.js              # Catalog UI logic
│       ├── training.js         # Training console (stepper, charts, rollout)
│       ├── simulation-console.js  # Simulation engine
│       ├── rollout-comparison.js  # Side-by-side rollout renderer
│       └── training-config-data.js  # Scenarios, agents, algorithms, sample runs
├── environments/               # 113 Gymnasium RL environments
│   ├── base_environment.py     # HealthcareRLEnvironment base class
│   ├── clinical/               # 20 environments (Epic, Cerner, Allscripts)
│   ├── imaging/                # 15 environments (Philips, GE Healthcare)
│   ├── population_health/      # 15 environments (Health Catalyst, Innovaccer)
│   ├── revenue_cycle/          # 15 environments (Change Healthcare)
│   ├── clinical_trials/        # 15 environments (Veeva, IQVIA)
│   ├── hr_payroll/             # 9 environments (Workday, SAP SuccessFactors, ADP)
│   ├── hospital_operations/    # 5 environments
│   ├── telehealth/             # 5 environments (Teladoc, Amwell)
│   ├── interoperability/       # 5 environments (InterSystems, Orion Health)
│   ├── cross_workflow/         # 5 multi-agent environments
│   └── jira/                   # 4 Jira workflow environments
├── apps/workflow_definitions/  # Jira workflows and mock data
├── portal/                     # Environment registry (discovery + metadata)
├── verifiers/                  # 7 verifier types (clinical, financial, Jira, etc.)
├── observability/              # Reward, action, episode, audit loggers
├── governance/                 # Safety guardrails, risk thresholds, compliance
├── models/                     # Saved model artifacts (runtime, gitignored)
├── tests/                      # Pytest suite
└── requirements.txt
```

## Environments (113 across 11 categories)

| Category | Count | Systems |
|----------|-------|---------|
| Clinical | 20 | Epic, Cerner, Allscripts |
| Imaging | 15 | Philips, GE Healthcare, PACS |
| Population Health | 15 | Health Catalyst, Innovaccer |
| Revenue Cycle | 15 | Change Healthcare |
| Clinical Trials | 15 | Veeva, IQVIA |
| HR & Payroll | 9 | Workday, SAP SuccessFactors, ADP |
| Hospital Operations | 5 | Staffing, OR, Supply Chain |
| Telehealth | 5 | Teladoc, Amwell |
| Interoperability | 5 | InterSystems, Orion Health |
| Cross-Workflow | 5 | Multi-agent coordination |
| Jira | 4 | Atlassian Jira Cloud/Server |

All environments inherit from `HealthcareRLEnvironment` and implement the Gymnasium interface (`reset`, `step`, `action_space`, `observation_space`).

## Training

### Supported Algorithms

| Algorithm | Description |
|-----------|-------------|
| **GRPO** | Group Relative Policy Optimization (recommended) |
| **PPO** | Proximal Policy Optimization |
| **DPO** | Direct Preference Optimization |
| **A2C** | Advantage Actor-Critic |

### Supported Agents

| Agent | Base Model | Trainable |
|-------|-----------|-----------|
| Qwen 1.7B Instruct | qwen-1.7b-instruct | Yes |
| LLaMA 3.2 1B | llama-3.2-1b | Yes |
| Mistral 7B Instruct | mistral-7b-instruct-v0.3 | Yes |
| GPT-4o (Baseline) | gpt-4o | No |

### Training Console Features

- **5-step progress stepper**: Configuration → Baseline Eval → Training → Evaluation → Complete
- **Rollout comparison**: Side-by-side pre/post training with named tool calls, arguments, verifier results, and final environment state
- **Real-time progress**: Polling-based status updates with reward charts
- **Model artifact management**: View metadata, copy model path
- **Training scenarios**: 113 RL environments used as training scenarios, filtered by system
- **2 sample training runs**: Pre-configured demo runs (Jira GRPO + Clinical PPO) with full detail pages and rollout comparison
- **Rollouts tab**: Browse all rollouts across environments with filtering and detail views (Messages, Tool Calls, Full JSON)
- **LLM Judge verifier**: Create verifiers with Prompt, Model, Examples, and Failure Policy configuration
- **New Training Run form**: 4-section layout — Name, Environment (system), Training Data & Evaluation (scenario + verifier), Agent & Training Method
- **API-ready agent config**: Agents and algorithms fetched from `/api/training/config` with fallback to defaults

### API Training Flow

```bash
# Start training
curl -X POST http://localhost:8000/train/JiraIssueResolution \
  -H "Content-Type: application/json" \
  -d '{"algorithm": "GRPO", "num_episodes": 320, "max_steps": 50}'

# Check status
curl http://localhost:8000/training/{job_id}

# List all jobs
curl http://localhost:8000/api/training/jobs
```

## Reward Function

All environments use a weighted reward function:

```
Reward = w_clinical * clinical_score
       + w_efficiency * efficiency_score
       + w_financial * financial_score
       - w_risk * risk_penalty
       - w_compliance * compliance_penalty
```

Weights are configurable per environment.

## Verifiers

Seven verifier types validate agent behavior:

- **Clinical** — clinical outcome quality
- **Operational** — workflow efficiency
- **Financial** — cost and revenue metrics
- **Compliance** — regulatory adherence
- **Jira** — workflow tool sequence and transition validation
- **Ensemble** — multi-verifier aggregation
- **Base** — abstract interface

## Data Persistence

User-created data is stored in **MariaDB** (configured via `MARIADB_*` env vars). Create the database and tables using `database/schema_mariadb.sql` or let the app create tables on first use.

| Table | Contents |
|-------|----------|
| `user_environments` | Custom environments created via the Add Environment form |
| `user_scenarios` | User-created training scenarios per environment |
| `user_verifiers` | User-created verifiers per environment |
| `contact_submissions` | Contact form submissions |

### Persistence Stores (`api/persistence.py`)

| Store | Table | Key Operations |
|-------|-------|----------------|
| `EnvironmentStore` | `user_environments` | CRUD for custom envs, backups, health snapshots |
| `ScenarioStore` | `user_scenarios` | Add, list, delete scenarios by environment/product |
| `VerifierStore` | `user_verifiers` | Add, list, delete verifiers by environment |

### What persists vs in-memory

| Data | Storage | Survives Restart |
|------|---------|-----------------|
| Custom environments | MariaDB | ✅ Yes |
| Scenarios (user-created) | MariaDB | ✅ Yes |
| Verifiers (user-created) | MariaDB | ✅ Yes |
| Contact form submissions | MariaDB | ✅ Yes |
| Built-in 113 environments | Python registry (in-memory) | ✅ Yes (code) |
| Training jobs & rollouts | In-memory dict | ❌ No |

### Deployment Safety

Back up your MariaDB database and credentials. The `api/data/` directory is gitignored (used for legacy JSON migration only). Docker deployments can pass `MARIADB_*` env vars to the container.

### Schema Migration

Stores auto-migrate on startup using `ALTER TABLE ADD COLUMN` where needed for forward compatibility.

## Testing

```bash
python -m pytest tests/ -v --tb=short
```

Tests cover Jira workflow definitions, RL environment behavior, registry integration, and coexistence between Jira and healthcare environments.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/environments` | List all 113 environments |
| POST | `/train/{env_name}` | Start training run |
| GET | `/training/{job_id}` | Training job status |
| GET | `/api/training/jobs` | List all training jobs |
| GET | `/api/rollout-comparison/{env}` | Rollout comparison data |
| GET | `/api/rollouts/{env}` | Rollout history |
| GET | `/api/rollouts/{env}/{id}` | Rollout detail (full step data) |
| GET | `/api/rollouts-all` | All rollouts across environments |
| GET | `/api/training/config` | Agent & algorithm config (future) |
| GET | `/kpis/{env_name}` | KPI metrics |
| POST | `/human-eval/{job_id}` | Submit human evaluation |
| GET | `/jira-mock-data` | Jira mock data |
| PUT | `/api/environments/{name}/system` | Update environment system name |
| PUT | `/api/environments/{name}/category` | Update environment category |
| GET | `/api/environments/{name}/scenarios` | List scenarios for environment |
| POST | `/api/environments/{name}/scenarios` | Add scenario to environment |
| DELETE | `/api/environments/{name}/scenarios/{id}` | Delete a scenario |
| GET | `/api/environments/{name}/verifiers` | List verifiers for environment |
| POST | `/api/environments/{name}/verifiers` | Add verifier to environment |
| DELETE | `/api/environments/{name}/verifiers/{id}` | Delete a verifier |
| POST | `/api/environments/{name}/clone-scenarios` | Clone scenarios to new environment |
| POST | `/api/environments/{name}/clone-verifiers` | Clone verifiers to new environment |

Full API docs at `http://localhost:8000/docs` (Swagger UI).

## Documentation

- **Architecture & requirements**: [architect.md](architect.md)
- **Repository structure**: [REPO_STRUCTURE.md](REPO_STRUCTURE.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Training framework**: [docs/TRAINING_FRAMEWORK.md](docs/TRAINING_FRAMEWORK.md)

## License

Proprietary - Centific
# test
