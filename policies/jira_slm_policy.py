"""
Jira SLM Policy – Small Language Model for Jira workflow tool selection.

Recommended SLM for Jira:
- **Primary**: Qwen2.5-0.5B-Instruct (Hugging Face: Qwen/Qwen2.5-0.5B-Instruct)
  - Small (~0.5B params), good at instruction following and tool/function-style output.
  - Fits Jira workflows: short prompts, discrete tool names, no long generation.
- **Alternative**: TinyLlama-1.1B, Phi-2, or similar small instruct models if you need
  different size/speed tradeoffs.

This module maps Jira env observations to a text prompt, runs the SLM (or rule-based
fallback), and maps the model output back to the env's discrete action space.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Optional: Hugging Face transformers for real SLM inference
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    _HF_AVAILABLE = True
except ImportError:
    _HF_AVAILABLE = False

# Default model ID (small, good for tool-use style)
DEFAULT_JIRA_SLM_ID = "Qwen/Qwen2.5-0.5B-Instruct"


def _observation_to_prompt(
    obs: np.ndarray,
    expected_tool_order: List[str],
) -> Tuple[str, int]:
    """
    Convert Jira env observation to a short prompt for the SLM.
    Jira obs: [step_norm, done_flag, last_tool_onehot..., valid, resolved]
    Returns (prompt_string, step_index).
    """
    n = len(expected_tool_order)
    step_norm = float(obs[0]) if obs.size > 0 else 0.0
    step_index = min(int(round(step_norm * n)), n - 1) if n else 0
    step_index = max(0, step_index)

    # Last tool from one-hot (indices 2 : 2+n)
    last_tool = "none"
    if obs.size >= 2 + n:
        onehot = obs[2 : 2 + n]
        for i in range(n):
            if onehot[i] > 0.5:
                last_tool = expected_tool_order[i]
                break

    tools_str = ", ".join(expected_tool_order)
    correct_next = expected_tool_order[step_index] if step_index < n else "done"

    prompt = (
        f"Jira workflow. Tools in order: {tools_str}. "
        f"Current step {step_index + 1}/{n}. Last tool used: {last_tool}. "
        f"Reply with only the next tool name, one word: "
    )
    return prompt, step_index


def _parse_tool_from_output(text: str, expected_tool_order: List[str]) -> Optional[str]:
    """Extract a tool name from model output (first word or known token)."""
    if not text or not expected_tool_order:
        return None
    text = text.strip().lower()
    # First word often is the tool name
    first = (text.split() or [""])[0]
    for tool in expected_tool_order:
        if tool.lower() == first or tool.lower() in text:
            return tool
    # Snip to first word and try match
    for tool in expected_tool_order:
        if first == tool.lower():
            return tool
    return None


class JiraSLMPolicy:
    """
    Policy that uses a Small Language Model (or rule-based fallback) to choose
    the next Jira workflow tool. Maps env observation -> prompt -> SLM -> action.
    """

    def __init__(
        self,
        expected_tool_order: List[str],
        *,
        model_id: Optional[str] = None,
        use_slm: bool = True,
        device: Optional[str] = None,
    ):
        """
        Args:
            expected_tool_order: List of tool names in correct order (e.g. from workflow).
            model_id: Hugging Face model id (default: Qwen2.5-0.5B-Instruct).
            use_slm: If True and transformers available, use SLM; else rule-based.
            device: Device for model ("cuda", "cpu", or None for auto).
        """
        self._expected_tool_order = list(expected_tool_order)
        self._n = len(self._expected_tool_order)
        self._model_id = model_id or DEFAULT_JIRA_SLM_ID
        self._use_slm = use_slm and _HF_AVAILABLE
        self._device = device
        self._model = None
        self._tokenizer = None
        self._load_error: Optional[str] = None

    def _ensure_model_loaded(self) -> bool:
        if not self._use_slm:
            return False
        if self._model is not None:
            return True
        try:
            import warnings
            with warnings.catch_warnings(record=True):
                self._tokenizer = AutoTokenizer.from_pretrained(
                    self._model_id, trust_remote_code=True
                )
                self._model = AutoModelForCausalLM.from_pretrained(
                    self._model_id,
                    trust_remote_code=True,
                )
            if self._device is None:
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = self._model.to(self._device)
            self._model.eval()
            return True
        except Exception as e:
            self._use_slm = False
            self._load_error = str(e)
            print(
                f"Jira SLM: model load failed ({e}). Using rule-based fallback. "
                "Check: pip install transformers accelerate; network for first-time model download."
            )
            return False

    def predict(
        self,
        obs: np.ndarray,
        deterministic: bool = True,
        return_explanation: bool = False,
    ) -> Tuple[int, Optional[Dict[str, Any]]]:
        """
        Predict action from observation.
        Returns (action, info). Action 0 = correct next tool, 1..n = wrong tool index.
        If return_explanation=True, info includes prompt, raw_output, explanation for explainability.
        """
        prompt, step_index = _observation_to_prompt(obs, self._expected_tool_order)
        correct_next = (
            self._expected_tool_order[step_index]
            if step_index < self._n
            else None
        )

        raw_output: Optional[str] = None
        tool_from_model: Optional[str] = None

        if step_index >= self._n:
            action = 0
            explanation = "Episode complete; no next tool."
            info = {"step_index": step_index, "tool": correct_next}
            if return_explanation:
                info["prompt"] = prompt
                info["raw_output"] = raw_output
                info["parsed_tool"] = None
                info["correct_next"] = correct_next
                info["action"] = action
                info["explanation"] = explanation
            return action, info

        if self._ensure_model_loaded():
            try:
                inputs = self._tokenizer(
                    prompt,
                    return_tensors="pt",
                    truncation=True,
                    max_length=256,
                ).to(self._device)
                with torch.no_grad():
                    out = self._model.generate(
                        **inputs,
                        max_new_tokens=16,
                        do_sample=not deterministic,
                        pad_token_id=self._tokenizer.eos_token_id,
                    )
                raw_output = self._tokenizer.decode(
                    out[0][inputs["input_ids"].shape[1]:],
                    skip_special_tokens=True,
                ).strip()
                tool_from_model = _parse_tool_from_output(
                    raw_output,
                    self._expected_tool_order,
                )
            except Exception:
                tool_from_model = None

        if tool_from_model is None:
            action = 0
            tool_from_model = correct_next
            explanation = (
                "Rule-based fallback: no valid tool parsed from model; using correct next tool."
                if raw_output is not None
                else "Rule-based fallback (SLM not loaded): using correct next tool."
            )
        elif tool_from_model == correct_next:
            action = 0
            explanation = f"Model correctly predicted next tool: {tool_from_model}."
        else:
            try:
                wrong_idx = self._expected_tool_order.index(tool_from_model)
                action = wrong_idx + 1
            except ValueError:
                action = 1
            explanation = (
                f"Model predicted '{tool_from_model}'; correct next was '{correct_next}'. "
                f"Mapped to action {action} (wrong tool index)."
            )

        info = {
            "step_index": step_index,
            "tool": tool_from_model,
            "correct_next": correct_next,
        }
        if return_explanation:
            info["prompt"] = prompt
            info["raw_output"] = raw_output
            info["parsed_tool"] = tool_from_model
            info["action"] = action
            info["explanation"] = explanation
        return action, info

    def get_training_context(self) -> Dict[str, Any]:
        """
        Return a description of what the SLM is training on (for explainability UI).
        Describes observation space, prompt format, and action mapping.
        """
        return {
            "description": "The Jira SLM is trained on the workflow state at each step. It receives a text prompt built from the current observation and outputs the next tool name.",
            "observation_space": {
                "shape": [2 + self._n + 2],
                "features": [
                    "step_norm (0–1): current step index / total steps",
                    "done_flag (0 or 1): whether workflow is complete",
                    f"last_tool_onehot ({self._n} values): which tool was used last",
                    "valid_transition_applied (0 or 1)",
                    "issue_resolved (0 or 1)",
                ],
                "expected_tool_order": list(self._expected_tool_order),
            },
            "prompt_format": (
                "Jira workflow. Tools in order: [tool1, tool2, ...]. "
                "Current step X/N. Last tool used: <name>. Reply with only the next tool name, one word:"
            ),
            "action_space": {
                "0": "Correct next tool (rewarded)",
                "1..n": "Wrong tool (index in expected order); used for exploration/penalty",
            },
            "model_id": self._model_id,
            "uses_slm": self.uses_slm,
            "load_error": self._load_error,
        }

    @property
    def expected_tool_order(self) -> List[str]:
        return list(self._expected_tool_order)

    @property
    def uses_slm(self) -> bool:
        return self._use_slm and self._model is not None
