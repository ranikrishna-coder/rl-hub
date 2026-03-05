"""
Jira Workflow Verifier
Aligns with apps/RL-Env-Studio Verifiers.tsx (Jira Issue Resolution, Jira Comment Management).
Scores trajectories by tool sequence and argument validity per workflow definition.
"""

import json
import os
from typing import Dict, Any, Optional, Tuple
import numpy as np

from .base_verifier import BaseVerifier, VerifierConfig


def _load_jira_workflow_definition() -> Dict[str, Any]:
    """Load workflow definition from apps/workflow_definitions/jira_workflows.json."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "apps", "workflow_definitions", "jira_workflows.json")
    if not os.path.exists(path):
        return {"workflows": []}
    with open(path, "r") as f:
        return json.load(f)


class JiraWorkflowVerifier(BaseVerifier):
    """
    Verifier for Jira workflows. Matches app Verifiers.tsx logic:
    - Jira Issue Resolution: expected_order get_issue_summary_and_description → get_transitions → transition_issue
    - Jira Status Update: get_transitions → transition_issue
    - Jira Comment Management: add_comment → get_comments
    """

    def __init__(self, config: Optional[VerifierConfig] = None):
        super().__init__(config)
        self._workflow_id = (self.metadata or {}).get("workflow_id", "issue_resolution")
        self._defn = _load_jira_workflow_definition()
        workflows = self._defn.get("workflows", [])
        self._workflow = next(
            (w for w in workflows if w.get("id") == self._workflow_id),
            workflows[0] if workflows else {},
        )
        self._expected_order = self._workflow.get("expected_tool_order", [])
        # Scoring weights from apps/workflow_definitions/jira_workflows.json (aligned with Verifiers.tsx)
        scoring = self._workflow.get("scoring", {})
        self._usage_weight = float(scoring.get("tool_usage_weight", 0.2))
        self._sequence_weight = float(scoring.get("sequence_weight", 0.4))
        # valid_transition_weight (issue_resolution, status_update) or content_valid_weight (comment_management)
        self._valid_arg_weight = float(
            scoring.get("valid_transition_weight") or scoring.get("content_valid_weight", 0.4)
        )

    def evaluate(
        self,
        state: np.ndarray,
        action: Any,
        next_state: np.ndarray,
        info: Optional[Dict[str, Any]] = None,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Score step from transition_info (set by Jira env). Maps to efficiency + compliance_penalty.
        """
        info = info or {}
        transition_info = info.get("transition_info") or info
        valid_step = transition_info.get("valid_step", False)
        tool_sequence = transition_info.get("tool_sequence_after") or []
        tool_used = transition_info.get("tool_used")

        # Sequence check: prefix of tool_sequence should match expected_order
        sequence_ok = True
        for i, expected in enumerate(self._expected_order):
            if i >= len(tool_sequence):
                sequence_ok = False
                break
            if tool_sequence[i] != expected:
                sequence_ok = False
                break

        # Valid transition / content (for transition_issue or add_comment)
        valid_arg = valid_step  # env already encodes valid transition use

        if valid_step and sequence_ok:
            efficiency = (
                self._usage_weight
                + self._sequence_weight * (1.0 if sequence_ok else 0.0)
                + self._valid_arg_weight * (1.0 if valid_arg else 0.0)
            )
            compliance_penalty = 0.0
        else:
            efficiency = 0.0
            compliance_penalty = 1.0

        breakdown = {
            "efficiency": efficiency,
            "compliance_penalty": compliance_penalty,
            "clinical": 0.0,
            "financial": 0.0,
            "patient_satisfaction": 0.0,
            "risk_penalty": 0.0,
        }
        total = efficiency - compliance_penalty
        self._log_evaluation(state, action, next_state, total, breakdown, info)
        return total, breakdown
