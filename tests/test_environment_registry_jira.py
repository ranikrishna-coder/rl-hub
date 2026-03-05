"""
Test that Jira environments are registered and load alongside healthcare envs.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portal.environment_registry import (
    ENVIRONMENT_REGISTRY,
    get_environment_class,
    get_environment_metadata,
    list_all_environments,
)


JIRA_ENV_NAMES = ["JiraIssueResolution", "JiraStatusUpdate", "JiraCommentManagement"]


def test_registry_contains_jira_environments():
    """Registry must contain all three Jira workflow environments."""
    for name in JIRA_ENV_NAMES:
        assert name in ENVIRONMENT_REGISTRY, f"Registry must contain {name}"


def test_jira_environments_have_correct_metadata():
    """Jira envs must have system=Jira, workflow=Jira, category=jira."""
    for name in JIRA_ENV_NAMES:
        meta = get_environment_metadata(name)
        assert meta is not None, f"Metadata for {name} must exist"
        assert meta.get("category") == "jira"
        assert "Jira" in (meta.get("system") or "")
        assert meta.get("workflow") == "Jira"


def test_jira_environment_classes_load():
    """Each Jira env class must load without error."""
    for name in JIRA_ENV_NAMES:
        cls = get_environment_class(name)
        assert cls is not None, f"get_environment_class({name}) must not return None"


def test_jira_environment_instantiation():
    """Each Jira env must instantiate and reset/step once."""
    for name in JIRA_ENV_NAMES:
        cls = get_environment_class(name)
        env = cls()
        obs, info = env.reset(seed=0)
        assert obs is not None
        obs2, reward, term, trunc, info2 = env.step(0)
        assert obs2 is not None


def test_list_all_environments_includes_jira():
    """list_all_environments() must include Jira envs."""
    all_envs = list_all_environments()
    names = {e["name"] for e in all_envs}
    for name in JIRA_ENV_NAMES:
        assert name in names, f"list_all_environments() must include {name}"
