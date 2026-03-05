"""
Jira policy for workflow tool selection via a remote model endpoint.

No local model is loaded. The application calls a configurable inference endpoint
(e.g. JIRA_MODEL_ENDPOINT) with the current observation/prompt and receives the
predicted tool name or action. This keeps deployment lightweight (API + UI only).

- Set JIRA_MODEL_ENDPOINT (or MODEL_ENDPOINT_URL) to your inference service URL.
- If the endpoint is not set or the request fails, the policy uses a rule-based
  fallback (correct next tool) so training still runs.
"""

from __future__ import annotations

import os
import urllib.request
import urllib.error
import json
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def _observation_to_prompt(
    obs: np.ndarray,
    expected_tool_order: List[str],
) -> Tuple[str, int]:
    """
    Convert Jira env observation to a short prompt for the model.
    Returns (prompt_string, step_index).
    """
    n = len(expected_tool_order)
    step_norm = float(obs[0]) if obs.size > 0 else 0.0
    step_index = min(int(round(step_norm * n)), n - 1) if n else 0
    step_index = max(0, step_index)

    last_tool = "none"
    if obs.size >= 2 + n:
        onehot = obs[2 : 2 + n]
        for i in range(n):
            if onehot[i] > 0.5:
                last_tool = expected_tool_order[i]
                break

    tools_str = ", ".join(expected_tool_order)
    prompt = (
        f"Jira workflow. Tools in order: {tools_str}. "
        f"Current step {step_index + 1}/{n}. Last tool used: {last_tool}. "
        f"Reply with only the next tool name, one word: "
    )
    return prompt, step_index


def _parse_tool_from_output(text: str, expected_tool_order: List[str]) -> Optional[str]:
    """Extract a tool name from model output."""
    if not text or not expected_tool_order:
        return None
    text = text.strip().lower()
    first = (text.split() or [""])[0]
    for tool in expected_tool_order:
        if tool.lower() == first or tool.lower() in text:
            return tool
    for tool in expected_tool_order:
        if first == tool.lower():
            return tool
    return None


def _get_endpoint_url() -> Optional[str]:
    """Model endpoint URL from environment (no local model)."""
    url = os.environ.get("JIRA_MODEL_ENDPOINT") or os.environ.get("MODEL_ENDPOINT_URL")
    if url:
        return url.rstrip("/")
    return None


def _call_model_endpoint(
    endpoint_url: str,
    prompt: str,
    expected_tool_order: List[str],
    step_index: int,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    POST to the model endpoint. Expects JSON body and returns (tool_name, raw_output, error).
    Contract: send {"prompt": str, "expected_tool_order": list, "step_index": int};
    expect {"tool": str} or {"raw_output": str} or {"action": int}.
    """
    payload = {
        "prompt": prompt,
        "expected_tool_order": expected_tool_order,
        "step_index": step_index,
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            out = json.loads(body) if body else {}
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError) as e:
        return None, None, str(e)

    tool = out.get("tool")
    raw_output = out.get("raw_output") or (out.get("response") if isinstance(out.get("response"), str) else None)
    if tool:
        return tool, raw_output, None
    if raw_output:
        parsed = _parse_tool_from_output(raw_output, expected_tool_order)
        return parsed, raw_output, None
    action = out.get("action")
    if action is not None and 0 <= action < len(expected_tool_order):
        return expected_tool_order[action], None, None
    return None, raw_output, "Endpoint did not return 'tool' or valid 'action'"


class JiraSLMPolicy:
    """
    Policy that uses a remote model endpoint for Jira tool selection.
    No local model is loaded; all inference is via HTTP. If the endpoint is not
    configured or the request fails, uses rule-based fallback (correct next tool).
    """

    def __init__(
        self,
        expected_tool_order: List[str],
        *,
        endpoint_url: Optional[str] = None,
    ):
        """
        Args:
            expected_tool_order: List of tool names in correct order (from workflow).
            endpoint_url: Override for model endpoint URL (default: from JIRA_MODEL_ENDPOINT / MODEL_ENDPOINT_URL).
        """
        self._expected_tool_order = list(expected_tool_order)
        self._n = len(self._expected_tool_order)
        self._endpoint_url = endpoint_url or _get_endpoint_url()
        self._load_error: Optional[str] = None
        if not self._endpoint_url:
            self._load_error = "JIRA_MODEL_ENDPOINT (or MODEL_ENDPOINT_URL) not set; using rule-based fallback."

    def predict(
        self,
        obs: np.ndarray,
        deterministic: bool = True,
        return_explanation: bool = False,
    ) -> Tuple[int, Optional[Dict[str, Any]]]:
        """
        Predict action from observation. Calls model endpoint when configured;
        otherwise uses correct next tool (rule-based fallback).
        Returns (action, info). Action 0 = correct next tool, 1..n = wrong tool index.
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

        if self._endpoint_url:
            tool_from_model, raw_output, err = _call_model_endpoint(
                self._endpoint_url,
                prompt,
                self._expected_tool_order,
                step_index,
            )
            if err and not tool_from_model:
                raw_output = raw_output or f"Endpoint error: {err}"

        if tool_from_model is None:
            action = 0
            tool_from_model = correct_next
            explanation = (
                "Rule-based fallback: no valid tool from endpoint; using correct next tool."
                if self._endpoint_url
                else "Rule-based fallback (model endpoint not configured); using correct next tool."
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
        """Return description for explainability UI (no local model)."""
        return {
            "description": "The Jira policy uses a remote model endpoint for tool selection. Observation is converted to a prompt; the endpoint returns the next tool name. If the endpoint is not set, a rule-based fallback is used.",
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
            "model_endpoint_configured": bool(self._endpoint_url),
            "uses_slm": bool(self._endpoint_url),
            "load_error": self._load_error,
        }

    @property
    def expected_tool_order(self) -> List[str]:
        return list(self._expected_tool_order)

    @property
    def uses_slm(self) -> bool:
        return bool(self._endpoint_url)
