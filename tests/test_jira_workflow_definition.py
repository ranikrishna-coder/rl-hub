"""
Validate Jira workflow definition in apps folder.
Ensures apps/workflow_definitions/jira_workflows.json exists and matches
the workflow definition expected by RL-Env-Studio (Scenarios.tsx, Verifiers.tsx).
"""

import json
import os
import pytest

# Path relative to repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_DEF_PATH = os.path.join(REPO_ROOT, "apps", "workflow_definitions", "jira_workflows.json")

# Expected workflows from apps/RL-Env-Studio (Scenarios.tsx)
EXPECTED_WORKFLOWS = {
    "issue_resolution": [
        "get_issue_summary_and_description",
        "get_transitions",
        "transition_issue",
    ],
    "status_update": ["get_transitions", "transition_issue"],
    "comment_management": ["add_comment", "get_comments"],
}


def test_jira_workflow_definition_file_exists():
    """Workflow definition file must exist in apps folder."""
    assert os.path.exists(WORKFLOW_DEF_PATH), (
        f"Missing {WORKFLOW_DEF_PATH}. Jira flow must follow workflow definition in apps folder."
    )


def test_jira_workflow_definition_valid_json():
    """Workflow definition must be valid JSON."""
    with open(WORKFLOW_DEF_PATH, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Workflow definition must be a JSON object"


def test_jira_workflow_definition_has_workflows_key():
    """Workflow definition must contain 'workflows' array."""
    with open(WORKFLOW_DEF_PATH, "r") as f:
        data = json.load(f)
    assert "workflows" in data, "Workflow definition must have 'workflows' key"
    assert isinstance(data["workflows"], list), "'workflows' must be an array"


def test_jira_workflow_definition_workflow_ids():
    """Each workflow must have id matching expected set."""
    with open(WORKFLOW_DEF_PATH, "r") as f:
        data = json.load(f)
    ids = {w.get("id") for w in data["workflows"]}
    assert ids >= set(EXPECTED_WORKFLOWS.keys()), (
        f"Workflows must include {set(EXPECTED_WORKFLOWS.keys())}. Found: {ids}"
    )


def test_jira_workflow_definition_tool_orders():
    """Each workflow's expected_tool_order must match apps Scenarios.tsx."""
    with open(WORKFLOW_DEF_PATH, "r") as f:
        data = json.load(f)
    for w in data["workflows"]:
        wid = w.get("id")
        if wid not in EXPECTED_WORKFLOWS:
            continue
        expected_order = EXPECTED_WORKFLOWS[wid]
        actual = w.get("expected_tool_order") or w.get("tools") or []
        assert actual == expected_order, (
            f"Workflow {wid}: expected tool order {expected_order}, got {actual}"
        )


def test_jira_workflow_definition_tools_section():
    """Definition should define tools used in workflows (optional but recommended)."""
    with open(WORKFLOW_DEF_PATH, "r") as f:
        data = json.load(f)
    all_tools = set()
    for order in EXPECTED_WORKFLOWS.values():
        all_tools.update(order)
    if "tools" in data:
        assert set(data["tools"]) >= all_tools, (
            f"'tools' must include all workflow tools: {all_tools}"
        )
