"""
Create Label Studio tasks on the fly from rollouts.json via the API.
"""

import json
import sys
from pathlib import Path

import requests

# ── Configuration ──────────────────────────────────────────────────
LS_URL = "https://annotation.centific.com/"
LS_TOKEN = "934838e229a69e7c4be0798c8c1b25a99d3825fb"
PROJECT_ID = 811
ROLLOUTS_FILE = "rollouts.json"
MAX_STEPS = 10


def flatten_rollout(top: dict, rollout: dict) -> dict:
    """Flatten a nested rollout into a single-level dict matching template.xml fields."""
    data = {
        "task_id": str(top.get("task_id", "")),
        "task_description": str(top.get("task_description", "")),
        "environment": str(top.get("environment", "")),
        "model": str(top.get("model", "")),
        "algorithm": str(top.get("algorithm", "")),
        "max_turns": str(top.get("max_turns", "")),
        "rollout_id": str(rollout.get("rollout_id", "")),
        "train_step": str(rollout.get("train_step", "")),
        "label": str(rollout.get("label", "")),
        "total_reward": str(rollout.get("total_reward", "")),
        "terminal_pass": str(rollout.get("terminal_pass", "")),
        "num_turns": str(rollout.get("num_turns", len(rollout.get("steps", [])))),
        "advantage": str(rollout.get("advantage", "")),
        "rollout_states_url": f"https://datafoundaryapps.blob.core.windows.net/rl-clinkriya-demo/{rollout.get('rollout_id', '')}.png",
    }

    for key, val in rollout.get("episode_rewards", {}).items():
        data[f"episode_rewards_{key}"] = str(val)

    steps = rollout.get("steps", [])
    for i in range(MAX_STEPS):
        if i < len(steps):
            s = steps[i]
            args = s.get("arguments")
            data[f"step_{i}_type"] = str(s.get("type", ""))
            data[f"step_{i}_tool"] = str(s.get("tool") or "—")
            data[f"step_{i}_arguments"] = json.dumps(args) if args is not None else "—"
            data[f"step_{i}_content"] = str(s.get("content") or "—")
            data[f"step_{i}_step_reward"] = str(s.get("step_reward")) if s.get("step_reward") is not None else "—"
            data[f"step_{i}_status"] = str(s.get("status", ""))
            data[f"step_{i}_note"] = str(s.get("note", "") or "—")
        else:
            for field in ("type", "tool", "arguments", "content", "step_reward", "status", "note"):
                data[f"step_{i}_{field}"] = ""

    return data


def create_tasks():
    """Read rollouts file, flatten each rollout, POST to Label Studio."""
    raw = json.loads(Path(ROLLOUTS_FILE).read_text(encoding="utf-8"))
    top = {k: v for k, v in raw.items() if k != "rollouts"}
    rollouts = raw.get("rollouts", [])

    endpoint = f"{LS_URL.rstrip('/')}/api/projects/{PROJECT_ID}/import"
    headers = {
        "Authorization": f"Token {LS_TOKEN}",
        "Content-Type": "application/json",
    }

    tasks = [{"data": flatten_rollout(top, r)} for r in rollouts]
    print(f"Posting {len(tasks)} task(s) to {endpoint} ...")

    resp = requests.post(endpoint, headers=headers, json=tasks)

    if resp.status_code in (200, 201):
        count = resp.json().get("task_count", len(tasks))
        print(f"Created {count} task(s) in project {PROJECT_ID}")
    else:
        print(f"Failed ({resp.status_code}): {resp.text}", file=sys.stderr)
        sys.exit(1)


def test_flatten():
    """Validate flatten_rollout against rollouts.json — no API call needed."""
    raw = json.loads(Path(ROLLOUTS_FILE).read_text(encoding="utf-8"))
    top = {k: v for k, v in raw.items() if k != "rollouts"}
    rollouts = raw.get("rollouts", [])

    assert len(rollouts) == 5, f"Expected 5 rollouts, got {len(rollouts)}"

    TEMPLATE_FIELDS = (
        ["task_id", "task_description", "environment", "model", "algorithm", "max_turns"]
        + ["rollout_id", "train_step", "label", "total_reward", "terminal_pass", "num_turns", "advantage", "rollout_states_url"]
        + [f"episode_rewards_{k}" for k in
           ("qtc_lookup", "threshold_eval", "ecg_order", "drug_stop", "terminal", "spurious_action", "invalid_fhir", "coupled_missing")]
        + [f"step_{i}_{f}" for i in range(MAX_STEPS) for f in ("type", "tool", "arguments", "content", "step_reward", "status", "note")]
    )

    for idx, rollout in enumerate(rollouts):
        flat = flatten_rollout(top, rollout)
        rid = flat["rollout_id"]
        num_turns = int(flat["num_turns"])
        actual_steps = len(rollout["steps"])

        # num_turns must equal the number of steps in the array
        assert num_turns == actual_steps, f"{rid}: num_turns={num_turns} but steps array has {actual_steps} entries"

        # all template fields present
        missing = [f for f in TEMPLATE_FIELDS if f not in flat]
        assert not missing, f"{rid}: missing fields: {missing}"

        # all values are strings
        non_str = {k: type(v).__name__ for k, v in flat.items() if not isinstance(v, str)}
        assert not non_str, f"{rid}: non-string values: {non_str}"

        # populated steps have non-empty type
        for i in range(num_turns):
            assert flat[f"step_{i}_type"] != "", f"{rid}: step_{i}_type is empty but should be populated"

        # padding steps beyond num_turns are empty strings
        for i in range(num_turns, MAX_STEPS):
            for f in ("type", "tool", "arguments", "content", "step_reward", "status", "note"):
                assert flat[f"step_{i}_{f}"] == "", f"{rid}: step_{i}_{f} should be empty but is '{flat[f'step_{i}_{f}']}'"

        print(f"  {rid} ({rollout['label']}): {num_turns} steps, {len(flat)} fields — OK")

    print(f"\nAll {len(rollouts)} rollouts passed validation.")


if __name__ == "__main__":
    # test_flatten()
    create_tasks()  # uncomment to push to Label Studio
