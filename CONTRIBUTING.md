# Contributing to AgentWork Simulator

Thanks for your interest in contributing! This guide will help you get set up and contributing quickly.

## Getting Started

### Prerequisites

- **Python 3.9+** (3.11 recommended)
- **Git**
- **MariaDB 10.3+** or MySQL (for persistence; configure via MARIADB_* env vars)

### 1. Clone the Repository

```bash
git clone git@github.com:ranikrishna-coder/rl-hub.git
cd rl-hub
```

### 2. Set Up Python Environment

```bash
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

You will need Jira credentials if working on Jira-related environments. Ask the team lead for the shared development credentials or create your own Jira Cloud API token at https://id.atlassian.com/manage-profile/security/api-tokens.

### 4. Run the Test Suite

Always run tests before submitting changes:

```bash
python -m pytest tests/ -v --tb=short
```

### 5. Start the Dev Server

```bash
python -m api.main
```

Then open http://localhost:8000 to access the web catalog, simulation console, training console, and dashboard.

## Development Workflow

### Branching Strategy

We use a feature-branch workflow:

1. **Create a branch** from `main` for your work:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Naming conventions** for branches:
   - `feature/` — new functionality (e.g., `feature/add-pharmacy-env`)
   - `fix/` — bug fixes (e.g., `fix/reward-calculation-overflow`)
   - `refactor/` — code restructuring (e.g., `refactor/simulator-base-class`)
   - `docs/` — documentation changes (e.g., `docs/update-api-guide`)

3. **Push your branch** and open a Pull Request against `main`.

### Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR.
- Write a clear title and description of what changed and why.
- Reference any related issues (e.g., "Closes #42").
- Make sure CI passes (tests, lint) before requesting review.
- Request review from at least one team member.

### Code Style

- **Python**: We use `black` for formatting and `flake8` for linting.
  ```bash
  black .                        # auto-format
  flake8 . --select=E9,F63,F7,F82  # check for critical issues
  ```
- **JavaScript** (frontend): Follow the existing patterns in `api/static/`.
- Write docstrings for public classes and functions.

## Adding a New RL Environment

All environments inherit from `HealthcareRLEnvironment`. To add a new one:

1. **Create the environment file** in the appropriate category folder under `environments/` (e.g., `environments/clinical/my_new_env.py`).

2. **Implement the required interface**:
   - `__init__()` — define observation/action spaces
   - `reset()` — return initial observation
   - `step(action)` — return (observation, reward, terminated, truncated, info)

3. **Register the environment** in `portal/environment_registry.json` so it appears in the catalog and API.

4. **Add tests** in `tests/` to validate reset, step, rewards, and registry loading.

5. **Run the full test suite** to confirm nothing is broken:
   ```bash
   python -m pytest tests/ -v --tb=short
   ```

## Running with Docker

If you prefer Docker:

```bash
docker compose up --build
```

This builds the full stack and serves at http://localhost:8000.

## Project Structure at a Glance

```
environments/    — RL environment implementations (8 categories, 50 envs)
simulator/       — Simulation engines (patient, hospital, financial, clinical trial)
api/             — FastAPI backend + static web assets
apps/            — Workflow definitions
portal/          — Environment registry
training/        — PPO/DQN training scripts
tests/           — Test suite
orchestration/   — Cross-workflow optimization
```

See [REPO_STRUCTURE.md](REPO_STRUCTURE.md) for a detailed breakdown.

## CI/CD

Our GitHub Actions pipeline runs automatically on push/PR to `main`:

- **Test** — pytest across Python 3.9–3.12
- **Lint** — black + flake8 checks
- **Install Test** — confirms clean install + server startup

All checks must pass before merging.

## Getting Help

- Check existing docs: `README.md`, `QUICK_START.md`, `USAGE_GUIDE.md`, `REPO_STRUCTURE.md`
- Open an issue on GitHub for bugs or feature requests
- Reach out to the team on Slack/Teams for questions
