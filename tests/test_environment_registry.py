"""Tests for the environment registry — all categories."""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from portal.environment_registry import (
    ENVIRONMENT_REGISTRY,
    get_environment_class,
    get_environment_metadata,
    list_all_environments,
)


def test_registry_has_minimum_environments():
    assert len(ENVIRONMENT_REGISTRY) >= 50, \
        f"Expected at least 50 environments, got {len(ENVIRONMENT_REGISTRY)}"


def test_list_all_environments_consistent():
    all_envs = list_all_environments()
    assert len(all_envs) == len(ENVIRONMENT_REGISTRY)


def test_every_registered_env_has_class_path():
    for name, meta in ENVIRONMENT_REGISTRY.items():
        assert "class_path" in meta, f"{name} missing class_path"


def test_every_registered_env_has_category():
    for name, meta in ENVIRONMENT_REGISTRY.items():
        assert "category" in meta, f"{name} missing category"


def test_metadata_returns_none_for_unknown():
    result = get_environment_metadata("FakeEnv123XYZ")
    assert result is None


def test_known_env_metadata():
    result = get_environment_metadata("JiraIssueResolution")
    assert result is not None
    assert result.get("category") == "jira"


def test_get_class_for_known_env():
    cls = get_environment_class("JiraIssueResolution")
    assert cls is not None
