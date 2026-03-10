"""Shared test fixtures for AgentWork Simulator."""
import sys
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture(scope="module")
def client():
    """FastAPI test client, reused per module for efficiency."""
    return TestClient(app)


@pytest.fixture(scope="module")
def environments_list(client):
    """Cached list of all environments from /environments."""
    resp = client.get("/environments")
    assert resp.status_code == 200
    data = resp.json()
    return data.get("environments", data if isinstance(data, list) else [])
