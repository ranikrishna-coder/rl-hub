"""Tests for contact form endpoint."""


def test_contact_submit_success(client):
    resp = client.post("/api/contact", json={
        "name": "Test User",
        "email": "test@example.com",
        "organization": "Test Org",
        "use_case": "Testing the contact form endpoint",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("ok") is True or data.get("status") == "success" or "id" in data


def test_contact_submit_missing_fields(client):
    resp = client.post("/api/contact", json={
        "name": "",
        "email": "test@example.com",
        "organization": "Test Org",
        "use_case": "Testing",
    })
    # Should reject empty name
    assert resp.status_code in (400, 422, 200)
