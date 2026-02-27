# Policies

## Jira SLM Policy

**Recommended SLM for Jira:** [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) (Hugging Face).

- **Why appropriate for Jira:** Small (~0.5B parameters), good at instruction following and short, structured output (tool names). Fits Jira workflows: discrete tool sequence, no long-form generation.
- **Alternatives:** TinyLlama-1.1B, Phi-2, or other small instruct models if you need different size/speed.

### Usage

1. **Training:** In the catalog, select a Jira environment (Jira Issue Resolution, Status Update, or Comment Management), choose algorithm **SLM**, then Start Training. The training loop will use `JiraSLMPolicy` to select actions (or fall back to rule-based if `transformers` is not installed).

2. **Dependencies (in requirements.txt):** `transformers` and `accelerate` are required for SLM. Without them, the policy falls back to rule-based (always picks correct next tool). If policy creation fails entirely, training uses random actions (low reward ~0.2).
   ```bash
   pip install transformers accelerate
   ```
   Without these, the policy uses a rule-based fallback (correct next tool).

3. **Mapping to the environment:** The policy converts the Jira env observation (step index, last tool, workflow state) into a short prompt, runs the SLM to predict the next tool name, then maps that to the env’s discrete action (0 = correct next tool, 1..n = wrong tool index).

### Explainability

- **What the model is training on:** The policy’s `get_training_context()` returns a description of the observation space, prompt format, and action mapping. This is stored in the training job and shown in the **Monitor Training** UI under “SLM Explainability”.
- **Per-step explainability:** Call `predict(obs, return_explanation=True)` to get in `info`: `prompt`, `raw_output`, `parsed_tool`, `correct_next`, `action`, and a short `explanation` string. Training stores a sample in the job; the monitor shows “Example step” with the prompt sent to the model, the model output, and the explanation.

### Code

- `policies/jira_slm_policy.py`: `JiraSLMPolicy(expected_tool_order, model_id=..., use_slm=True)`, `predict(obs, return_explanation=False) -> (action, info)`, and `get_training_context() -> dict`.
