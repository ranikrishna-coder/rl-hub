# RL Hub — Training Framework Documentation

This document describes the frameworks, libraries, and pipelines used for reinforcement learning training in RL Hub.

---

## Overview

| Component | Framework | Purpose |
|-----------|-----------|---------|
| **RL environments** | [Gymnasium](https://gymnasium.farama.org/) (≥0.29) | Standard `reset`, `step`, `observation_space`, `action_space` interface |
| **PPO / DQN (standalone)** | [stable-baselines3](https://stable-baselines3.readthedocs.io/) (≥2.0) | Gradient-based policy optimization |
| **SLM (Jira)** | [Hugging Face Transformers](https://huggingface.co/docs/transformers/) + [Accelerate](https://huggingface.co/docs/accelerate/) | Small language model inference for tool selection |
| **API training loop** | Custom Python | Episode-based rollouts; action source varies by algorithm |
| **Deep learning backend** | [PyTorch](https://pytorch.org/) (≥2.0) | Used by stable-baselines3 and Transformers |

---

## Training Paths

### 1. API Training (`POST /train/{environment_name}`)

Triggered via the web catalog, RL-Env-Studio, or REST API. Uses a **custom episode loop** in `api/main.py` (`run_training`).

- **Episodes:** Configurable (e.g. 100 default, 320 for Jira envs)
- **Max steps per episode:** Configurable (e.g. 1000 default, 50 for Jira)
- **Action source:**
  - **SLM:** `JiraSLMPolicy` — Small language model (Qwen2.5-0.5B-Instruct) predicts the next tool. Used for Jira environments (JiraIssueResolution, JiraStatusUpdate, JiraCommentManagement).
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

- **Model:** Qwen/Qwen2.5-0.5B-Instruct (default)
- **Flow:** Observation → prompt → model.generate() → parse tool name → map to discrete action
- **Libraries:** `transformers`, `accelerate`, `torch`
- **Fallback:** If the model fails to load, uses a rule-based policy (always selects the correct next tool)

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
| transformers | ≥4.36.0 | SLM (Jira policy) |
| accelerate | ≥0.25.0 | Model loading/device handling for SLM |
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
- **API training** runs a custom loop; for Jira + SLM it uses `JiraSLMPolicy` (Transformers), otherwise random actions.
- **PyTorch** powers both stable-baselines3 and the SLM policy.
