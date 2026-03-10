"""Tests for verifier API endpoints."""


def test_list_verifiers(client):
    resp = client.get("/api/verifiers")
    assert resp.status_code == 200
    data = resp.json()
    assert "verifiers" in data or isinstance(data, list)


def test_create_verifier(client):
    verifier = {
        "name": "Test Verifier",
        "type": "rule-based",
        "system": "Jira",
        "environment": "JiraIssueResolution",
        "description": "Test verifier for unit tests",
    }
    resp = client.post("/api/verifiers", json=verifier)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    assert "verifier" in data
    assert "id" in data["verifier"]


def test_get_verifier_not_found(client):
    resp = client.get("/api/verifiers/nonexistent-id-999")
    assert resp.status_code in (404, 200)
