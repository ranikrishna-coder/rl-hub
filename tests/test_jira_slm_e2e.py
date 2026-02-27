"""
End-to-end test: Jira SLM training for apps/workflow_definitions/jira_workflows.json.
Verifies training completes. If SLM model loads (no 403/network issue), asserts uses_slm;
otherwise training runs with rule-based fallback and test still passes for UAT/CI.
"""
import os
import sys
import time

import pytest

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Import app and dependencies
from fastapi.testclient import TestClient
from api.main import app, training_jobs, run_training
from portal.environment_registry import get_environment_class


def test_jira_slm_training_e2e():
    """Run SLM training for JiraIssueResolution (Issue Resolution from jira_workflows.json)."""
    client = TestClient(app)

    # Start training: JiraIssueResolution maps to issue_resolution in jira_workflows.json
    # Use 5 episodes and 20 max_steps for a fast test
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

    # Poll until complete (max 120 seconds for model load + 5 episodes)
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

    # Check SLM context
    slm_ctx = job.get("slm_training_context") or {}
    uses_slm = slm_ctx.get("uses_slm")
    load_error = slm_ctx.get("load_error")

    # Report results
    print("\n--- Jira SLM E2E Test Results ---")
    print(f"Environment: JiraIssueResolution (issue_resolution from jira_workflows.json)")
    print(f"Algorithm: SLM | Episodes: 5 | Job: {job_id}")
    print(f"Mean reward: {job.get('results', {}).get('mean_reward', 'N/A')}")
    print(f"uses_slm: {uses_slm}")
    if load_error:
        print(f"load_error: {load_error}")
    print("----------------------------------\n")

    # In CI/sandbox Hugging Face often returns 403 or no network; training still completes with fallback.
    if not uses_slm and load_error:
        pytest.skip(
            f"SLM model did not load ({load_error}). "
            "Training completed with rule-based fallback. Run locally with network/HF token for full SLM e2e."
        )
    assert uses_slm, "SLM model was expected to load but did not (no load_error recorded)."


if __name__ == "__main__":
    test_jira_slm_training_e2e()
    print("PASS: Jira SLM E2E test")
