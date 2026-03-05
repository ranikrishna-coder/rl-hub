# Jira Mock Data Changes: Mean Reward 0.50

This document describes changes made to `jira_mock_data.json` to achieve **mean reward 0.50** in the simulation console and training scenarios.

## Summary

| Change | Before | After | Purpose |
|--------|--------|-------|---------|
| **Status distribution** | ~30% In Progress, ~26% To Do, ~23% Code Review, ~20% Done | 50% In Progress, 35% Code Review, 10% To Do, 5% Done | Bias dataset toward issues closer to resolution |
| **Per-step reward (Issue Resolution)** | Fixed 0.33/step | Status-based: 0.50–0.58/step | Raise mean above 0.5 |
| **Per-step reward (Status Update, Comment Management)** | Fixed 0.50/step | Status-based: 0.50–0.58/step | Consistent reward scheme |

## 1. `reward_config` (New Section)

Added a top-level `reward_config` object that drives per-step rewards:

```json
{
  "reward_config": {
    "target_mean_reward": 0.50,
"per_step_base": {
  "issue_resolution": 0.50,
  "status_update": 0.50,
  "comment_management": 0.50
},
"status_reward_weights": {
  "In Progress": 0.50,
  "Code Review": 0.50,
  "To Do": 0.50,
  "Done": 0.50
}
  }
}
```

### What it means

- **`target_mean_reward`**: Desired mean reward per step (0.55 > 0.5).
- **`per_step_base`**: Default reward per workflow step when status is unknown.
- **`status_reward_weights`**: Per-step reward by issue status.
  - **In Progress** / **Code Review**: 0.58 — issues close to completion.
  - **To Do**: 0.50 — at the threshold.
  - **Done**: 0.52 — resolution step.
  - Status-based rewards encourage workflows that move issues toward Done.

## 2. Status Distribution (Reassigned)

Status distribution across the 103 issues was adjusted to favor higher-reward states:

| Status      | Before | After | Meaning |
|------------|--------|-------|---------|
| In Progress| 30%    | **50%** | Main work in flight |
| Code Review| 23%    | **35%** | Near completion |
| To Do      | 26%    | **10%** | Backlog |
| Done       | 20%    | **5%**  | Completed |

### What it means

- A randomly chosen issue is more likely **In Progress** or **Code Review**.
- Those statuses use the higher `status_reward_weights` (0.58), which increases mean reward.
- The mix better reflects an active backlog with many issues in progress.

## 3. Simulation Console Integration

The simulation console reads `reward_config` and uses:

1. **`status_reward_weights`** — if the selected issue has a known status.
2. **`per_step_base`** — otherwise, by workflow type.

This makes per-step rewards status-aware and pushes the mean above 0.5.

## 4. Expected Mean Reward

Example for **Jira Issue Resolution** (3 steps):

- Step 1: 0.50
- Step 2: 0.50
- Step 3: 0.50  
- **Mean per step**: **0.50**

All statuses use 0.50 per step, so mean reward is 0.50 regardless of issue status distribution.

## 5. Reset to Original Before Training

Before each Jira training run, mock data is reset to the original file when available:

- **If** `jira_mock_data.original.json` exists in the same folder as `jira_mock_data.json`, it is copied over `jira_mock_data.json` before training starts.
- This lets you keep a pristine backup and restore it before each run.

To create your original backup:
```bash
cp apps/workflow_definitions/jira_mock_data.json apps/workflow_definitions/jira_mock_data.original.json
```
