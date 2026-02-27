"""
Jira Workflow RL Environment
Follows workflow definition in apps/workflow_definitions/jira_workflows.json.
System: Jira (Atlassian). Workflows: Issue Resolution, Status Update, Comment Management.
"""

import json
import os
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional, Tuple

import sys
_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _parent not in sys.path:
    sys.path.insert(0, _parent)

from environments.base_environment import (
    HealthcareRLEnvironment,
    RewardComponent,
    KPIMetrics,
)

try:
    from verifiers.base_verifier import BaseVerifier
except ImportError:
    BaseVerifier = None


def _load_mock_data() -> Dict[str, Any]:
    """Load Jira mock data from apps/workflow_definitions/jira_mock_data.json. Used for training without a live Jira instance."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "apps", "workflow_definitions", "jira_mock_data.json")
    if not os.path.exists(path):
        return {"issues": [], "comment_threads": {}, "reward_config": {}}
    with open(path, "r") as f:
        return json.load(f)


def _load_workflow_definition() -> Dict[str, Any]:
    """Load Jira workflow definition from apps folder. Keeps config intact."""
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "apps", "workflow_definitions", "jira_workflows.json")
    if not os.path.exists(path):
        # Fallback: inline default matching apps/workflow_definitions/jira_workflows.json
        return {
            "workflows": [
                {
                    "id": "issue_resolution",
                    "expected_tool_order": [
                        "get_issue_summary_and_description",
                        "get_transitions",
                        "transition_issue",
                    ],
                    "min_required_calls": 3,
                },
                {
                    "id": "status_update",
                    "expected_tool_order": ["get_transitions", "transition_issue"],
                    "min_required_calls": 2,
                },
                {
                    "id": "comment_management",
                    "expected_tool_order": ["add_comment", "get_comments"],
                    "min_required_calls": 2,
                },
                {
                    "id": "subtask_management",
                    "expected_tool_order": ["get_issue_summary_and_description", "create_subtask"],
                    "min_required_calls": 2,
                },
            ]
        }
    with open(path, "r") as f:
        return json.load(f)


class JiraWorkflowEnv(HealthcareRLEnvironment):
    """
    Gymnasium-compatible RL environment for Jira workflows.
    Implements Issue Resolution, Status Update, and Comment Management
    as defined in apps/workflow_definitions/jira_workflows.json.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        verifier: Optional[Any] = None,
        **kwargs
    ):
        """
        Args:
            config: Optional env config. May contain "workflow_id": "issue_resolution" | "status_update" | "comment_management".
            workflow_id: Override config to select workflow (default: issue_resolution).
            verifier: Optional Jira verifier (from app definition). When provided, reward uses verifier.evaluate().
        """
        config = config or {}
        self._workflow_id = workflow_id or config.get("workflow_id", "issue_resolution")
        self._verifier = verifier if (BaseVerifier and isinstance(verifier, BaseVerifier)) else None
        super().__init__(config=config, **kwargs)

        self._defn = _load_workflow_definition()
        workflows = self._defn.get("workflows", [])
        self._workflow = next(
            (w for w in workflows if w.get("id") == self._workflow_id), workflows[0] if workflows else {}
        )
        self._expected_order = self._workflow.get("expected_tool_order", [])
        self._min_required_calls = self._workflow.get("min_required_calls", len(self._expected_order))

        # Action space: 0 = correct next tool, 1..K = wrong tool (K = len(expected_order))
        # So action 0 always means "do the next correct step"; others are invalid for testing.
        n_tools = len(self._expected_order)
        self.action_space = spaces.Discrete(n_tools + 1)  # 0 = correct next, 1..n_tools = wrong step index

        # State: step_index (norm), last_tool_index (one-hot size n_tools), valid_transition_applied (0/1), issue_resolved (0/1)
        state_dim = 2 + n_tools + 2  # step_norm, done_flag, one-hot last tool, valid_transition, resolved
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(state_dim,), dtype=np.float32
        )

        self._step_index = 0
        self._tool_sequence: list = []
        self._valid_transition_used = False
        self._issue_resolved = False
        self._current_valid_transition_ids: list = []
        self._current_issue: Optional[Dict[str, Any]] = None
        self._achieved_status: Optional[str] = None
        self._scenario_id: Optional[str] = config.get("scenario_id")
        # Load mock data for training without live Jira (no API connection),
        # allowing an override (e.g., live Jira snapshot) to be injected via config.
        mock_override = config.get("mock_data_override")
        if isinstance(mock_override, dict) and mock_override.get("issues"):
            self._mock_data = mock_override
        else:
            self._mock_data = _load_mock_data()
        self._mock_issues = [i for i in self._mock_data.get("issues", []) if i.get("valid_transitions")]
        self._reward_config = self._mock_data.get("reward_config", {})

    def _filter_issues_by_scenario(self, issues: list) -> list:
        """Filter issues by scenario_id (e.g. in_progress_to_blocked requires Blocked transition)."""
        if not self._scenario_id or not issues:
            return issues
        if self._scenario_id == "in_progress_to_blocked":
            return [i for i in issues if any(t.get("name") == "Blocked" for t in (i.get("valid_transitions") or []))]
        if self._scenario_id == "in_progress_to_done":
            return [i for i in issues if any(t.get("name") == "Done" for t in (i.get("valid_transitions") or []))]
        return issues

    def _get_issue_at_index(self, episode_index: int) -> Optional[Dict[str, Any]]:
        """Get issue at episode_index (cycle through all). Returns None if no mock data."""
        filtered = self._filter_issues_by_scenario(self._mock_issues)
        if not filtered:
            return None
        idx = episode_index % len(filtered)
        return filtered[idx]

    def reset(self, seed=None, options=None):
        """Override to pass episode_index for cycling through all issues."""
        self._reset_options = (options or {}).copy()
        return super().reset(seed=seed, options=options)

    def _sample_issue(self) -> Optional[Dict[str, Any]]:
        """Sample an issue from mock data for this episode. Returns None if no mock data."""
        if not self._mock_issues:
            return None
        filtered = self._filter_issues_by_scenario(self._mock_issues)
        if not filtered:
            filtered = self._mock_issues
        idx = int(self.np_random.integers(0, len(filtered)))
        return filtered[idx]

    def _initialize_state(self) -> np.ndarray:
        self._step_index = 0
        self._tool_sequence = []
        self._valid_transition_used = False
        self._issue_resolved = False
        self._achieved_status = None
        # Use episode_index to cycle through all issues when provided (training runs across all)
        opts = getattr(self, "_reset_options", None) or {}
        episode_index = opts.get("episode_index")
        if episode_index is not None:
            issue = self._get_issue_at_index(episode_index)
        else:
            issue = self._sample_issue()
        if issue:
            self._current_issue = issue
            transitions = issue.get("valid_transitions", [])
            self._current_valid_transition_ids = [str(t.get("id", t.get("name", ""))) for t in transitions if t]
        else:
            self._current_issue = None
            self._current_valid_transition_ids = ["31", "61"]  # fallback when no mock data
        return self._get_state_features()

    def _get_state_features(self) -> np.ndarray:
        n = len(self._expected_order)
        step_norm = self._step_index / max(n, 1)
        done_flag = 1.0 if self._step_index >= self._min_required_calls else 0.0
        last_tool_onehot = np.zeros(n, dtype=np.float32)
        if self._tool_sequence:
            last_tool = self._tool_sequence[-1]
            for i, t in enumerate(self._expected_order):
                if t == last_tool:
                    last_tool_onehot[i] = 1.0
                    break
        valid = 1.0 if self._valid_transition_used else 0.0
        resolved = 1.0 if self._issue_resolved else 0.0
        return np.array(
            [step_norm, done_flag, *last_tool_onehot, valid, resolved],
            dtype=np.float32,
        )

    def _apply_action(self, action: Any) -> Dict[str, Any]:
        n = len(self._expected_order)
        action = int(action)
        correct_next = self._step_index < n
        transition_info: Dict[str, Any] = {
            "action": action,
            "step_index": self._step_index,
            "correct_next_step": self._expected_order[self._step_index] if correct_next else None,
            "tool_sequence_before": list(self._tool_sequence),
        }

        if action == 0 and correct_next:
            # Correct next step in workflow
            tool = self._expected_order[self._step_index]
            self._tool_sequence.append(tool)
            self._step_index += 1
            if tool == "transition_issue":
                self._valid_transition_used = True
                self._issue_resolved = True
            elif tool == "create_subtask":
                self._issue_resolved = True
            transition_info["tool_used"] = tool
            transition_info["valid_step"] = True
            if self._achieved_status:
                transition_info["achieved_status"] = self._achieved_status
        else:
            # Invalid: wrong order or wrong action
            if action > 0 and action <= n:
                wrong_tool = self._expected_order[action - 1]
                self._tool_sequence.append(wrong_tool)
            transition_info["tool_used"] = None
            transition_info["valid_step"] = False

        transition_info["tool_sequence_after"] = list(self._tool_sequence)
        transition_info["workflow_id"] = self._workflow_id
        if self._current_issue:
            transition_info["current_issue_key"] = self._current_issue.get("key")
            transition_info["valid_transition_ids"] = self._current_valid_transition_ids
        return transition_info

    def _calculate_reward_components(
        self, state: np.ndarray, action: Any, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        comp = {
            RewardComponent.CLINICAL: 0.0,
            RewardComponent.FINANCIAL: 0.0,
            RewardComponent.PATIENT_SATISFACTION: 0.0,
            RewardComponent.RISK_PENALTY: 0.0,
        }
        if self._verifier is not None:
            # Use Jira verifier from app definition (Verifiers.tsx / workflow_definitions)
            transition_info = info.get("transition_info") or info
            reward, breakdown = self._verifier.evaluate(
                state, action, self._get_state_features(), info={"transition_info": transition_info}
            )
            comp[RewardComponent.EFFICIENCY] = breakdown.get("efficiency", 0.0)
            comp[RewardComponent.COMPLIANCE_PENALTY] = breakdown.get("compliance_penalty", 0.0)
        else:
            if info.get("valid_step"):
                # Use mock data reward_config when available (training without live Jira)
                rcfg = self._reward_config
                status_weights = rcfg.get("status_reward_weights", {})
                per_step = rcfg.get("per_step_base", {}).get(self._workflow_id, 0.5)
                ti = info.get("transition_info") or info
                achieved = ti.get("achieved_status") or self._achieved_status
                comp[RewardComponent.EFFICIENCY] = float(
                    status_weights.get(achieved, per_step) if status_weights and achieved
                    else per_step
                )
                comp[RewardComponent.COMPLIANCE_PENALTY] = 0.0
            else:
                comp[RewardComponent.EFFICIENCY] = 0.0
                comp[RewardComponent.COMPLIANCE_PENALTY] = 1.0
        return comp

    def _is_done(self) -> bool:
        return self._step_index >= self._min_required_calls

    def _get_kpis(self) -> KPIMetrics:
        n = len(self._expected_order)
        steps_done = min(self._step_index, n)
        return KPIMetrics(
            clinical_outcomes={},
            operational_efficiency={
                "workflow_step": self._step_index,
                "expected_steps": n,
                "steps_completed": steps_done,
            },
            financial_metrics={},
            patient_satisfaction=0.0,
            risk_score=0.0,
            compliance_score=1.0 if self._step_index >= self._min_required_calls else 0.5,
            timestamp=float(self.time_step),
        )


class JiraIssueResolutionEnv(JiraWorkflowEnv):
    """Jira Issue Resolution Flow: get_issue_summary_and_description → get_transitions → transition_issue."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="issue_resolution", **kwargs)


class JiraStatusUpdateEnv(JiraWorkflowEnv):
    """Jira Status Update Workflow: get_transitions → transition_issue."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="status_update", **kwargs)


class JiraCommentManagementEnv(JiraWorkflowEnv):
    """Jira Comment Thread Management: add_comment → get_comments."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="comment_management", **kwargs)


class JiraSubtaskManagementEnv(JiraWorkflowEnv):
    """Jira Subtask Management: get_issue_summary_and_description → create_subtask."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config=config, workflow_id="subtask_management", **kwargs)
        # Subtask workflow: use all issues as parents (no valid_transitions filter)
        self._mock_issues = [i for i in self._mock_data.get("issues", []) if i.get("key")]
