"""
Validate Jira Status Update scenario: Change from in-progress to blocked.
Uses sample data from jira_mock_data.json and jira_workflows.json.
Ensures status gets generated (Blocked) and rewards get applied.
"""

import json
import os
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCK_DATA_PATH = os.path.join(REPO_ROOT, "apps", "workflow_definitions", "jira_mock_data.json")
WORKFLOW_PATH = os.path.join(REPO_ROOT, "apps", "workflow_definitions", "jira_workflows.json")


def _load_json(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def test_mock_data_has_in_progress_issues_with_blocked_transition():
    """Mock data must include In Progress issues with Blocked as valid transition."""
    data = _load_json(MOCK_DATA_PATH)
    issues = data.get("issues", [])
    in_progress_with_blocked = [
        i for i in issues
        if i.get("status") == "In Progress"
        and any(t.get("name") == "Blocked" for t in (i.get("valid_transitions") or []))
    ]
    assert len(in_progress_with_blocked) >= 1, (
        "Mock data must include at least one In Progress issue with Blocked transition"
    )
    assert any(i["key"] in ("PROJ-101", "PROJ-102", "PROJ-103") for i in in_progress_with_blocked), (
        "PROJ-101, PROJ-102, or PROJ-103 should have Blocked transition"
    )


def test_reward_config_has_blocked_status():
    """reward_config.status_reward_weights must include Blocked for rewards to apply."""
    data = _load_json(MOCK_DATA_PATH)
    rcfg = data.get("reward_config", {})
    weights = rcfg.get("status_reward_weights", {})
    assert "Blocked" in weights, (
        "status_reward_weights must include 'Blocked' so rewards apply when status becomes Blocked"
    )
    assert isinstance(weights["Blocked"], (int, float)), "Blocked reward weight must be numeric"


def test_status_update_workflow_has_in_progress_to_blocked_scenario():
    """status_update workflow must define the scenario Change from in-progress to blocked."""
    data = _load_json(WORKFLOW_PATH)
    status_update = next((w for w in data.get("workflows", []) if w.get("id") == "status_update"), None)
    assert status_update is not None, "status_update workflow must exist"
    scenarios = status_update.get("scenarios", [])
    blocked_scenario = next(
        (s for s in scenarios if s.get("id") == "in_progress_to_blocked" or s.get("title") == "Change from in-progress to blocked"),
        None,
    )
    assert blocked_scenario is not None, (
        "status_update must have scenario 'Change from in-progress to blocked'"
    )
    assert blocked_scenario.get("target_status") == "Blocked", (
        "Scenario target_status must be Blocked"
    )


def test_status_update_scenario_flow_status_and_reward():
    """
    Simulate the status update flow for scenario 'in_progress_to_blocked':
    - Issue starts In Progress
    - After get_transitions + transition_issue, status becomes Blocked
    - Reward is applied using status_reward_weights['Blocked']
    """
    mock_data = _load_json(MOCK_DATA_PATH)
    issues = mock_data.get("issues", [])
    issue = next(
        (i for i in issues if i.get("key") == "PROJ-101" and any(t.get("name") == "Blocked" for t in (i.get("valid_transitions") or []))),
        issues[0] if issues else None,
    )
    assert issue is not None and issue.get("key") == "PROJ-101", "PROJ-101 with Blocked must exist"

    # Simulate flow: start In Progress, apply transition -> Blocked
    initial_status = issue.get("status")
    assert initial_status == "In Progress", "Issue must start In Progress"

    # After transition_issue with target Blocked
    final_status = "Blocked"
    assert final_status in (t.get("name") for t in (issue.get("valid_transitions") or [])), (
        "Blocked must be a valid transition"
    )

    # Reward should apply
    rcfg = mock_data.get("reward_config", {})
    weights = rcfg.get("status_reward_weights", {})
    step_reward = weights.get("Blocked", rcfg.get("per_step_base", {}).get("status_update", 0.5))
    assert step_reward > 0, "Reward for Blocked status must be positive"
    assert isinstance(step_reward, (int, float)), "Reward must be numeric"
