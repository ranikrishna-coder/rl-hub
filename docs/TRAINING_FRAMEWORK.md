# AgentWork Simulator — Training Framework Documentation

This document describes the frameworks, libraries, and pipelines used for reinforcement learning training in AgentWork Simulator.

---

## Overview

| Component | Framework | Purpose |
|-----------|-----------|---------|
| **RL environments** | [Gymnasium](https://gymnasium.farama.org/) (≥0.29) | Standard `reset`, `step`, `observation_space`, `action_space` interface |
| **PPO / DQN (standalone)** | [stable-baselines3](https://stable-baselines3.readthedocs.io/) (≥2.0) | Gradient-based policy optimization |
| **SLM (Jira)** | Remote model endpoint (HTTP) | Tool selection via configurable inference API; no local model |
| **API training loop** | Custom Python | Episode-based rollouts; action source varies by algorithm |
| **Deep learning backend** | [PyTorch](https://pytorch.org/) (≥2.0) | Used by stable-baselines3 and Transformers |

---

## Training Paths

### 1. API Training (`POST /train/{environment_name}`)

Triggered via the web catalog, RL-Env-Studio, or REST API. Uses a **custom episode loop** in `api/main.py` (`run_training`).

- **Episodes:** Configurable (e.g. 100 default, 320 for Jira envs)
- **Max steps per episode:** Configurable (e.g. 1000 default, 50 for Jira)
- **Action source:**
  - **SLM:** `JiraSLMPolicy` — Calls a remote model endpoint (set `JIRA_MODEL_ENDPOINT`) to predict the next tool. Used for Jira environments (JiraIssueResolution, JiraStatusUpdate, JiraCommentManagement). If the endpoint is not set, uses a rule-based fallback.
  - **PPO / DQN / other:** `env.action_space.sample()` — Random actions. No gradient-based learning.

- **Output:** Saves model metadata JSON (mean/max/min reward, episodes completed) and exposes results via `GET /training/{job_id}`.

API training does **not** use stable-baselines3. For PPO/DQN it runs episodes with random actions and records rewards.

### 2. Standalone Training Scripts (`training/`)

Scripts that use **stable-baselines3** for full RL training:

| Script | Algorithm | Framework | Description |
|--------|-----------|-----------|-------------|
| `training/train_ppo.py` | PPO | stable-baselines3 | Proximal Policy Optimization with vectorized envs, EvalCallback, CheckpointCallback |
| `training/train_dqn.py` | DQN | stable-baselines3 | Deep Q-Network with replay buffer, exploration schedule |

These scripts:

- Create vectorized environments via `make_vec_env`
- Use `model.learn(total_timesteps=...)` for gradient updates
- Support TensorBoard logging
- Save trained models (`.zip`) for later inference

### 3. SLM Training (Jira only)

When `algorithm=SLM` and the environment is a Jira env, the API uses `JiraSLMPolicy` from `policies/jira_slm_policy.py`:

- **Inference:** Remote model endpoint; set `JIRA_MODEL_ENDPOINT` (or `MODEL_ENDPOINT_URL`) to your inference service URL. No local model is loaded.
- **Flow:** Observation → prompt → HTTP POST to endpoint → parse tool from response → map to discrete action
- **Fallback:** If the endpoint is not set or the request fails, uses a rule-based policy (correct next tool)

### 4. Jira Mock Data (No Live Jira Instance)

Jira environments use **mock data** for training and agent actions when no live Jira API is available:

- **Source:** `apps/workflow_definitions/jira_mock_data.json` (issues, valid_transitions, reward_config)
- **On reset:** Each episode samples a random issue from mock data; `valid_transitions` drive the simulated workflow
- **Rewards:** `reward_config.status_reward_weights` and `per_step_base` from mock data; achieved status (Done, Blocked, Code Review, etc.) maps to reward
- **Simulation console:** Also uses mock data via `GET /jira-mock-data`

---

## Environment Interface (Gymnasium)

All RL environments implement the Gymnasium API:

```python
obs, info = env.reset(seed=42)
action = env.action_space.sample()  # or from policy
obs, reward, terminated, truncated, info = env.step(action)
```

- **Observation space:** Varies by env (e.g. Jira: step_norm, done_flag, last_tool_onehot, valid, resolved)
- **Action space:** Discrete (e.g. 0 = correct next tool, 1..n = wrong tool index for Jira)
- **Reward:** Scalar from env + optional verifier (e.g. Jira workflow verifier)

---

## Dependencies

From `requirements.txt`:

| Package | Version | Role |
|---------|---------|------|
| gymnasium | ≥0.29.0 | RL environment interface |
| stable-baselines3 | ≥2.0.0 | PPO, DQN algorithms |
| torch | ≥2.0.0 | Deep learning backend |
| (none for SLM) | — | Jira SLM uses a remote endpoint; no extra Python deps in app |
| tensorboard | ≥2.14.0 | Training metrics (standalone scripts) |

---

## Model Outputs

| Algorithm | Output Location | Format |
|-----------|-----------------|--------|
| API (any) | `models/{ppo,slm,dqn}/{env}_{job_id}_metadata.json` | JSON with mean/max/min reward, job_id, episodes |
| PPO/DQN (standalone) | `models/ppo/` or `models/dqn/` | `.zip` (stable-baselines3 format) + optional checkpoints |

---

## Summary

- **Gymnasium** defines the environment interface.
- **stable-baselines3** is used for real PPO/DQN training in `training/` scripts.
- **API training** runs a custom loop; for Jira + SLM it uses `JiraSLMPolicy` (remote model endpoint or rule-based fallback), otherwise random actions.
- **PyTorch** powers stable-baselines3; the Jira SLM path uses only the configured HTTP endpoint.
