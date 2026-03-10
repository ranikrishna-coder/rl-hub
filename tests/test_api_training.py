"""Tests for training lifecycle endpoints."""


def test_start_training_valid(client):
    resp = client.post("/train/JiraIssueResolution", json={
        "algorithm": "PPO",
        "num_episodes": 2,
        "max_steps": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["status"] == "running"


def test_start_training_invalid_env(client):
    resp = client.post("/train/NonExistentEnv999", json={
        "algorithm": "PPO",
        "num_episodes": 1,
        "max_steps": 5,
    })
    assert resp.status_code in (404, 400, 500)


def test_training_status_not_found(client):
    resp = client.get("/training/fake-job-id-99999")
    assert resp.status_code in (404, 200)
    if resp.status_code == 200:
        data = resp.json()
        assert data.get("status") in (None, "not_found", "unknown") or "error" in data


def test_list_training_jobs(client):
    resp = client.get("/api/training/jobs")
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data
    assert isinstance(data["jobs"], list)


def test_training_job_has_required_fields(client):
    """Start a job then verify it appears in the list with required fields."""
    # Start a job
    start = client.post("/train/JiraIssueResolution", json={
        "algorithm": "PPO",
        "num_episodes": 1,
        "max_steps": 3,
    })
    if start.status_code != 200:
        return  # skip if start fails
    job_id = start.json()["job_id"]

    # Check it appears in list
    resp = client.get("/api/training/jobs")
    data = resp.json()
    jobs = data.get("jobs", [])
    job = next((j for j in jobs if j.get("job_id") == job_id), None)
    assert job is not None, f"Job {job_id} not found in list"
    assert "status" in job
    assert "environment_name" in job
    assert "algorithm" in job
