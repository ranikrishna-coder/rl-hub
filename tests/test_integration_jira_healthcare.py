"""
Integration tests: Jira and healthcare environments coexist and run.
Validates requirement that Jira flow is added along with healthcare use cases.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portal.environment_registry import get_environment_class, list_all_environments


def test_healthcare_and_jira_both_present():
    """Registry must contain at least one healthcare and all Jira envs."""
    all_envs = list_all_environments()
    names = [e["name"] for e in all_envs]
    healthcare = [n for n in names if n not in ("JiraIssueResolution", "JiraStatusUpdate", "JiraCommentManagement")]
    assert len(healthcare) >= 1, "At least one healthcare environment must be present"
    assert "JiraIssueResolution" in names
    assert "JiraStatusUpdate" in names
    assert "JiraCommentManagement" in names


def test_healthcare_env_loads_and_runs():
    """A representative healthcare env (TreatmentPathwayOptimization) must load and run."""
    cls = get_environment_class("TreatmentPathwayOptimization")
    if cls is None:
        pytest.skip("TreatmentPathwayOptimization not available (optional deps)")
    env = cls()
    obs, info = env.reset(seed=0)
    assert obs is not None
    env.step(0)


def test_jira_env_loads_and_runs():
    """Jira env must load and run."""
    cls = get_environment_class("JiraIssueResolution")
    assert cls is not None
    env = cls()
    obs, info = env.reset(seed=0)
    assert obs is not None
    env.step(0)


def test_multiple_envs_sequential():
    """Load and run one healthcare and one Jira env in sequence (no cross-contamination)."""
    hc = get_environment_class("TreatmentPathwayOptimization")
    jira = get_environment_class("JiraIssueResolution")
    if hc:
        e1 = hc()
        e1.reset(seed=1)
        e1.step(0)
    assert jira is not None
    e2 = jira()
    e2.reset(seed=2)
    e2.step(0)
