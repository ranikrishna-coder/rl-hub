# AgentWork Simulator — Project Context Transfer

**Date**: 2026-03-05
**Repo**: https://github.com/CentificProduct/AgentWork-Simulator
**Branch**: `main`
**Latest Commit**: `4555a8b` — "Rollout comparison, verifier UX optimization, and training verifier cascade"
**Git Remotes**:
- `origin` → `git@github.com:ranikrishna-coder/rl-hub.git`
- `centific-prod` → `git@github.com:CentificProduct/AgentWork-Simulator.git`

---

## 1. Project Overview

AgentWork Simulator is a **Reinforcement Learning platform** for training and evaluating AI agents in production-ready enterprise workflow environments. It provides:

- **113 RL environments** across 4 industries (Finance, Healthcare, Enterprise Apps, Human Resources)
- **22+ integrated software systems** (Jira, Workday, Epic, SAP SuccessFactors, etc.)
- **Interactive simulation console** for step-by-step agent testing
- **Training pipeline** with PPO/A2C/DQN algorithms
- **Verifier system** (32 verifiers, 4 types) for reward signal evaluation
- **Human-in-the-Loop (HIL)** verifier support

### Tech Stack

- **Backend**: Python, FastAPI, Uvicorn (no database — all in-memory)
- **Frontend**: Vanilla HTML/JS/CSS (no React/npm/bundler)
- **Models**: Stable-Baselines3 (PPO, A2C, DQN)
- **Serving**: `python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000`

---

## 2. Directory Structure

```
AgentWork-Simulator/
├── api/
│   ├── main.py                          # FastAPI app — routes, models, training loop, APIs (2405 lines)
│   └── static/
│       ├── index.html                   # Catalog page (environment browser) (191 lines)
│       ├── app.js                       # Catalog JS — env cards, training config modal, training monitor (3145 lines)
│       ├── styles.css                   # Catalog + shared CSS (verifier, rollout comparison) (1159 lines)
│       ├── simulation-console.html      # Simulation console page (259 lines)
│       ├── simulation-console.js        # Simulation JS — env init, step execution, verifier cascade (2043 lines)
│       ├── test-console.css             # Simulation-specific CSS (880 lines)
│       ├── rollout-comparison.js        # Shared rollout comparison component (177 lines)
│       ├── verifier-data.js             # Centralized verifier registry — 32 verifiers (1042 lines)
│       ├── dashboard.html               # Dashboard page
│       ├── dashboard.js                 # Dashboard JS
│       ├── landing.html                 # Landing/home page
│       ├── landing.css                  # Landing page CSS
│       ├── human-eval.html              # Human evaluation page
│       ├── human-eval.css               # Human eval CSS
│       ├── contact.html                 # Contact page
│       ├── global-nav.css               # Global navigation CSS
│       ├── toast.js                     # Toast notification system
│       └── toast.css                    # Toast CSS
├── environments/                        # 113 RL environment definitions (Python classes)
├── portal/
│   └── environment_registry.py          # Environment discovery & registry
├── training/                            # Training utilities
├── simulator/                           # Simulation engine
├── verifiers/                           # Verifier implementations
├── policies/                            # RL policy definitions
├── models/                              # Saved model checkpoints (gitignored)
├── governance/                          # Governance configs
├── observability/                       # Monitoring/logging
├── tests/                               # Test suite
├── docs/                                # Documentation
└── .claude/
    └── launch.json                      # Dev server config (port 8000)
```

---

## 3. Key Routes (FastAPI)

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Landing page |
| `/catalog` | GET | Environment catalog (industry → persona → env cards) |
| `/catalog?industry=X&persona=Y` | GET | Filtered catalog view |
| `/test-console?env=X` | GET | Simulation console |
| `/dashboard` | GET | Dashboard |
| `/environments` | GET | All environments (JSON API) |
| `/api/environments` | GET | Environment list API |
| `/api/environments/{name}` | GET | Single environment details |
| `/api/environments/{name}/initialize` | POST | Initialize environment for simulation |
| `/api/environments/{name}/step` | POST | Execute one simulation step |
| `/api/training/start` | POST | Start training job |
| `/api/training/status/{job_id}` | GET | Training job status |
| `/api/training/stop/{job_id}` | POST | Stop training job |
| `/api/rollouts` | POST | Store a rollout record |
| `/api/rollouts/{env_name}` | GET | List rollouts for environment |
| `/api/rollout-comparison/{env_name}` | GET | Side-by-side baseline vs trained comparison |
| `/api/verifiers` | GET | List all verifiers |
| `/api/dashboard/record-activity` | POST | Record dashboard activity event |

---

## 4. Recent Implementation (Current Session)

### 4.1 Rollout Comparison (Pre-trained vs Post-trained)

**Purpose**: Side-by-side visualization comparing agent behavior before and after training.

**Components**:

- **`rollout-comparison.js`** (NEW): Shared IIFE component exposing `window.renderRolloutComparison(container, baseline, trained, meta)`. Renders two columns with:
  - Policy info (name, checkpoint label, reward, steps)
  - Rich timeline events (SYSTEM → gray, TOOL_CALL → green, TOOL_RESULT → blue)
  - Tool call summary badges
  - Final environment state (JSON)
  - Verifier results (PASS ✓ green / FAIL ✗ red)
  - Fallback: synthesizes timeline from basic step data when `timeline_events` is empty

- **Backend** (`main.py`):
  - `RolloutStepData.timeline_events: Optional[List[Dict[str, Any]]]` — per-step event timeline
  - `RolloutRecord` extended with: `policy_name`, `checkpoint_label`, `scenario_name`, `verifier_results`, `final_environment_state`
  - Training loop captures baseline rollout (first episode, `policy_name: "Random Baseline"`, `checkpoint_label: "base"`) and trained rollout (`policy_name: algorithm`, `checkpoint_label: f"step_{episode+1}"`)
  - `baseline_rollout_id` and `trained_rollout_id` stored on training job
  - `GET /api/rollout-comparison/{env}` with params: `baseline_id`, `trained_id`, `job_id`; auto-fallback logic to find most recent baseline/trained

- **Training monitor** (`app.js`):
  - "🔍 View Rollout Comparison" button appears when job has both rollout IDs
  - `window.openRolloutComparisonFromJob(jobId, envName)` fetches and renders inline

- **Simulation** (`simulation-console.js`):
  - `_simStartTime` tracks elapsed time via `performance.now()`
  - Steps recorded with rich timeline events (SYSTEM on step 1, TOOL_CALL, TOOL_RESULT)
  - After rollout POST, `_showSimRolloutComparison(envName)` fetches last 2 rollouts and renders in `#sim-rollout-comparison`

- **Old rollout UI removed**:
  - No more "View Rollouts" button on env cards
  - Removed: `openRolloutModal`, `renderRolloutList`, `viewRolloutDetail`, `renderRolloutDetail`
  - Removed: `#rollout-modal` div from `index.html`

### 4.2 Verifier UX Optimization (Simulation Console)

**Purpose**: The old verifier filter in the simulation window was choppy and cluttered. Optimized for compact, clean UX.

**Changes** (`simulation-console.html` + `test-console.css`):
- System dropdown + Type filter on **same row** using `.verifier-compact-controls` (flex)
- Full-width verifier dropdown below using `.verifier-main-dropdown`
- Clear button is tiny 24px circle `×` (`.verifier-clear-btn`)
- HIL notice shortened to "Human evaluation required."
- "Create New" → "+ New", separate "Clear" button removed
- Margins/paddings reduced ~30%, font sizes 0.78–0.82rem

### 4.3 Training Verifier Cascade Replication

**Purpose**: Training config modal's verifier selection now uses the same cascading dropdown system as the simulation console.

**Changes** (`app.js`):
- Replaced hardcoded verifier `<select>` with cascading HTML: system filter → type filter → verifier dropdown → info row → sub-filter → HIL notice
- New `_tv*` prefixed functions (to avoid collision with simulation verifier functions):
  - `_initTrainingVerifier(envName)`
  - `_tvPopulateSystemDropdown(activeSystem)`
  - `_tvPopulateVerifierDropdown(system, typeFilter)`
  - `_tvSetupListeners()`
  - `_tvUpdateInfoRow()`
  - `_tvUpdateSubFilter()`
  - `_tvUpdateHilNotice()`
  - `_tvGetSelectedVerifierConfig()`
- State variables: `_tvActiveSystem`, `_tvActiveTypeFilter`, `_tvSelectedVerifierId`
- Reads from shared `window.VERIFIER_DATA` (32 verifiers); falls back to old hardcoded logic if unavailable
- `submitTrainingConfig()` uses rich verifier config when available

**Shared CSS** (`styles.css`): Common verifier styles moved from `test-console.css` to `styles.css` so the training modal (served via `index.html`) inherits the same styling.

### 4.4 Prior Session Work (completed before this session)

- **Rollouts per environment card** — environment cards show rollout count
- **HIL verifier support** — 6 HIL verifiers among the 32 total
- **Verifier UX optimization (initial)** — compact dropdown system for simulation
- **HIL confirmation dialog in `startTraining()`** — warns before training with HIL verifier
- **Fixed stale DOM ID references** — `verifier-type` and `verifier-weights` replaced with `getSelectedVerifierConfig()` calls in `simulation-console.js`

---

## 5. Verifier System Architecture

### Data Source
`verifier-data.js` exposes `window.VERIFIER_DATA` — an array of 32 verifier objects:

```javascript
{
  id: "jira-issue-resolution",
  name: "Jira Issue Resolution",
  system: "Jira",
  type: "rule-based",        // rule-based | llm-based | hybrid | hil
  version: "v1",
  status: "active",
  environments: ["JiraIssueResolution"],
  sub_verifiers: [
    { id: "tool-sequence", name: "Tool Sequence", default_enabled: true },
    { id: "argument-validity", name: "Argument Validity", default_enabled: true },
    { id: "scoring-weights", name: "Scoring Weights", default_enabled: true }
  ],
  hil_required: false,
  scenarios: [...]
}
```

### Verifier Types (4)
- **rule-based**: Deterministic rule checking
- **llm-based**: LLM-powered evaluation
- **hybrid**: Combination of rules + LLM
- **hil**: Human-in-the-Loop evaluation (requires human confirmation)

### Systems (9)
Jira, Workday, Epic, SAP SuccessFactors, ADP, Cerner, Allscripts, Meditech, Athenahealth

### Cascade Flow (both simulation + training)
1. **System dropdown** — filters verifiers by software system (e.g., "Jira (5)")
2. **Type filter** — further filters by verifier type (e.g., "Rule-based")
3. **Verifier dropdown** — shows matching verifiers
4. **Info row** — displays type badge + system + version + status
5. **Sub-filter** — checkboxes for sub-verifiers (if verifier has them)
6. **HIL notice** — warning banner if verifier requires human evaluation

### Function Naming Convention
- **Simulation** (`simulation-console.js`): `getSelectedVerifierConfig()`, `populateVerifierDropdown()`, `updateVerifierInfoRow()`, etc.
- **Training** (`app.js`): `_tvGetSelectedVerifierConfig()`, `_tvPopulateVerifierDropdown()`, `_tvUpdateInfoRow()`, etc. — prefixed with `_tv` to avoid naming collision

---

## 6. Rollout Data Model

### RolloutStepData
```python
class RolloutStepData(BaseModel):
    step: int
    action: Optional[str] = None
    reward: float = 0.0
    state_summary: Optional[Dict[str, Any]] = None
    reward_breakdown: Optional[Dict[str, float]] = None
    timeline_events: Optional[List[Dict[str, Any]]] = None  # NEW
```

### Timeline Event Structure
```json
{
  "timestamp_ms": 412,
  "event_type": "TOOL_CALL",        // SYSTEM | TOOL_CALL | TOOL_RESULT
  "content": "...",                  // For SYSTEM and TOOL_RESULT
  "tool_name": "triage_ticket",     // For TOOL_CALL
  "tool_args": {"issue_key": "ISK2"} // For TOOL_CALL
}
```

### RolloutRecord
```python
class RolloutRecord(BaseModel):
    environment_name: str
    episode_number: int
    steps: List[RolloutStepData]
    initial_state: Optional[Dict[str, Any]] = None
    final_outcome: Optional[Dict[str, Any]] = None
    total_reward: float = 0.0
    total_steps: int = 0
    status: str = "completed"
    source: str = "simulation"         # simulation | training
    job_id: Optional[str] = None
    timestamp: Optional[str] = None
    policy_name: Optional[str] = None           # NEW — e.g., "Random Baseline", "PPO"
    checkpoint_label: Optional[str] = None      # NEW — e.g., "base", "step_300"
    scenario_name: Optional[str] = None         # NEW
    verifier_results: Optional[List[Dict]] = None  # NEW — [{check, passed, reason}]
    final_environment_state: Optional[Dict] = None # NEW
```

### Comparison API
```
GET /api/rollout-comparison/{environment_name}
  ?baseline_id=UUID        (optional)
  ?trained_id=UUID         (optional)
  ?job_id=UUID             (optional — auto-lookup from job)

Response: { environment_name, baseline: RolloutRecord|null, trained: RolloutRecord|null }
```

Auto-fallback logic:
1. If `job_id` provided → look up `baseline_rollout_id` and `trained_rollout_id` from job
2. If specific IDs not found → search most recent rollout with `checkpoint_label == "base"` as baseline, most recent with `source == "training"` as trained

---

## 7. Training System

### Training Config Modal (app.js: `openTrainingConfig()`)
- **Software system selector** — sets training context, updates verifier suggestions
- **Agent model** — PPO (default), A2C, DQN
- **Reward verifier** — cascading dropdown (system → type → verifier)
- **Training parameters**: Dataset URL, Episodes (default 100), Max steps per episode (default 1000)
- **Advanced settings**: Learning rate, discount factor, batch size, entropy coefficient
- **HIL guard**: If selected verifier has `hil_required: true`, shows confirmation dialog before starting

### Training Flow (main.py)
1. `POST /api/training/start` → creates job, starts background thread
2. Background thread runs:
   - Baseline phase: runs N random episodes, captures first episode as baseline rollout
   - Training phase: runs PPO/A2C/DQN with Stable-Baselines3
   - Evaluation phase: runs trained model, captures rollout with timeline events
3. `baseline_rollout_id` and `trained_rollout_id` stored on job
4. `GET /api/training/status/{job_id}` → returns job with progress, metrics, rollout IDs

### Training Monitor (app.js: `displayTrainingJob()`)
- Shows progress bar, episode metrics, reward graph
- When complete and both rollout IDs exist: shows "🔍 View Rollout Comparison" button
- `openRolloutComparisonFromJob()` fetches comparison API and renders inline

---

## 8. Simulation Console

### Flow
1. Select software system → select environment → select verifier (optional)
2. "Initialize Environment" → `POST /api/environments/{name}/initialize`
3. "Step Forward" or "Auto Run" → `POST /api/environments/{name}/step`
4. Each step records: action, reward, state summary, timeline events
5. On completion: `POST /api/rollouts` to store the rollout
6. Auto-renders rollout comparison if 2+ rollouts exist for the environment

### Key State Variables (simulation-console.js)
- `currentEnvironment` — selected environment name
- `stepCount` — current step number
- `totalReward` — cumulative reward
- `currentRolloutSteps` — array of step data with timeline events
- `_simStartTime` — `performance.now()` timestamp at initialization

---

## 9. CSS Architecture

### Shared Styles (`styles.css` — loaded by `index.html` / catalog)
- Verifier cascade styles: `.verifier-compact-controls`, `.verifier-compact-select`, `.verifier-clear-btn`, `.verifier-main-dropdown`, `.verifier-info-row`, `.verifier-sub-filter`, `.sub-verifier-chip`, `.hil-notice`
- Type badge styles: `.verifier-type-badge`, `.vtype-rule-based`, `.vtype-llm-based`, `.vtype-hybrid`, `.vtype-hil`
- Rollout comparison: `.rc-container`, `.rc-header`, `.rc-columns` (CSS grid 1fr 1fr), `.rc-column`, `.rc-col-baseline` (gray accent), `.rc-col-trained` (purple accent), `.rc-timeline`, `.rc-event`, `.rc-event-system/tool-call/tool-result`, `.rc-summary`, `.rc-code`, `.rc-verifier-check`

### Simulation-Specific (`test-console.css`)
- Overrides for simulation page context
- Kept: `#verifier-section h3`, `.verifier-advanced-details`, `.verifier-action-row`, type badge overrides

### Design System
- Primary purple: `#7c3aed`
- Accent gradient: `linear-gradient(135deg, #a855f7, #7c3aed)`
- Border radius: `0.625rem` (10px)
- Font sizes: body 0.85rem, labels 0.78rem, badges 0.68rem
- Card shadows: `0 1px 4px rgba(0,0,0,0.06)`

---

## 10. Running the App

```bash
cd /Users/kausalyarani.k/Documents/AgentWork-Simulator
python3 -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Or via `.claude/launch.json`:
```json
{
  "version": "0.0.1",
  "configurations": [{
    "name": "dev",
    "runtimeExecutable": "python3",
    "runtimeArgs": ["-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"],
    "port": 8000
  }]
}
```

**Known issue**: `ModuleNotFoundError: No module named 'environments.telehealth.follow_up_optimization'` — pre-existing missing environment file. Does not affect app functionality.

---

## 11. Key API Test Commands

```bash
# List environments
curl http://localhost:8000/api/environments

# Initialize an environment
curl -X POST http://localhost:8000/api/environments/JiraIssueResolution/initialize

# Run a step
curl -X POST http://localhost:8000/api/environments/JiraIssueResolution/step \
  -H 'Content-Type: application/json' -d '{"action": "get_issue"}'

# Store a rollout
curl -X POST http://localhost:8000/api/rollouts \
  -H 'Content-Type: application/json' -d '{
    "environment_name": "jira-service-desk",
    "episode_number": 1,
    "steps": [{"step":1,"action":"test","reward":5.0}],
    "total_reward": 5.0, "total_steps": 1, "status": "completed",
    "source": "simulation", "policy_name": "Random Baseline", "checkpoint_label": "base"
  }'

# Get rollout comparison
curl http://localhost:8000/api/rollout-comparison/jira-service-desk

# Start training
curl -X POST http://localhost:8000/api/training/start \
  -H 'Content-Type: application/json' -d '{
    "environment_name": "JiraIssueResolution",
    "algorithm": "PPO",
    "episodes": 10,
    "max_steps_per_episode": 100
  }'

# Check training status
curl http://localhost:8000/api/training/status/{job_id}
```

---

## 12. Pending / Known Issues

1. **Telehealth module missing**: `environments.telehealth.follow_up_optimization` — needs file created or registry entry removed
2. **In-memory storage**: All rollouts, training jobs, and state are in-memory — lost on server restart. No database persistence.
3. **Models directory**: `models/a2c/` and `models/ppo/` contain generated checkpoint files (gitignored)
4. **Rollout comparison in simulation**: Only shows comparison when 2+ rollouts exist for the same environment name; the environment name must match exactly between rollouts
