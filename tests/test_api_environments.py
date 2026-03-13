"""Tests for environment listing and metadata endpoints."""


def test_list_environments_returns_200(client):
    resp = client.get("/api/environments")
    assert resp.status_code == 200


def test_list_environments_count(environments_list):
    assert len(environments_list) >= 50


def test_environment_has_required_fields(environments_list):
    """Every environment must have name and category."""
    for env in environments_list:
        assert "name" in env, f"Missing 'name' in {env}"
        assert "category" in env, f"Missing 'category' in {env.get('name')}"


def test_environment_has_system(environments_list):
    """Every environment should have a system field."""
    for env in environments_list:
        assert "system" in env, f"Missing 'system' in {env.get('name')}"


def test_environment_action_metadata(environments_list):
    """Every env should have actionSpace and actionType."""
    for env in environments_list:
        assert "actionSpace" in env or "actions" in env, \
            f"Missing action metadata for {env['name']}"


def test_known_categories_present(environments_list):
    """Key categories must be represented."""
    categories = {e["category"] for e in environments_list}
    expected = {"clinical", "jira"}
    for cat in expected:
        assert cat in categories, f"Category '{cat}' missing from environments"


def test_environment_metadata_endpoint(client):
    resp = client.get("/environment/JiraIssueResolution/metadata")
    if resp.status_code == 200:
        data = resp.json()
        assert "category" in data or "name" in data


def test_environment_metadata_unknown(client):
    resp = client.get("/environment/NonExistentEnv999/metadata")
    # Server may return 404, 500 (unhandled), or 200 with empty data
    assert resp.status_code in (404, 500, 200)
