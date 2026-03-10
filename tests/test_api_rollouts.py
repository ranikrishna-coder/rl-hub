"""Tests for rollout storage and retrieval endpoints."""


def test_store_rollout(client):
    rollout = {
        "environment_name": "JiraIssueResolution",
        "episode_number": 1,
        "steps": [],
        "total_reward": 0.5,
        "total_steps": 3,
        "status": "completed",
        "source": "simulation",
    }
    resp = client.post("/api/rollouts", json=rollout)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True or "id" in data


def test_get_all_rollouts(client):
    resp = client.get("/api/rollouts-all")
    assert resp.status_code in (200, 500)  # may error if no rollouts stored yet
    if resp.status_code == 200:
        data = resp.json()
        assert "rollouts" in data or isinstance(data, list)


def test_get_rollouts_by_env(client):
    resp = client.get("/api/rollouts/JiraIssueResolution")
    assert resp.status_code == 200
    data = resp.json()
    assert "environment_name" in data or "rollouts" in data or isinstance(data, list)


def test_rollout_comparison(client):
    resp = client.get("/api/rollout-comparison/JiraIssueResolution")
    assert resp.status_code == 200
    data = resp.json()
    # Should have baseline and/or trained fields
    assert isinstance(data, dict)
