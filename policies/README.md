# Policies

## Jira policy (model endpoint)

The Jira policy selects the next workflow tool using a **remote model endpoint**. No local model is loaded; deployment stays application-only (API + UI).

### Configuration

- Set **`JIRA_MODEL_ENDPOINT`** (or **`MODEL_ENDPOINT_URL`**) to your inference service URL (e.g. `https://your-inference.example.com/predict`).
- If the endpoint is not set or a request fails, the policy uses a **rule-based fallback** (correct next tool) so training still runs.

### Endpoint contract

- **Request (POST JSON):** `{"prompt": str, "expected_tool_order": list, "step_index": int}`
- **Response:** one of:
  - `{"tool": "ToolName"}` — predicted next tool
  - `{"raw_output": "..."}` — raw text; policy will parse a tool name from it
  - `{"action": 0}` — action index (0 = first tool, etc.)

### Usage

1. **Training:** In the catalog, select a Jira environment (e.g. Jira Issue Resolution), choose algorithm **SLM**, then Start Training. The loop uses `JiraSLMPolicy`: it calls the endpoint when configured, otherwise uses the rule-based fallback.
2. **Mapping:** The policy turns the Jira observation (step, last tool, state) into a prompt, gets the next tool from the endpoint, then maps it to the env action (0 = correct next tool, 1..n = wrong tool index).

### Explainability

- **Training context:** `get_training_context()` describes the observation space, prompt format, and action mapping. Stored on the job and shown in the Monitor Training UI under “SLM Explainability”.
- **Per-step:** `predict(obs, return_explanation=True)` returns in `info`: `prompt`, `raw_output`, `parsed_tool`, `correct_next`, `action`, and an `explanation` string.

### Code

- **`policies/jira_slm_policy.py`:** `JiraSLMPolicy(expected_tool_order, endpoint_url=None)`, `predict(obs, return_explanation=False) -> (action, info)`, `get_training_context() -> dict`. Endpoint URL defaults to `JIRA_MODEL_ENDPOINT` or `MODEL_ENDPOINT_URL`.
