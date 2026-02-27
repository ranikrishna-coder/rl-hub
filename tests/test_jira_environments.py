"""
Test Jira RL environments: reset, step, rewards, and workflow adherence.
Validates that Jira envs follow apps/workflow_definitions/jira_workflows.json.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environments.jira import (
    JiraWorkflowEnv,
    JiraIssueResolutionEnv,
    JiraStatusUpdateEnv,
    JiraCommentManagementEnv,
    JiraSubtaskManagementEnv,
)


@pytest.fixture
def issue_resolution_env():
    return JiraIssueResolutionEnv(seed=42)


@pytest.fixture
def status_update_env():
    return JiraStatusUpdateEnv(seed=42)


@pytest.fixture
def comment_management_env():
    return JiraCommentManagementEnv(seed=42)


@pytest.fixture
def subtask_management_env():
    return JiraSubtaskManagementEnv(seed=42)


def test_jira_issue_resolution_reset(issue_resolution_env):
    obs, info = issue_resolution_env.reset(seed=123)
    assert obs is not None
    assert obs.shape == issue_resolution_env.observation_space.shape
    assert "time_step" in info
    assert "kpis" in info


def test_jira_issue_resolution_correct_actions_give_positive_reward(issue_resolution_env):
    """Taking correct workflow steps (action 0) should yield positive efficiency reward."""
    issue_resolution_env.reset(seed=456)
    total_reward = 0.0
    for _ in range(3):  # 3 steps for issue_resolution
        obs, reward, terminated, truncated, info = issue_resolution_env.step(0)
        total_reward += reward
        assert "reward_components" in info
        assert info["reward_components"].get("efficiency", 0) >= 0
        if terminated:
            break
    assert total_reward > 0, "Correct sequence should yield positive total reward"


def test_jira_issue_resolution_wrong_action_gives_penalty(issue_resolution_env):
    """Invalid step (e.g. action 1) should yield compliance penalty."""
    issue_resolution_env.reset(seed=789)
    obs, reward, terminated, truncated, info = issue_resolution_env.step(1)
    assert "reward_components" in info
    assert info["reward_components"].get("compliance_penalty", 0) > 0 or reward < 0


def test_jira_issue_resolution_workflow_order_enforced(issue_resolution_env):
    """Environment should enforce get_issue -> get_transitions -> transition_issue."""
    issue_resolution_env.reset(seed=101)
    transition_info_history = []
    for _ in range(4):
        obs, reward, term, trunc, info = issue_resolution_env.step(0)
        transition_info_history.append(info.get("transition_info", {}))
        if term or trunc:
            break
    tool_sequence = []
    for ti in transition_info_history:
        if ti.get("valid_step") and ti.get("tool_used"):
            tool_sequence.append(ti["tool_used"])
    expected = ["get_issue_summary_and_description", "get_transitions", "transition_issue"]
    assert tool_sequence == expected, f"Expected {expected}, got {tool_sequence}"


def test_jira_status_update_env_reset_and_step(status_update_env):
    status_update_env.reset(seed=1)
    obs, reward, term, trunc, info = status_update_env.step(0)
    assert obs is not None
    assert status_update_env._workflow_id == "status_update"
    assert status_update_env._expected_order == ["get_transitions", "transition_issue"]


def test_jira_comment_management_env_reset_and_step(comment_management_env):
    comment_management_env.reset(seed=2)
    obs, reward, term, trunc, info = comment_management_env.step(0)
    assert obs is not None
    assert comment_management_env._workflow_id == "comment_management"
    assert comment_management_env._expected_order == ["add_comment", "get_comments"]


def test_jira_subtask_management_env_reset_and_step(subtask_management_env):
    """Subtask management env should use subtask_management workflow and two-step sequence."""
    subtask_management_env.reset(seed=3)
    obs, reward, term, trunc, info = subtask_management_env.step(0)
    assert obs is not None
    assert subtask_management_env._workflow_id == "subtask_management"
    assert subtask_management_env._expected_order == ["get_issue_summary_and_description", "create_subtask"]


def test_jira_subtask_management_env_cycles_across_issues(subtask_management_env):
    """JiraSubtaskManagementEnv should cycle across all mock issues via episode_index."""
    seen_keys = set()
    for episode in range(10):
        obs, info = subtask_management_env.reset(seed=episode, options={"episode_index": episode})
        # After reset, one step will populate transition_info with current_issue_key
        obs2, reward, term, trunc, info2 = subtask_management_env.step(0)
        ti = info2.get("transition_info") or {}
        key = ti.get("current_issue_key")
        if key:
            seen_keys.add(key)
    # At least 3 distinct issues should be seen in first 10 episodes
    assert len(seen_keys) >= 3, f"Expected to see multiple Jira issues, saw: {seen_keys}"


def test_jira_workflow_env_gymnasium_interface(issue_resolution_env):
    """Jira env must follow Gymnasium reset/step interface."""
    obs, info = issue_resolution_env.reset()
    assert issue_resolution_env.observation_space.contains(obs)
    action = issue_resolution_env.action_space.sample()
    obs2, reward, term, trunc, info2 = issue_resolution_env.step(action)
    assert isinstance(reward, (int, float))
    assert isinstance(term, bool)
    assert isinstance(trunc, bool)


def test_jira_workflow_env_loads_definition_from_apps():
    """Jira env should load workflow definition from apps/workflow_definitions."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "apps", "workflow_definitions", "jira_workflows.json")
    env = JiraIssueResolutionEnv()
    assert env._workflow_id == "issue_resolution"
    assert len(env._expected_order) == 3
    if os.path.exists(path):
        assert "issue_resolution" in [w.get("id") for w in env._defn.get("workflows", [])]
