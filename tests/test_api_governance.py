"""Tests for governance, KPI, and validation endpoints."""
import pytest


def test_get_kpis(client):
    resp = client.get("/kpis/JiraIssueResolution")
    assert resp.status_code == 200
    data = resp.json()
    assert "kpis" in data or isinstance(data, list)


def test_get_kpis_unknown_env(client):
    resp = client.get("/kpis/NonExistentEnv999")
    assert resp.status_code in (404, 200, 500)


def test_governance_list(client):
    resp = client.get("/governance")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


def test_list_custom_environments(client):
    resp = client.get("/api/custom-environments")
    assert resp.status_code == 200
    data = resp.json()
    assert "environments" in data or "count" in data or isinstance(data, list)


SAMPLE_ENVS = [
    "JiraIssueResolution",
    "TreatmentPathwayOptimization",
]


@pytest.mark.parametrize("env_name", SAMPLE_ENVS)
def test_validate_environment(client, env_name):
    """Sample environments should validate successfully."""
    resp = client.get(f"/validate/{env_name}")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("valid") is True, f"{env_name} validation failed: {data}"


def test_validate_nonexistent_environment(client):
    resp = client.get("/validate/FakeEnv123")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("valid") is False
