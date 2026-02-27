## RL Hub – Architecture & Requirements

This document captures the current architecture, product vision, requirements, and testing/operational model for **RL Hub** as implemented in this repository.

---

## 1. Product Vision

**RL Hub** is a platform for:

- **Designing, simulating, and training** reinforcement learning (RL) agents across a catalog of workflow environments.
- **Bridging multiple domains** – currently:
  - A rich set of **healthcare and operations** environments (clinical, imaging, hospital operations, revenue cycle, etc.).
  - A family of **Jira workflow environments** (Issue Resolution, Status Update, Comment Management, Subtask Management).
- Providing a **full loop from design → simulation → training → human evaluation** so domain experts can:
  - Explore environments and understand what they optimize.
  - Run interactive simulations to understand behavior.
  - Train RL or SLM (sequence-learning model) policies.
  - Perform **human-in-the-loop (HITL) evaluation** of model outputs, with structured scoring.

The near-term deployment target is **Render** (Dockerized FastAPI backend serving static frontends).

---

## 2. High-Level System Overview

### 2.1 Main Components

- **FastAPI backend (`api/main.py`)**
  - Serves:
    - REST API for training, monitoring, KPIs, Jira operations, and human evaluation.
    - Static assets for:
      - Environment catalog (`index.html`, `app.js`, `styles.css`).
      - Simulation Console (`simulation-console.html`, `simulation-console.js`, `test-console.css`).
      - Human Evaluation Console (`human-eval.html`).
      - Optional RL-Env-Studio build at `/static/studio`.
  - Manages in-memory training jobs (`training_jobs` dict).
  - Exposes a healthcheck endpoint for Render.

- **Environments (`environments/`)**
  - `base_environment.py` – `HealthcareRLEnvironment` + base RL environment abstractions.
  - Domain packages: `clinical/`, `imaging/`, `hospital_operations/`, `revenue_cycle/`, `population_health/`, `telehealth/`, `clinical_trials/`, `interoperability/`, `cross_workflow/`.
  - `jira/jira_workflow_env.py` – encapsulates Jira workflows defined in `apps/workflow_definitions/jira_workflows.json`, plus helpers for Jira-specific logic and reward signals.

- **Environment registry (`portal/environment_registry.py`)**
  - Discovers and describes all environments via a registry JSON.
  - Backed by `list_all_environments()` and `get_environment_class()` used by the API and frontends.

- **Verifiers (`verifiers/`)**
  - Encapsulate reward/verification logic:
    - Clinical, operational, financial, compliance verifiers.
    - Jira-specific verifiers and ensemble logic.
  - `verifier_registry.py` provides a central registration point.

- **Observability (`observability/`)**
  - `RewardLogger`, `ActionTraceLogger`, `EpisodeMetricsTracker`, `AuditLogger`.
  - Used in `run_training` to capture episode-level traces and KPIs.

- **Governance (`governance/`)**
  - `safety_guardrails.py`, `risk_thresholds.py`, `compliance_rules.py`.
  - Wraps environment actions to enforce guardrails (e.g., safe ranges, risk thresholds).

- **Frontends (`api/static/`)**
  - **Catalog UI** (`index.html`, `app.js`, `styles.css`):
    - Lists & filters environments (domain, category, system).
    - Launches training via `/train/{env_name}`.
    - Provides a **Training Monitor** and links to the **Human Evaluation Console**.
  - **Simulation Console** (`simulation-console.html`, `simulation-console.js`, `test-console.css`):
    - Runs client-side simulations for any environment.
    - Has special logic for Jira environments (mock data + optional live Jira).
    - Provides a local-only human evaluation widget for simulation runs.
  - **Human Evaluation Console** (`human-eval.html`):
    - Light-themed, two-column HITL console.
    - Left: run/episode context & metadata.
    - Right: reasoning steps (with per-step scoring), final output, and overall Yes/No decision.

- **Workflow definitions & mock data (`apps/workflow_definitions/`)**
  - `jira_workflows.json` – structure and tool orders for Jira workflows (issue_resolution, status_update, comment_management, subtask_management).
  - `jira_mock_data.json` – Jira issues, transitions, reward config, and scenarios; used for training and simulation when not pointing at live Jira.
  - `MOCK_DATA_CHANGES.md` – describes changes/dev notes for mock data.

- **Models (`models/`)**
  - `ppo/`, `slm/`, etc. – pre-trained model artifacts (by ID) and metadata JSONs.
  - Used for download & reference; backend doesn’t yet persist training_runs beyond in-memory `training_jobs` plus saved model artifacts.

- **Tests (`tests/`)**
  - `test_environment_registry_jira.py` – validates Jira envs are present in registry and instantiable.
  - `test_jira_environments.py` – RL behavior of Jira envs (rewards, correct/wrong actions).
  - `test_integration_jira_healthcare.py` – ensures Jira and healthcare envs co-exist and can run sequentially.
  - `test_jira_status_update_scenario.py` – ensures Jira mock data and workflows support the “In Progress → Blocked” scenario and have reward weights.
  - `test_jira_workflow_definition.py` – validates the Jira workflow definition JSON structure.
  - `test_jira_slm_e2e.py` – end-to-end SLM training test for JiraIssueResolution. Skips in CI when the SLM model cannot be downloaded (e.g. 403 from Hugging Face).

### 2.2 High-Level Architecture Diagram

```mermaid
flowchart LR
    subgraph Browser
        Catalog["Catalog UI (index.html + app.js)"]
        SimConsole["Simulation Console (simulation-console.html + JS)"]
        HumanEval["HITL Evaluation Console (human-eval.html)"]
        Studio["RL-Env-Studio (optional React SPA build)"]
    end

    Catalog -->|REST/JSON| API
    SimConsole -->|REST/JSON| API
    HumanEval -->|REST/JSON| API
    Studio -->|REST/JSON| API

    subgraph Backend[FastAPI Backend (api/main.py)]
        API["FastAPI app<br/>/train, /training, /environments,<br/>/human-eval, /jira/*, /kpis"]
        Registry["Environment Registry<br/>(portal/environment_registry)"]
        Envs["Environments<br/>(environments/*)"]
        Verifiers["Verifiers<br/>(verifiers/*)"]
        Obs["Observability<br/>(reward_logger, action_trace_logger, episode_metrics, audit_logger)"]
        Gov["Governance<br/>(safety_guardrails, risk_thresholds, compliance_rules)"]
        Jobs["Training Jobs (in-memory dict)"]
        Models["Saved Models (models/*)"]
    end

    API --> Registry
    API --> Jobs
    API --> Models
    Registry --> Envs
    Envs --> Verifiers
    Envs --> Gov
    Envs --> Obs

    subgraph External
        Jira["Live Jira Cloud/Server (optional)"]
    end

    API -->|/jira/*| Jira
```

---

## 3. Functional Requirements

### 3.1 Environment Catalog & Discovery

1. **List environments**
   - The system shall expose `GET /environments` returning a JSON list with:
     - `name`, `category`, `system`, `description`, and other metadata from `environment_registry`.
   - The catalog UI shall render all environments and show counts.

2. **Filter environments**
   - The catalog shall support filtering by:
     - **Domain**: `All`, `Enterprise apps`, `Operational workflows`.
     - **Category**: e.g. `jira`, `clinical`, `imaging`, etc.
     - **System**: values derived from the registry (e.g. `Jira (Atlassian)`, `Epic`, etc.).

3. **Environment detail view**
   - Clicking “View details” opens an environment detail page (single-page overlay) with:
     - Description, use cases, actions/feature summary from the registry + `app.js` maps.
     - Link(s) to:
       - Start training (opens Training panel).
       - Launch Simulation Console for that environment (by query param `?env=EnvName`).

### 3.2 Training Workflows

1. **Start training**
   - Endpoint: `POST /train/{environment_name}`.
   - Request body:
     - `algorithm`: `"PPO"`, `"DQN"`, `"A2C"`, `"SAC"`, `"SLM"`, etc.
     - `num_episodes`: integer.
     - `max_steps`: integer per episode.
     - `config`: environment-specific configuration dict.
   - Response body:
     - `job_id`, initial status (`queued`/`running`), and any immediate metadata.

2. **Run training**
   - Server shall start training in a background task (`run_training` in `api/main.py`), using:
     - `get_environment_class` + `HealthcareRLEnvironment` subclasses.
     - Verifier registry for reward shaping.
     - Observability loggers for rewards, actions, episode metrics, and audit logs.
   - On completion:
     - `training_jobs[job_id]` is updated with:
       - `status` (`completed` or `failed`).
       - `results` (mean/max/min reward, episodes, totals).
       - For Jira SLM: `slm_training_context` & `slm_explainability` (if SLM model loads).
       - For Jira Subtask Management PPO: `subtask_log_url` for episodic logs.
       - `model_url` and `model_path` when models are saved.

3. **Monitor training**
   - Endpoint: `GET /training/{job_id}` shall return the current job snapshot from `training_jobs`.
   - The Training Monitor (in `app.js`) shall:
     - Poll for status.
     - Render:
       - Progress bar (episodes completed / total).
       - Reward metrics.
       - Model download section (if `model_url` present).
       - Jira Subtask log section (`subtask_log_url`) for that env.
       - Error box for `status="failed"` with `error` and `error_traceback`.
       - SLM explainability panel when `algorithm === 'SLM'`.
     - Show the **Human Evaluation** section with:
       - “Open Human Evaluation” button linking to `/static/human-eval.html?job_id={job_id}`.
       - Last human evaluation summary if `last_human_evaluation` is present.

4. **Human evaluation (training jobs)**
   - Endpoint: `POST /human-eval/{job_id}` with body:
     - `decision: "yes" | "no"`.
     - `comments?: string`.
     - `step_scores?: [{ step_index: int, score: "correct" | "flawed" | "critical_error" }]`.
   - Behavior:
     - Persist eval into `training_jobs[job_id].human_evaluations` and `last_human_evaluation`.
     - Return `{ success, job_id, evaluation, total_evaluations }`.

### 3.3 Simulation Console

1. **Initialize environment**
   - Simulation Console uses:
     - `GET /environments` and `portal` registry to populate the environment dropdown.
     - `GET /kpis/{environment_name}` for KPI config + sample run initialization.
   - User selects:
     - Environment category/system.
     - Environment-specific configuration fields (driven by `environmentConfigs` in `simulation-console.js`).
     - Verifier type and optional weights.

2. **Run simulation**
   - All state and metrics are maintained **client-side** in JS.
   - User can:
     - Step manually.
     - Auto-run at different speeds.
   - Console shows:
     - Current state (queues, items, tasks, Jira issues or subtasks).
     - Current action.
     - Action history.
     - Metrics panel:
       - **Step Count**.
       - **Total Reward**.
       - Bottom panel “Run Summary” and “Lagging Indicators”:
         - Steps completed, total reward, episode completion.
         - Average reward/step, steps to completion.

3. **Jira-specific simulation**
   - For Jira environments, simulation uses:
     - `apps/workflow_definitions/jira_mock_data.json` as its data source (fetched via `GET /jira-mock-data`).
     - Mapping between environment names and Jira workflows (`JIRA_ENV_TO_WORKFLOW` in `simulation-console.js`).
     - Reward and scenario configuration consistent with Jira envs in Python.
   - For Jira Subtask Management:
     - Can create or delete subtasks in simulation against mock data.
     - Can optionally call **live Jira** for subtasks if configured and enabled.
     - Logs subtask episodes to a JSON log for download.

4. **Human evaluation (simulation runs)**
   - A **local “Human Evaluation” panel** allows:
     - Yes/No decision and comment.
     - Stored in `sessionStorage`, not the backend.
   - Intended for quick feedback in simulation, not for RLHF data storage (which lives in `/human-eval/{job_id}`).

### 3.4 Jira Integration

1. **Mock data-based flows**
   - Issue resolution, status update, comment management, and subtask flows are driven from:
     - `jira_workflows.json` (tool sequences, scenarios).
     - `jira_mock_data.json` (issues, transitions, reward configuration).
   - Tests assert:
     - At least one `In Progress` issue has a `Blocked` transition (e.g. PROJ-101).
     - `reward_config.status_reward_weights` contains “Blocked”.
     - Workflow `status_update` has `in_progress_to_blocked` scenario.

2. **Live Jira flows**
   - Controlled by `.env` keys:
     - `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`, `JIRA_SUBTASK_ISSUE_TYPE_NAME`, etc.
   - Endpoints:
     - `POST /jira/subtasks` – create subtask for a given parent.
     - `DELETE /jira/issues/{issue_key}/subtasks` – delete all subtasks under a parent issue (preserves parent).
   - Training or simulation can toggle between mock and live via config flags (`JIRA_USE_LIVE_FOR_TRAINING`, environment config).

### 3.5 Human Evaluation Console Details

1. **Run context**
   - Displays:
     - Job ID.
     - Environment name.
     - Algorithm.
     - Training status.

2. **Episode summary & model metadata**
   - Summarizes:
     - How many episodes were run and completed.
     - Mean reward.
     - Basic training metadata (from `job.results`).

3. **Reasoning steps**
   - Derived from:
     - SLM explainability (`job.slm_explainability`) when present:
       - Prompt snippet, parsed tool, correct next tool, action, explanation.
     - Training outcome (episodes completed, rewards).
   - For each step, evaluator can select:
     - **Correct**
     - **Flawed**
     - **Critical Error**
   - Step scores are included in the `POST /human-eval/{job_id}` body and persisted in training jobs.

4. **Final output & overall evaluation**
   - Shows final outcome metrics (mean reward, episodes, algorithm).
   - Evaluator records final Yes/No decision and comment.
   - Step score summary is computed on save and shown as:
     - “N Correct, M Flawed, K Critical Error”.

---

## 4. Non-Functional Requirements

### 4.1 Performance

- Training should:
  - Handle tens to low hundreds of episodes per job within minutes, depending on environment complexity.
  - Use simple, CPU-friendly algorithms (PPO, DQN, etc. through stable-baselines or custom logic) – no GPU dependency assumed in this deployment.
- API endpoints:
  - `GET /environments`, `GET /training/{job_id}`, `GET /kpis/{env}` should respond within **<300ms** under normal load.
  - `/jira/*` endpoints should be dominated by Jira API latency; backend overhead should be minimal.
- Frontends:
  - Static assets served by FastAPI only (no SSR), so perceived latency is primarily initial asset load + API calls.
  - Simulation console updates are all local; step rendering should remain responsive (<50ms per step) for typical queues.

### 4.2 Scalability

- **Backend**
  - Stateless except for `training_jobs` (in-memory). For multi-instance or long-running production:
    - Future requirement: move job store to a persistent DB or cache (Postgres, Redis).
  - Designed as a monolith but with clear subpackages (environments, verifiers, observability, governance).
  - Dockerized for horizontal scaling behind a load balancer; training jobs would need sticky sessions or shared job store.

- **Frontends**
  - Pure static assets; trivial to host behind a CDN.
  - Catalog & simulation console rely on REST APIs; scaling is primarily backend-side.

### 4.3 Reliability & Availability

- Render deployment:
  - Healthcheck at `/` (or root FastAPI health) ensures container restarts on failure.
  - Tests are run in Docker build (`pytest tests/`), failing build if:
    - Jira mock data or workflow definitions are inconsistent.
    - Jira environments can’t load.
    - Integration tests between Jira and healthcare envs fail.
  - Jira SLM E2E test skips in CI when the model can’t load (403/network), ensuring builds can pass with fallback.

### 4.4 Security

- Jira credentials:
  - Loaded via `.env` at startup using `_load_local_env_file`; `.env` is not committed and is ignored in VCS.
  - For Jira settings, `.env` values override environment variables to simplify configuration inside app repo.
  - Jira API tokens must not be logged or returned to the client.
- CORS:
  - `fastapi.middleware.cors` configured with explicit development/deployment origins, with optional extension via `CORS_ORIGINS` env var.
  - Current implementation effectively allows all origins but is structured to be tightened for production.
- Attack surface:
  - No direct DB exposure (DB not active); primary risk area is Jira proxy endpoints (/jira/*).
  - Input validation via Pydantic models and explicit request schemas (e.g. `HumanEvalRequest`).

### 4.5 Maintainability

- Code organization:
  - Backend (api), domain logic (environments), registry (portal), verifiers, governance, observability, workflows (apps/workflow_definitions), tests.
  - Frontends are separated under `api/static/` and are self-contained JS/HTML.
- Patterns:
  - Environment registry centralizes discovery.
  - Verifier registry decouples reward logic from environments.
  - Observability and governance are layered onto environments, not hard-coded inside.
  - Tests are domain-specific and succinct, focusing on invariants.
- Documentation:
  - `README.md`, usage guides, and environment creation docs.
  - This `architect.md` serves as the system-level architecture and requirements document.

---

## 5. Key API Contracts (Selected)

### 5.1 Environment Registry & KPIs

- `GET /environments`
  - **Response:** `{ "environments": [ { "name": str, "category": str, "system": str, ... }, ... ] }`

- `GET /kpis/{environment_name}`
  - **Query params:** optional `episode_id`, `verifier_type`, `verifier_config`.
  - **Response:** `{ "kpis": { "clinical_outcomes": {...}, "operational_efficiency": {...}, "financial_metrics": {...} }, "episode_summary": {...} }`

### 5.2 Training & Jobs

- `POST /train/{environment_name}`
  - **Body:**
    ```json
    {
      "algorithm": "PPO",
      "num_episodes": 100,
      "max_steps": 1000,
      "config": { "...": "..." }
    }
    ```
  - **Response:** `{ "job_id": "uuid", "status": "queued" | "running", ... }`

- `GET /training/{job_id}`
  - **Response example (simplified):**
    ```json
    {
      "job_id": "uuid",
      "environment_name": "JiraIssueResolution",
      "algorithm": "PPO",
      "status": "completed",
      "num_episodes": 100,
      "results": {
        "total_episodes": 100,
        "episodes_completed": 100,
        "mean_reward": 0.42,
        "max_reward": 0.9,
        "min_reward": -0.1
      },
      "slm_training_context": { "...": "..." },
      "slm_explainability": { "...": "..." },
      "subtask_log_url": "/models/ppo/.../subtasks.json",
      "model_url": "/models/ppo/.../model.zip",
      "human_evaluations": [ ... ],
      "last_human_evaluation": { ... }
    }
    ```

### 5.3 Jira API

- `POST /jira/subtasks`
  - **Body:** includes parent key, summary, description, etc.
  - **Behavior:** creates a subtask under given parent in live Jira (if configured).

- `DELETE /jira/issues/{issue_key}/subtasks`
  - Deletes all subtasks under the specified parent issue in live Jira; preserves the parent.

### 5.4 Human Evaluation

- `POST /human-eval/{job_id}`
  - **Request:**
    ```json
    {
      "decision": "yes",
      "comments": "Looks good",
      "step_scores": [
        { "step_index": 0, "score": "correct" },
        { "step_index": 1, "score": "flawed" }
      ]
    }
    ```
  - **Response:**
    ```json
    {
      "success": true,
      "job_id": "uuid",
      "evaluation": {
        "decision": "yes",
        "comments": "Looks good",
        "timestamp": "2026-02-27T08:30:00Z",
        "step_scores": [...]
      },
      "total_evaluations": 3
    }
    ```

---

## 6. Test Cases & UAT Scenarios

### 6.1 Automated Tests (Pytest)

The `tests/` directory covers:

- **Environment registry & Jira presence** – registry consistency, environment classes load correctly.
- **Jira environment behavior** – reset, rewards for correct vs wrong actions, workflow order enforcement.
- **Integration** – Jira and healthcare envs can both be discovered and run without conflict.
- **Jira workflow definitions & mock data** – JSON structure, presence of specific scenarios (“In Progress → Blocked”) and reward weights.
- **Jira SLM E2E** – training flow and SLM loading (skipped when network/SLM unavailable; see test).

### 6.2 Recommended UAT Scenarios

Below are high-value manual test scenarios for UAT before deployment.

#### 6.2.1 Catalog & Discovery

- **UAT-001 – Environment listing**
  - Steps:
    1. Open `/` (catalog).
    2. Confirm total environment count matches `GET /environments`.
    3. Filter by `Enterprise apps` domain and `Jira` category.
    4. Confirm only Jira environments appear (Issue Resolution, Status Update, Comment Management, Subtask Management).
  - Expected:
    - Counts and filters match backend.

- **UAT-002 – Environment detail view**
  - Steps:
    1. Click “View details” on `JiraSubtaskManagement`.
    2. Verify description, use-case text, and actions summary.
    3. Confirm buttons/links to Training and Simulation present.
  - Expected:
    - Detail content matches `portal` registry metadata.

#### 6.2.2 Training & Monitoring

- **UAT-010 – PPO training for JiraIssueResolution**
  - Steps:
    1. From catalog, start PPO training for `JiraIssueResolution` with ~20 episodes.
    2. Open Training Monitor and track job until completion.
  - Expected:
    - Job reaches `completed`.
    - Reward stats visible.
    - Model download & info visible if model-saving enabled.

- **UAT-011 – JiraSubtaskManagement training & subtask log**
  - Steps:
    1. Start PPO training for `JiraSubtaskManagement`.
    2. After completion, locate Subtask Action Log section.
    3. Download JSON log and inspect episodes where `create_subtask` was used.
  - Expected:
    - Log URL is valid and serves a well-formed JSON log.

- **UAT-012 – SLM training (online)**
  - Steps:
    1. Ensure environment has network and correct Hugging Face credentials (if needed).
    2. Train `JiraIssueResolution` with `algorithm: SLM`.
    3. Monitor for `slm_training_context.uses_slm = true`.
  - Expected:
    - SLM model loads successfully.
    - Explainability panel shows a prompt, parsed tool, and explanation.

#### 6.2.3 Simulation Console

- **UAT-020 – Generic simulation**
  - Steps:
    1. Open `/test-console`.
    2. Select a healthcare environment (e.g. `ImagingOrderPrioritization`).
    3. Initialize environment and run a few steps.
  - Expected:
    - State, current action, and metrics update each step.
    - Run Summary & Lagging Indicators reflect step count and total reward.

- **UAT-021 – Jira Status Update scenario**
  - Steps:
    1. In Simulation Console, choose `JiraStatusUpdate`.
    2. Select scenario “Change from in-progress to blocked”.
    3. Run steps until completion.
  - Expected:
    - At least one issue with `In Progress → Blocked` path is simulated.
    - Run Summary indicates completion; relevant KPIs update.

- **UAT-022 – Jira Subtask Management (mock)**
  - Steps:
    1. Choose `JiraSubtaskManagement`, “Create sub task” scenario.
    2. Initialize and run steps; simulate subtask creation in mock data.
    3. Use “Download” button for Jira subtask log in Simulation panel.
  - Expected:
    - JSON log of created subtasks is downloaded (mock; no live Jira calls unless enabled).

#### 6.2.4 Human Evaluation

- **UAT-030 – HITL eval from Training Monitor**
  - Steps:
    1. After a training job completes, open that job in Training Monitor.
    2. Confirm Human Evaluation section appears with “Open Human Evaluation”.
    3. Click the button, go to `human-eval.html?job_id=...`.
    4. Score reasoning steps (Correct/Flawed/Critical Error) as appropriate.
    5. Select Yes/No decision and submit.
  - Expected:
    - API returns success.
    - HITL console shows “Saved” with step score summary.
    - Refreshing Training Monitor shows updated Last Evaluation + count.

- **UAT-031 – Simulation human eval panel**
  - Steps:
    1. In Simulation Console, run any environment.
    2. Use the Human Evaluation panel on the right to mark Yes/No and optional comments.
  - Expected:
    - Panel displays “Recorded: Yes/No …”.
    - Page reload clears local status; data is not sent to backend (local-only).

---

## 7. Key Architectural Decisions & Trade-Offs

### 7.1 Monolith vs Microservices

- **Decision:** Use a single FastAPI monolith that:
  - Serves REST APIs and static files.
  - Owns environment registry, training orchestration, Jira integration, and human evaluation.
- **Pros:**
  - Simple deployment (single Docker image).
  - Lower operational overhead.
  - Easier for contributors to understand the entire system.
- **Cons:**
  - All features share the same release cadence.
  - Scaling independently by component (e.g. training vs catalog) requires additional logic (e.g. separate workers in the future).
- **Future:** If usage grows, we can split training workers into a separate service that consumes jobs from a queue while the main FastAPI app becomes a thin control-plane API.

### 7.2 In-Memory Job Store vs Persistent DB

- **Decision:** Store training job state in an in-memory dict `training_jobs` for now.
- **Pros:**
  - Very simple to implement and reason about.
  - Fast lookups with no DB overhead.
  - Fine for single-instance deployments and short-lived jobs.
- **Cons:**
  - Jobs are lost on restart.
  - Multiple instances would not share job state (harder to scale out horizontally).
  - No historical analytics without exporting or persisting results.
- **Future:** Introduce a persistent backing store (Postgres or Redis) and treat `training_jobs` as a cache view.

### 7.3 Static Frontends vs SPA Everywhere

- **Decision:** Keep primary UIs as vanilla HTML + JS (`index.html`, `simulation-console.html`, `human-eval.html`) with an optional React SPA (RL-Env-Studio) for advanced workflows.
- **Pros:**
  - Minimal bundle size; easy to host from FastAPI’s static file mount.
  - Low build complexity for the main UI.
  - RL-Env-Studio can evolve independently as an advanced UI layer.
- **Cons:**
  - Less code sharing across frontends.
  - Harder to reuse complex components without a component framework.

### 7.4 SLM Integration

- **Decision:** Integrate SLM (sequence-learning model) for Jira workflow tool selection, but allow a **rule-based fallback** when the model cannot be loaded (e.g. network/403).
- **Pros:**
  - Environments remain functional without external dependencies.
  - Enables CI in locked-down environments (tests pass with fallback).
  - Allows gradual rollout of SLM capabilities.
- **Cons:**
  - Behavior differs between “SLM loaded” and fallback.
  - Requires careful instrumentation and documentation for users to know whether SLM is active.

---

## 8. Operations & Deployment Notes

- **Deployment target:** Render (Docker)
  - Dockerfile:
    - **Stage 1:** Optionally builds RL-Env-Studio if `apps/RL-Env-Studio/package.json` exists; otherwise logs a message and leaves `api/static/studio` empty.
    - **Stage 2:** Installs Python dependencies, copies code, copies Studio build (empty or real), runs `pytest tests/` as part of the build, then defines the run command (`python -m api.main`).
  - Healthcheck configured to call root endpoint periodically.

- **Environment configuration:**
  - `.env` in project root is loaded at startup; Jira-related keys override process env for ease of configuration in app repos.
  - CORS origins may be extended via `CORS_ORIGINS`.

- **Monitoring & logs:**
  - Training logs are printed to stdout in the container.
  - Reward, action, and audit logs can be extended to send to external observability stacks in the future.

---

## 9. System Design Checklist (for future changes)

When adding new features or environments, ensure:

- **Functional**
  - [ ] New environment is defined in `environments/*` and registered via the portal registry.
  - [ ] Tests cover its registration and at least one happy-path episode.
  - [ ] UI descriptions and use-cases are added to the catalog in `app.js`.
  - [ ] If needed, Simulation Console config is extended in `simulation-console.js`.

- **Non-Functional**
  - [ ] Reward/verification logic is added via verifiers where appropriate.
  - [ ] Governance (safety/risk/compliance) is respected for high-risk environments.
  - [ ] New Jira or external integrations validate input and handle partial failures.

- **Testing**
  - [ ] Pytest tests added to `tests/` (do not leave one-off test_*.py at repo root).
  - [ ] E2E tests avoid hard dependence on external model downloads or services; use skip logic where necessary.

- **Docs**
  - [ ] README and, where needed, `architect.md` updated with new flows, endpoints, or decisions.

This document should be kept current as the system evolves, especially when:
- New domains are added (beyond healthcare and Jira).
- Training storage moves from in-memory to a persistent store.
- RL-Env-Studio becomes the primary UI instead of the current static pages.

