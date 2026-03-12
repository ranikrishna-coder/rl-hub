"""Tests for HTML page serving endpoints."""


def test_root_page(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_catalog_page(client):
    resp = client.get("/environments")
    assert resp.status_code == 200


def test_training_console_page(client):
    resp = client.get("/training-console")
    assert resp.status_code == 200


def test_contact_page(client):
    resp = client.get("/contact")
    assert resp.status_code == 200


def test_api_info(client):
    resp = client.get("/api")
    assert resp.status_code == 200
    data = resp.json()
    assert "endpoints" in data or "title" in data or isinstance(data, dict)
