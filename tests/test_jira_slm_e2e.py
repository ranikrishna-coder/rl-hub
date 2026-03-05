"""
End-to-end test: Jira SLM training (model endpoint or rule-based fallback).

Verifies training completes. When JIRA_MODEL_ENDPOINT is set, the policy uses the
endpoint; otherwise it uses the rule-based fallback. Both paths are valid.
"""
import os
import sys
import time

import pytest

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from api.main import app


def test_jira_slm_training_e2e():
    """Run SLM training for JiraIssueResolution; passes with endpoint or fallback."""
    client = TestClient(app)

    resp = client.post(
        "/train/JiraIssueResolution",
        json={
            "algorithm": "SLM",
            "num_episodes": 5,
            "max_steps": 20,
            "config": {},
        },
    )
    assert resp.status_code == 200, f"Failed to start training: {resp.text}"
    data = resp.json()
    job_id = data["job_id"]
    assert job_id, "No job_id returned"

    for _ in range(60):
        status_resp = client.get(f"/training/{job_id}")
        assert status_resp.status_code == 200
        job = status_resp.json()
        if job.get("status") in ("completed", "failed"):
            break
        time.sleep(2)

    assert job.get("status") == "completed", (
        f"Training did not complete: status={job.get('status')}, "
        f"error={job.get('error', 'N/A')}"
    )

    slm_ctx = job.get("slm_training_context") or {}
    uses_slm = slm_ctx.get("uses_slm")
    load_error = slm_ctx.get("load_error")

    print("\n--- Jira SLM E2E Test Results ---")
    print(f"Environment: JiraIssueResolution | Algorithm: SLM | Job: {job_id}")
    print(f"Mean reward: {job.get('results', {}).get('mean_reward', 'N/A')}")
    print(f"uses_slm (endpoint used): {uses_slm}")
    if load_error:
        print(f"load_error: {load_error}")
    print("----------------------------------\n")

    # Training must complete; endpoint may or may not be configured
    assert "results" in job, "Job should include results after completion"


if __name__ == "__main__":
    test_jira_slm_training_e2e()
    print("PASS: Jira SLM E2E test")
