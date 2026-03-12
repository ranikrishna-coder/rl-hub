# AgentWork-Simulator — Changelog

> All changes made during the local development session (March 12–13, 2026).
> **6 files changed** — ~701 meaningful lines added / 86 removed (whitespace-normalized).

---

## Summary of Changes

| File | Lines Changed (meaningful) | Purpose |
|------|---------------------------|---------|
| `api/config.py` | +6 | New config for verifier SQLite DB path |
| `api/persistence.py` | +89 | New `VerifierStore` class for persistent verifier storage |
| `api/main.py` | +36 / −4 | Verifier persistence, Kubernetes classification fix |
| `api/static/app.js` | +175 | Scenario & verifier backend persistence, HF iframe fix |
| `api/static/training-config-data.js` | +400 / −6 | New SRE training run (`train_sre_03_12`) |
| `api/static/training.js` | +81 / −2 | Scenario dropdown, verifier loading, improvement metric fix |

---

## 1. Verifier Persistence (Backend)

### Problem
Custom verifiers created through the UI were stored only in an in-memory Python dictionary (`_verifier_store`). They were **lost on every server restart or page reload**.

### Changes

#### `api/config.py`
- Added `VERIFIER_STORE_DB_PATH` configuration variable pointing to `data/verifiers.db`.

#### `api/persistence.py`
- Added a new **`VerifierStore`** class — a full SQLite-backed CRUD store for verifier definitions.
- Methods: `list_all()`, `get()`, `upsert()`, `delete()`, `count()`, `list_by_environment()`, `db_size_bytes()`.
- Uses WAL journal mode and `ON CONFLICT` upsert for safe concurrent access.

#### `api/main.py`
- Replaced the in-memory `_verifier_store: Dict[str, dict] = {}` with a `VerifierStore` instance backed by SQLite.
- All CRUD endpoints (`POST`, `PUT`, `PATCH`, `GET`) now **read from and write to** the SQLite database in addition to the in-memory cache.
- Made the `system` field **optional** in `VerifierDefinition` (defaults to `"Custom"`) — the frontend was not always sending this field, causing 422 errors.
- Added `environment` query parameter to `GET /api/verifiers` for filtering verifiers by environment.

---

## 2. Kubernetes Classification Fix (Backend)

### Problem
Imported HuggingFace environments (e.g., SRE 24×7) were being classified as **"PyTorch"** instead of **"Kubernetes"** because the deep classifier gave higher scores to PyTorch signals (`torch` in dependencies) while Kubernetes had no dependency signals configured.

### Changes

#### `api/main.py`
- **`_SYSTEM_KEYWORDS["Kubernetes"]`**: Added `"kube"`, `"pod"`, `"namespace"`, `"deployment"` for better shallow classification.
- **`_DEEP_SYSTEM_SIGNALS["Kubernetes"]`**: Added `"kubernetes"` and `"kubectl"` to `deps` list; added `"k8s.yaml"` and `"kube"` to `files` list — so the deep classifier now correctly scores Kubernetes environments.

---

## 3. Scenario Persistence & Display (Frontend)

### Problem
- Scenarios added via the UI were only stored in a JavaScript in-memory array and **lost on reload**.
- The scenario list on the environment detail page only filtered by `category`, missing scenarios linked by `product` (environment name).
- The training page's scenario dropdown was **hardcoded to hidden** (`display: none`).

### Changes

#### `api/static/app.js`
- **`saveNewScenario()`**: Now sends a `POST` request to `/api/scenarios` to persist new scenarios to the backend SQLite database.
- **`buildScenariosSection()`**: Updated filter to match scenarios by `category` **OR** `product` (environment name).
- Added **`_loadPersistedScenarios()`**: Async function that fetches custom scenarios from `/api/scenarios?product={envName}` and merges them into the in-memory `TRAINING_CONFIG.scenarios` array, then re-renders the section.

#### `api/static/training.js`
- **`filterScenarios()`**: Completely rewritten — now populates the scenario dropdown with both built-in and custom scenarios (fetched from the backend), filtered by the selected environment's category or product name. The dropdown is shown when matching scenarios exist.

---

## 4. Verifier Persistence & Display (Frontend)

### Problem
- Custom verifiers created on the environment detail page were only stored in `window.VERIFIER_DATA.all` (in-memory) and **lost on reload**.
- The training page's verifier checkboxes only used hardcoded data from `verifier-data.js`, which had no entries for custom/imported environments.

### Changes

#### `api/static/app.js`
- **`saveNewVerifier()`**: Now sends a `POST` request to `/api/verifiers` to persist new verifiers to the backend.
- Added **`_loadPersistedVerifiers()`**: Async function that fetches all custom verifiers from `/api/verifiers`, normalizes their field names, and merges them into `window.VERIFIER_DATA.all`. Updates the verifier count badge on the detail page.

#### `api/static/training.js`
- **`populateVerifiers()`**: Rewritten to fetch custom verifiers from `/api/verifiers` and merge them with built-in verifiers (deduped by `id`), then render checkboxes. Falls back to built-in only on fetch failure.
- Extracted **`_renderVerifierOptions()`** helper for cleaner rendering logic.

---

## 5. HuggingFace Iframe "Not Found" Fix (Frontend)

### Problem
The "App" tab on the environment detail page embedded a HuggingFace Space in an iframe using the root URL (`https://owner-repo.hf.space`). Some Docker-based Spaces serve their app at a sub-path (e.g., `/web`) specified in the `README.md` front matter as `base_path`, causing a **"Not Found"** error.

### Changes

#### `api/static/app.js`
- **`_buildSimulationsContent()`**: Updated iframe `src` construction to include `base_path` from `details.frontMatter` or `openenv.base_path` if available:
  ```javascript
  var basePath = (details.frontMatter || {}).base_path || (openenv || {}).base_path || '';
  var iframeSrc = 'https://' + hfOwner + '-' + hfRepo + '.hf.space' + basePath;
  ```

---

## 6. SRE Training Run (`train_sre_03_12`) (Frontend)

### Problem
The user requested a new training run entry for the "SRE 24×7" environment using real training/evaluation data from `/home/Agentic/RL/data/`.

### Changes

#### `api/static/training-config-data.js`
- Added a complete training run entry `train_sre_03_12` to the `trainingRuns` array with:
  - **Job ID**: `k8s-sre-grpo-Qwen-Qwen3-0.6B-2026-03-11_00-35-44`
  - **Algorithm**: GRPO
  - **Model**: `Qwen/Qwen3-0.6B`
  - **Environment**: SRE 24×7
  - **Metrics**: Sourced from `training_metrics.json` and `eval_rollouts.json`
    - `avgReward`: 0.75 (eval trained model average)
    - `baselineReward`: 1.54 (eval baseline model average)
  - **Mock rollouts**: Populated from `eval_rollouts.json` — CrashLoopBackOff scenario for both baseline and trained model, with full step-by-step data and verifier results.
  - **Episodes**: 10 training episodes sourced from `training_rollouts.json` with per-step details.

---

## 7. Improvement Metric Display Fix (Frontend)

### Problem
The "Improvement" metric on the training page always prepended a `+` sign, even for negative values, resulting in display like `+-79%`.

### Changes

#### `api/static/training.js`
- Updated the improvement calculation to only prepend `+` for non-negative values:
  ```javascript
  var diff = (run.avgReward - run.baselineReward) * 100;
  return (diff >= 0 ? '+' : '') + diff.toFixed(0) + '%';
  ```

---

## Files NOT Changed (Context)

| File | Note |
|------|------|
| `api/static/verifier-data.js` | Hardcoded built-in verifier definitions — unchanged |
| `api/static/training.html` | Training page HTML — unchanged |
| `portal/environment_registry.py` | Built-in environment registry — unchanged |
| `api/persistence.py` (existing classes) | `EnvironmentStore` and `ScenarioStore` — unchanged |
| `requirements.txt` | No new Python dependencies added |

---

## Database Files Created (gitignored)

| File | Purpose |
|------|---------|
| `data/verifiers.db` | SQLite store for custom verifier definitions |
| `data/scenarios.db` | SQLite store for custom scenarios (pre-existing) |
| `data/environments.db` | SQLite store for custom environments (pre-existing) |
