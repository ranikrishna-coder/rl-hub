"""
FastAPI Backend for RL Hub
Provides endpoints for training, monitoring, and KPI retrieval
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uvicorn
import json
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_local_env_file() -> None:
    """
    Lightweight .env loader so Jira credentials can be configured
    in a file instead of shell exports.

    - Looks for a .env file in the project root (same level as api/, apps/, etc.)
    - Does NOT override environment variables that are already set
    - Ignores comments and blank lines
    """
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(project_root, ".env")
        if not os.path.exists(env_path):
            return

        with open(env_path, "r") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                # Strip optional surrounding quotes
                value = value.strip().strip('"').strip("'")
                if not key:
                    continue
                # For Jira-related settings, always prefer the .env value
                if key.startswith("JIRA_"):
                    os.environ[key] = value
                # For everything else, don't override existing env vars
                elif key not in os.environ:
                    os.environ[key] = value
    except Exception:
        # Never break app startup because of .env parsing problems
        pass


# Load .env if present so Jira config can live in the app repo
_load_local_env_file()


from environments import HealthcareRLEnvironment
from portal.environment_registry import get_environment_class, list_all_environments

# Import verifier architecture
from verifiers.verifier_registry import VerifierRegistry, get_verifier
from verifiers.base_verifier import VerifierConfig

# Import observability
from observability.reward_logger import RewardLogger
from observability.action_trace_logger import ActionTraceLogger
from observability.episode_metrics import EpisodeMetricsTracker
from observability.audit_logger import AuditLogger

# Import governance
from governance.safety_guardrails import SafetyGuardrails, SafetyConfig
from governance.risk_thresholds import RiskThresholds, RiskThresholdConfig
from governance.compliance_rules import ComplianceRules

app = FastAPI(title="RL Hub API", version="1.0.0")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# CORS middleware
# Allow GitHub Pages and common deployment URLs
# Note: FastAPI CORS doesn't support wildcards, so we allow all origins
# In production, you may want to restrict this to specific domains
allowed_origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "https://ranikrishna-coder.github.io",
    "https://rl-hub-api.onrender.com",
]
# Add environment variable for additional origins
if os.getenv("CORS_ORIGINS"):
    allowed_origins.extend(os.getenv("CORS_ORIGINS").split(","))

# For GitHub Pages, we need to allow all origins since we can't predict the exact URL
# In production, you can restrict this by setting CORS_ORIGINS environment variable
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Training jobs storage (in production, use database)
training_jobs: Dict[str, Dict[str, Any]] = {}

# Observability storage (in production, use database)
reward_loggers: Dict[str, RewardLogger] = {}
action_trace_loggers: Dict[str, ActionTraceLogger] = {}
episode_metrics_trackers: Dict[str, EpisodeMetricsTracker] = {}
audit_loggers: Dict[str, AuditLogger] = {}

# Governance storage
governance_configs: Dict[str, Dict[str, Any]] = {}


class TrainingRequest(BaseModel):
    environment_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    algorithm: str = "PPO"
    num_episodes: int = 100
    max_steps: int = 1000
    dataset_url: Optional[str] = None
    verifier_config: Optional[Dict[str, Any]] = None  # Verifier configuration


class TrainingResponse(BaseModel):
    job_id: str
    status: str
    environment_name: str
    message: str


# RL-Env-Studio SPA: serve built React app at /studio
_studio_dir = os.path.join(static_dir, "studio")
_studio_index = os.path.join(_studio_dir, "index.html")


@app.get("/studio")
async def studio_root():
    """Serve RL-Env-Studio SPA (Dashboard, Scenarios, Verifiers, Gym, Training, etc.)"""
    if os.path.isfile(_studio_index):
        return FileResponse(_studio_index)
    raise HTTPException(
        status_code=404,
        detail="RL-Env-Studio not built. Run: npm run build:studio",
    )


@app.get("/studio/{full_path:path}")
async def studio_spa(full_path: str):
    """Serve RL-Env-Studio static assets or SPA fallback for client-side routes"""
    file_path = os.path.join(_studio_dir, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    if os.path.isfile(_studio_index):
        return FileResponse(_studio_index)  # SPA fallback for /studio/verifiers etc.
    raise HTTPException(
        status_code=404,
        detail="RL-Env-Studio not built. Run: npm run build:studio",
    )


@app.get("/")
async def root():
    """Root endpoint - serves the catalog UI"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "RL Hub API",
        "version": "1.0.0",
        "endpoints": {
            "catalog": "/ (this page)",
            "simulation_console": "/test-console",
            "studio": "/studio",
            "environments": "/environments",
            "jira_mock_data": "/jira-mock-data",
            "train": "/train/{environment_name}",
            "kpis": "/kpis/{environment_name}",
            "training_status": "/training/{job_id}",
            "validate": "/validate/{environment_name}",
            "validate_all": "/validate-all",
            "download_model": "/models/{algorithm}/{model_filename}"
        }
    }


def _load_jira_mock_data() -> Dict[str, Any]:
    """Load Jira mock data from apps/workflow_definitions/jira_mock_data.json."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "apps", "workflow_definitions", "jira_mock_data.json")
    if not os.path.exists(path):
        return {"issues": [], "comment_threads": {}, "sample_workflows": {}}
    with open(path, "r") as f:
        return json.load(f)


def _build_live_jira_snapshot(max_issues: int = 50) -> Dict[str, Any]:
    """
    Build a Jira mock-data-like snapshot from a live Jira project for training.
    - Reads JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY
    - Fetches issues via /rest/api/3/search
    - For each issue, fetches valid transitions via /rest/api/3/issue/{key}/transitions
    - Returns a dict shaped like jira_mock_data.json (issues + reward_config passthrough)
    """
    base_url = os.getenv("JIRA_BASE_URL")
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")
    project_key = os.getenv("JIRA_PROJECT_KEY")

    if not (base_url and email and api_token and project_key):
        raise RuntimeError("JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, and JIRA_PROJECT_KEY must be set to use live Jira for training.")

    try:
        import requests
    except ImportError as e:
        raise RuntimeError("requests library is required for live Jira training. Install with: pip install requests") from e

    # Base search to pull recent issues for the project
    search_url = base_url.rstrip("/") + "/rest/api/3/search"
    jql = f"project = {project_key} ORDER BY created DESC"
    params = {
        "jql": jql,
        "maxResults": max_issues,
        "fields": "summary,description,status",
    }
    resp = requests.get(search_url, params=params, auth=(email, api_token), timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"Jira search failed ({resp.status_code}): {resp.text}")

    data = resp.json()
    issues = data.get("issues", [])

    # Load existing mock data once so we can reuse reward_config
    existing_mock = _load_jira_mock_data()
    reward_config = existing_mock.get("reward_config", {})

    # Build issues list compatible with jira_mock_data.json
    snapshot_issues = []
    for issue in issues:
        key = issue.get("key")
        fields = issue.get("fields") or {}
        status = (fields.get("status") or {}).get("name") or "To Do"
        status_id = (fields.get("status") or {}).get("id") or ""
        summary = fields.get("summary") or ""
        description = fields.get("description") or ""

        # Fetch transitions for this issue
        transitions_url = base_url.rstrip("/") + f"/rest/api/3/issue/{key}/transitions"
        t_resp = requests.get(transitions_url, auth=(email, api_token), timeout=10)
        valid_transitions = []
        if t_resp.status_code == 200:
            t_data = t_resp.json()
            for t in t_data.get("transitions", []) or []:
                valid_transitions.append({"id": t.get("id"), "name": t.get("name")})

        snapshot_issues.append(
            {
                "key": key,
                "summary": summary,
                "description": description,
                "status": status,
                "statusId": status_id,
                "valid_transitions": valid_transitions,
            }
        )

    return {
        "issues": snapshot_issues,
        "comment_threads": existing_mock.get("comment_threads", {}),
        "sample_workflows": existing_mock.get("sample_workflows", {}),
        "reward_config": reward_config,
    }


@app.get("/jira-mock-data")
async def get_jira_mock_data():
    """Return mock Jira issues and comment threads for sample use cases (issue resolution, comment management)."""
    return _load_jira_mock_data()


class JiraSubtaskRequest(BaseModel):
    """Request model for creating a live Jira sub-task under a parent issue (e.g. epic)."""
    parent_key: str
    summary: str
    description: Optional[str] = None
    project_key: Optional[str] = None
    issue_type_name: Optional[str] = None  # Override for non-standard sub-task type names


@app.post("/jira/subtasks")
async def create_jira_subtask(req: JiraSubtaskRequest):
    """
    Create a real Jira sub-task under a parent issue when JIRA_* env vars are configured.
    This is optional and does not affect mock-based Jira workflows.
    """
    base_url = os.getenv("JIRA_BASE_URL")
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")
    default_project = os.getenv("JIRA_PROJECT_KEY")
    # Allow sites/projects where the sub-task issue type has a custom name
    default_issue_type_name = os.getenv("JIRA_SUBTASK_ISSUE_TYPE_NAME", "Sub-task")

    if not (base_url and email and api_token):
        raise HTTPException(
            status_code=400,
            detail="JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN must be set on the server to use live Jira."
        )

    # Build Jira Cloud / Server REST API request
    url = base_url.rstrip("/") + "/rest/api/3/issue"

    # Build list of candidate issue type names, allowing multiple values like "subtask,task,story"
    raw_names = (req.issue_type_name or default_issue_type_name or "Sub-task")
    candidate_names = [
        n.strip() for n in str(raw_names).split(",") if str(n).strip()
    ]
    if not candidate_names:
        candidate_names = ["Sub-task"]

    # Prefer "subtask-like" names but allow task/story as fallbacks
    preferred_order = ["sub-task", "subtask", "Sub-task", "Subtask", "task", "Task", "story", "Story"]
    # Reorder candidate_names to follow preferred_order where possible
    ordered_candidates: list[str] = []
    seen = set()
    for name in preferred_order:
        for c in candidate_names:
            if c.lower() == name.lower() and c.lower() not in seen:
                ordered_candidates.append(c)
                seen.add(c.lower())
    for c in candidate_names:
        if c.lower() not in seen:
            ordered_candidates.append(c)

    # By default, use the first candidate name; this will be overridden with an ID
    # if we successfully discover a matching issue type via Jira's API.
    effective_issue_type_name = ordered_candidates[0]

    fields: Dict[str, Any] = {
        "parent": {"key": req.parent_key},
        "summary": req.summary,
        "issuetype": {"name": effective_issue_type_name},
    }
    if req.description:
        # Jira Cloud v3 API expects description in Atlassian Document Format (ADF)
        fields["description"] = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": req.description,
                        }
                    ],
                }
            ],
        }
    # Jira requires a valid project for issue creation, even for sub-tasks.
    # Prefer an explicit project_key from the request; otherwise fall back to JIRA_PROJECT_KEY.
    effective_project_key = req.project_key or default_project
    if effective_project_key:
        fields["project"] = {"key": effective_project_key}

    payload = {"fields": fields}

    try:
        import requests  # Local import to avoid hard dependency during non-Jira usage
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        resp = requests.post(
            url,
            json=payload,
            auth=(email, api_token),
            headers=headers,
            timeout=10,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to contact Jira: {e}")

    if resp.status_code not in (200, 201):
        msg = f"Jira API error {resp.status_code}"
        jira_body: Any = None
        try:
            jira_body = resp.json()
            # Prefer concise error details without leaking sensitive data
            err = jira_body.get("errorMessages") or jira_body.get("errors") or jira_body.get("message")
            if err:
                msg += f": {err}"
        except Exception:
            jira_body = resp.text
        # Return structured detail so the client can see exactly what Jira said
        raise HTTPException(
            status_code=resp.status_code,
            detail={
                "message": msg,
                "jira_response": jira_body,
                "jira_url": url,
            },
        )

    data = resp.json()
    return {
        "key": data.get("key"),
        "id": data.get("id"),
        "self": data.get("self"),
    }


@app.delete("/jira/issues/{issue_key}")
async def delete_jira_issue(issue_key: str):
    """
    Delete a Jira issue (including sub-tasks) by key in a live Jira instance.
    This is used by the simulation console's JiraSubtaskManagement delete scenario.
    """
    base_url = os.getenv("JIRA_BASE_URL")
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")

    if not (base_url and email and api_token):
        raise HTTPException(
            status_code=400,
            detail="JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN must be set on the server to use live Jira."
        )

    url = base_url.rstrip("/") + f"/rest/api/3/issue/{issue_key}"

    try:
        import requests
        resp = requests.delete(
            url,
            auth=(email, api_token),
            timeout=10,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to contact Jira: {e}")

    if resp.status_code not in (200, 204):
        msg = f"Jira API error {resp.status_code}"
        jira_body: Any = None
        try:
            jira_body = resp.json()
            err = jira_body.get("errorMessages") or jira_body.get("errors") or jira_body.get("message")
            if err:
                msg += f": {err}"
        except Exception:
            jira_body = resp.text
        raise HTTPException(
            status_code=resp.status_code,
            detail={
                "message": msg,
                "jira_response": jira_body,
                "jira_url": url,
            },
        )

    return {"status": "deleted", "issue_key": issue_key}


@app.delete("/jira/issues/{issue_key}/subtasks")
async def delete_jira_subtasks(issue_key: str):
    """
    Delete all subtasks under a given parent issue key in a live Jira instance.
    Used by the JiraSubtaskManagement delete_subtask scenario when a task key is provided.
    """
    base_url = os.getenv("JIRA_BASE_URL")
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")

    if not (base_url and email and api_token):
        raise HTTPException(
            status_code=400,
            detail="JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN must be set on the server to use live Jira."
        )

    try:
        import requests
    except ImportError as e:
        raise HTTPException(status_code=500, detail="requests library is required for Jira operations.") from e

    issue_url = base_url.rstrip("/") + f"/rest/api/3/issue/{issue_key}"

    try:
        resp = requests.get(issue_url, params={"fields": "subtasks"}, auth=(email, api_token), timeout=10)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to contact Jira: {e}")

    if resp.status_code != 200:
        msg = f"Jira API error {resp.status_code}"
        jira_body: Any = None
        try:
            jira_body = resp.json()
            err = jira_body.get("errorMessages") or jira_body.get("errors") or jira_body.get("message")
            if err:
                msg += f": {err}"
        except Exception:
            jira_body = resp.text
        raise HTTPException(
            status_code=resp.status_code,
            detail={
                "message": msg,
                "jira_response": jira_body,
                "jira_url": issue_url,
            },
        )

    data = resp.json()
    subtasks = (data.get("fields") or {}).get("subtasks") or []
    if not subtasks:
        return {"status": "no_subtasks", "parent_issue_key": issue_key, "deleted": [], "errors": []}

    deleted: list[str] = []
    errors: list[Dict[str, Any]] = []
    for st in subtasks:
        st_key = st.get("key")
        if not st_key:
            continue
        del_url = base_url.rstrip("/") + f"/rest/api/3/issue/{st_key}"
        try:
            del_resp = requests.delete(del_url, auth=(email, api_token), timeout=10)
        except Exception as e:
            errors.append({"subtask": st_key, "error": str(e)})
            continue
        if del_resp.status_code in (200, 204):
            deleted.append(st_key)
        else:
            try:
                body = del_resp.json()
            except Exception:
                body = del_resp.text
            errors.append({"subtask": st_key, "status": del_resp.status_code, "response": body})

    return {
        "status": "ok",
        "parent_issue_key": issue_key,
        "deleted": deleted,
        "errors": errors,
    }


@app.get("/config.js")
async def get_config():
    """Serve config.js with API URL"""
    # Get the API URL from environment or use current request host
    api_url = os.getenv("API_URL", "https://rl-hub-api.onrender.com")
    
    # If API_URL is not set, try to construct from request
    # This will be handled by the JavaScript auto-detection
    
    config_content = f"""// API Configuration
// This can be overridden by setting window.API_BASE before loading app.js
window.API_BASE = window.API_BASE || '{api_url}';
console.log('🚀 RL Hub - API Base URL:', window.API_BASE);
"""
    from fastapi.responses import Response
    return Response(content=config_content, media_type="application/javascript")


@app.get("/test-console")
async def test_console(env: Optional[str] = None):
    """Simulation console for any RL environment (serves simulation-console.html)."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    console_path = os.path.join(static_dir, "simulation-console.html")
    if os.path.exists(console_path):
        return FileResponse(console_path)
    raise HTTPException(status_code=404, detail="Simulation console not found")


@app.get("/environments")
async def list_environments():
    """List all available environments with enhanced metadata"""
    environments = list_all_environments()
    
    # Enhance each environment with actions, state features, and action type
    enhanced_environments = []
    for env_data in environments:
        env_name = env_data["name"]
        enhanced_env = env_data.copy()
        
        try:
            # Get the environment class
            env_class = get_environment_class(env_name)
            if env_class:
                # Extract actions from ACTIONS attribute (some environments use different names)
                actions = []
                if hasattr(env_class, 'ACTIONS'):
                    actions = env_class.ACTIONS
                elif hasattr(env_class, 'PRIORITIES'):  # Some environments use PRIORITIES
                    actions = env_class.PRIORITIES
                elif hasattr(env_class, 'INTERVENTIONS'):  # Some use INTERVENTIONS
                    actions = env_class.INTERVENTIONS
                elif hasattr(env_class, 'STRATA'):  # Some use STRATA
                    actions = env_class.STRATA
                
                if actions:
                    enhanced_env["actions"] = actions
                    enhanced_env["actionSpace"] = len(actions)
                else:
                    # Try to get from action_space if available
                    if hasattr(env_class, 'action_space'):
                        action_space = env_class.action_space
                        if hasattr(action_space, 'n'):
                            enhanced_env["actionSpace"] = action_space.n
                            enhanced_env["actions"] = [f"action_{i}" for i in range(action_space.n)]
                        else:
                            enhanced_env["actions"] = []
                            enhanced_env["actionSpace"] = "N/A"
                    else:
                        enhanced_env["actions"] = []
                        enhanced_env["actionSpace"] = "N/A"
                
                # Extract state features count from observation_space
                if hasattr(env_class, 'observation_space'):
                    obs_space = env_class.observation_space
                    if hasattr(obs_space, 'shape'):
                        enhanced_env["stateFeatures"] = obs_space.shape[0] if len(obs_space.shape) > 0 else "N/A"
                    else:
                        enhanced_env["stateFeatures"] = "N/A"
                else:
                    enhanced_env["stateFeatures"] = "N/A"
                
                # Determine action type from action_space
                if hasattr(env_class, 'action_space'):
                    action_space = env_class.action_space
                    if hasattr(action_space, '__class__'):
                        action_type_name = action_space.__class__.__name__
                        if 'Discrete' in action_type_name:
                            enhanced_env["actionType"] = "Discrete"
                        elif 'Box' in action_type_name:
                            enhanced_env["actionType"] = "Continuous"
                        elif 'MultiDiscrete' in action_type_name:
                            enhanced_env["actionType"] = "Multi-Discrete"
                        else:
                            enhanced_env["actionType"] = "Discrete"  # Default
                    else:
                        enhanced_env["actionType"] = "Discrete"
                else:
                    enhanced_env["actionType"] = "Discrete"
            else:
                # Fallback if class can't be loaded
                enhanced_env["actions"] = []
                enhanced_env["actionSpace"] = "N/A"
                enhanced_env["stateFeatures"] = "N/A"
                enhanced_env["actionType"] = "Discrete"
        except Exception as e:
            # If there's an error loading the class, use defaults
            enhanced_env["actions"] = []
            enhanced_env["actionSpace"] = "N/A"
            enhanced_env["stateFeatures"] = "N/A"
            enhanced_env["actionType"] = "Discrete"
        
        enhanced_environments.append(enhanced_env)
    
    return {
        "count": len(enhanced_environments),
        "environments": enhanced_environments
    }


@app.post("/train/{environment_name}", response_model=TrainingResponse)
async def start_training(
    environment_name: str,
    request: TrainingRequest,
    background_tasks: BackgroundTasks
):
    """Start training for a specific environment"""
    try:
        # Use environment_name from path (more reliable than body)
        final_env_name = environment_name
        
        # Get environment class
        env_class = get_environment_class(final_env_name)
        if env_class is None:
            # Try to get more details about why it failed
            from portal.environment_registry import ENVIRONMENT_REGISTRY
            if final_env_name not in ENVIRONMENT_REGISTRY:
                available = list(ENVIRONMENT_REGISTRY.keys())[:10]
                raise HTTPException(
                    status_code=404, 
                    detail=f"Environment '{final_env_name}' not found in registry. Available: {', '.join(available)}..."
                )
            else:
                class_path = ENVIRONMENT_REGISTRY[final_env_name].get("class_path", "unknown")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to load environment class for '{final_env_name}'. Class path: {class_path}. Check that the environment file exists and the class name is correct."
                )
        
        # Jira envs: apply training flow from apps folder (Training.tsx - 320 episodes, short max_steps)
        req = request
        if final_env_name in ("JiraIssueResolution", "JiraStatusUpdate", "JiraCommentManagement", "JiraSubtaskManagement"):
            if req.num_episodes == 100:
                req = req.model_copy(update={"num_episodes": 320})
            if req.max_steps == 1000:
                req = req.model_copy(update={"max_steps": 50})
        
        # Create job ID
        import uuid
        job_id = str(uuid.uuid4())
        
        # Create models directory if it doesn't exist
        models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", req.algorithm.lower())
        os.makedirs(models_dir, exist_ok=True)
        
        # Model path
        model_filename = f"{final_env_name}_{job_id}.zip"
        model_path = os.path.join(models_dir, model_filename)
        
        # Store job info
        training_jobs[job_id] = {
            "job_id": job_id,
            "environment_name": final_env_name,
            "status": "running",
            "algorithm": req.algorithm,
            "num_episodes": req.num_episodes,
            "progress": 0,
            "results": None,
            "model_path": model_path,
            "model_url": f"/models/{req.algorithm.lower()}/{model_filename}",
            "dataset_url": req.dataset_url
        }
        
        # Start training in background
        background_tasks.add_task(
            run_training,
            job_id,
            env_class,
            final_env_name,
            req.config,
            req.algorithm,
            req.num_episodes,
            req.max_steps,
            req.dataset_url,
            model_path,
            req.verifier_config  # Pass verifier config
        )
        
        return TrainingResponse(
            job_id=job_id,
            status="running",
            environment_name=final_env_name,
            message=f"Training started for {final_env_name}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


def run_training(
    job_id: str,
    env_class: type,
    environment_name: str,
    config: Optional[Dict[str, Any]],
    algorithm: str,
    num_episodes: int,
    max_steps: int,
    dataset_url: Optional[str],
    model_path: str,
    verifier_config: Optional[Dict[str, Any]] = None
):
    """Run training in background"""
    try:
        # Download dataset if URL provided
        if dataset_url:
            try:
                import urllib.request
                import tempfile
                dataset_path = os.path.join(tempfile.gettempdir(), f"dataset_{job_id}.csv")
                urllib.request.urlretrieve(dataset_url, dataset_path)
                training_jobs[job_id]["dataset_path"] = dataset_path
            except Exception as e:
                training_jobs[job_id]["dataset_error"] = f"Failed to download dataset: {str(e)}"
                # Continue without dataset - will use synthetic data
        
        # Validate environment class
        if env_class is None:
            raise ValueError(f"Environment class for {environment_name} is None - check registry")

        # Jira envs: reset mock data to original file before training (restore from backup if it exists),
        # or optionally build a live Jira snapshot when enabled.
        JIRA_ENV_NAMES = ("JiraIssueResolution", "JiraStatusUpdate", "JiraCommentManagement", "JiraSubtaskManagement")
        jira_live_snapshot: Optional[Dict[str, Any]] = None
        if environment_name in JIRA_ENV_NAMES:
            use_live_flag = os.getenv("JIRA_USE_LIVE_FOR_TRAINING", "").lower() in ("1", "true", "yes")
            if use_live_flag:
                try:
                    jira_live_snapshot = _build_live_jira_snapshot()
                    training_jobs[job_id]["jira_live_training"] = {
                        "enabled": True,
                        "issue_count": len(jira_live_snapshot.get("issues", [])),
                    }
                except Exception as e:
                    # Fall back to file-based mock data if live snapshot fails
                    training_jobs[job_id]["jira_live_training_error"] = str(e)
                    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    mock_path = os.path.join(base, "apps", "workflow_definitions", "jira_mock_data.json")
                    orig_path = os.path.join(base, "apps", "workflow_definitions", "jira_mock_data.original.json")
                    if os.path.exists(orig_path) and os.path.exists(mock_path):
                        import shutil
                        shutil.copy2(orig_path, mock_path)
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                mock_path = os.path.join(base, "apps", "workflow_definitions", "jira_mock_data.json")
                orig_path = os.path.join(base, "apps", "workflow_definitions", "jira_mock_data.original.json")
                if os.path.exists(orig_path) and os.path.exists(mock_path):
                    import shutil
                    shutil.copy2(orig_path, mock_path)
        
        # Create verifier if config provided, or for Jira envs use app-defined Jira verifier
        verifier = None
        jira_envs_workflow_map = {
            "JiraIssueResolution": "issue_resolution",
            "JiraStatusUpdate": "status_update",
            "JiraCommentManagement": "comment_management",
            "JiraSubtaskManagement": "subtask_management",
        }
        # Allow UI to choose Jira verifier via verifier_config.metadata.workflow_id
        if (verifier_config or {}).get("type") == "jira_workflow" and (verifier_config or {}).get("metadata", {}).get("workflow_id"):
            jira_env_workflow = verifier_config["metadata"]["workflow_id"]
        else:
            jira_env_workflow = jira_envs_workflow_map.get(environment_name)

        if jira_env_workflow and environment_name in jira_envs_workflow_map:
            # Jira environments: use Jira verifier from apps folder (Verifiers.tsx / workflow_definitions)
            try:
                verifier_config_obj = VerifierConfig(
                    weights=((verifier_config or {}).get("weights")) or {},
                    thresholds=((verifier_config or {}).get("thresholds")) or {},
                    enabled=((verifier_config or {}).get("enabled", True)),
                    metadata={"workflow_id": jira_env_workflow}
                )
                verifier = VerifierRegistry.create_verifier(
                    "jira_workflow", verifier_config_obj,
                    instance_id=f"jira_{environment_name}_{id(verifier_config_obj)}"
                )
            except Exception as e:
                print(f"Warning: Failed to create Jira verifier: {e}, using env built-in")
                verifier = None
        elif verifier_config:
            try:
                verifier_type = verifier_config.get("type", "ensemble")
                if verifier_type == "ensemble" or verifier_type is None:
                    verifier = VerifierRegistry.create_default_ensemble(
                        configs=verifier_config.get("verifiers", {})
                    )
                else:
                    verifier_config_obj = VerifierConfig(
                        weights=verifier_config.get("weights", {}),
                        thresholds=verifier_config.get("thresholds", {}),
                        enabled=verifier_config.get("enabled", True),
                        metadata=verifier_config.get("metadata", {})
                    )
                    verifier = VerifierRegistry.create_verifier(verifier_type, verifier_config_obj)
            except Exception as e:
                print(f"Warning: Failed to create verifier: {e}, using default")
                verifier = None
        
        # Create environment with error handling
        try:
            # Check if constructor accepts verifier parameter
            import inspect
            sig = inspect.signature(env_class.__init__)
            has_verifier_param = 'verifier' in sig.parameters

            # Merge in Jira live snapshot if available
            effective_config = (config or {}).copy() if config is not None else {}
            if jira_live_snapshot is not None and environment_name in JIRA_ENV_NAMES:
                effective_config["mock_data_override"] = jira_live_snapshot

            # Try with config, max_steps, and verifier
            if verifier is not None and has_verifier_param:
                if effective_config:
                    env = env_class(config=effective_config, max_steps=max_steps, verifier=verifier)
                else:
                    env = env_class(max_steps=max_steps, verifier=verifier)
            elif effective_config:
                try:
                    env = env_class(config=effective_config, max_steps=max_steps)
                except TypeError:
                    env = env_class(config=effective_config)
            else:
                try:
                    env = env_class(max_steps=max_steps)
                except TypeError:
                    env = env_class()
        except Exception as e:
            raise ValueError(f"Failed to instantiate environment {environment_name}: {str(e)}")
        
        # Validate environment has required methods
        if not hasattr(env, 'reset') or not hasattr(env, 'step') or not hasattr(env, 'action_space'):
            raise ValueError(f"Environment {environment_name} does not have required Gymnasium interface")

        # Jira SLM policy: use Small Language Model for Jira envs when algorithm is SLM
        jira_slm_policy = None
        JIRA_ENVS_FOR_SLM = ("JiraIssueResolution", "JiraStatusUpdate", "JiraCommentManagement", "JiraSubtaskManagement")
        if algorithm.upper() == "SLM" and environment_name in JIRA_ENVS_FOR_SLM and hasattr(env, "_expected_order"):
            try:
                from policies.jira_slm_policy import JiraSLMPolicy
                jira_slm_policy = JiraSLMPolicy(env._expected_order, use_slm=True)
            except Exception as e:
                print(f"Warning: Jira SLM policy creation failed: {e}. Using random actions. Install: pip install transformers accelerate")

        # Simple training loop (in production, use stable-baselines3 or similar)
        total_rewards = []
        consecutive_errors = 0
        # Allow up to 20% of episodes to fail (min 10, max 50); also stop on 10+ consecutive failures
        max_total_errors = min(50, max(10, int(0.20 * num_episodes)))
        # For Jira Subtask Management, capture episodes where a subtask is created
        subtask_episodes: list[Dict[str, Any]] = []
        for episode in range(num_episodes):
            try:
                # Reset environment (pass episode_index so Jira env cycles through all mock issues)
                if environment_name in JIRA_ENVS_FOR_SLM:
                    reset_result = env.reset(seed=episode, options={"episode_index": episode})
                else:
                    reset_result = env.reset(seed=episode)
                if isinstance(reset_result, tuple):
                    state, info = reset_result
                else:
                    state = reset_result
                    info = {}
                
                episode_reward = 0.0
                episode_steps = 0
                
                for step in range(max_steps):
                    # Get action: SLM policy for Jira when algorithm=SLM, else random
                    try:
                        if jira_slm_policy is not None:
                            action, step_info = jira_slm_policy.predict(
                                state, deterministic=False, return_explanation=True
                            )
                            action = int(action)
                            # Keep one explainability sample (last step of first episode, or every 50th step)
                            if step_info and (episode == 0 and step == 0 or (episode * max_steps + step) % 50 == 0):
                                training_jobs[job_id]["slm_explainability"] = {
                                    "episode": episode + 1,
                                    "step": step + 1,
                                    "prompt": step_info.get("prompt"),
                                    "raw_output": step_info.get("raw_output"),
                                    "parsed_tool": step_info.get("parsed_tool"),
                                    "correct_next": step_info.get("correct_next"),
                                    "action": action,
                                    "explanation": step_info.get("explanation"),
                                }
                        else:
                            action = env.action_space.sample()
                    except Exception as e:
                        raise ValueError(f"Failed to sample action from action space: {str(e)}")
                    
                    # Take step
                    try:
                        step_result = env.step(action)
                        if len(step_result) == 5:
                            state, reward, terminated, truncated, info = step_result
                        elif len(step_result) == 4:
                            # Older Gym API
                            state, reward, done, info = step_result
                            terminated = done
                            truncated = False
                        else:
                            raise ValueError(f"Unexpected step result format: {len(step_result)} values")
                    except Exception as e:
                        raise ValueError(f"Environment step failed: {str(e)}")
                    
                    episode_reward += float(reward)
                    episode_steps += 1

                    # JiraSubtaskManagement: log when create_subtask is used
                    if environment_name == "JiraSubtaskManagement":
                        try:
                            ti = (info.get("transition_info") or info) if isinstance(info, dict) else {}
                            if ti.get("tool_used") == "create_subtask" and ti.get("valid_step"):
                                subtask_episodes.append({
                                    "episode": episode + 1,
                                    "step": step + 1,
                                    "issue_key": ti.get("current_issue_key"),
                                    "tool_sequence": ti.get("tool_sequence_after") or [],
                                    "workflow_id": ti.get("workflow_id")
                                })
                        except Exception:
                            # Logging is best-effort; don't break training
                            pass
                    
                    if terminated or truncated:
                        break
                
                total_rewards.append(episode_reward)
                consecutive_errors = 0  # Reset on successful episode
                training_jobs[job_id]["progress"] = int((episode + 1) / num_episodes * 100)
                
                # Update progress every 10 episodes or at the end
                if (episode + 1) % 10 == 0 or (episode + 1) == num_episodes:
                    training_jobs[job_id]["current_episode"] = episode + 1
                    training_jobs[job_id]["avg_reward_so_far"] = sum(total_rewards) / len(total_rewards) if total_rewards else 0.0
                    
            except Exception as episode_error:
                # Log episode error but continue training
                consecutive_errors += 1
                error_msg = str(episode_error)
                print(f"Error in episode {episode + 1} for {environment_name}: {error_msg}")
                training_jobs[job_id]["episode_errors"] = training_jobs[job_id].get("episode_errors", [])
                training_jobs[job_id]["episode_errors"].append({
                    "episode": episode + 1,
                    "error": error_msg
                })
                # Use zero reward for failed episode
                total_rewards.append(0.0)
                training_jobs[job_id]["progress"] = int((episode + 1) / num_episodes * 100)
                
                # Stop on too many consecutive errors (sustained failure) or if total errors exceed cap
                if consecutive_errors > 10:
                    raise ValueError(f"Too many consecutive episode errors ({consecutive_errors}). Last error: {error_msg}")
                if len(training_jobs[job_id]["episode_errors"]) > max_total_errors:
                    raise ValueError(f"Too many total episode errors (>{max_total_errors}). Last error: {error_msg}")
        
        # Attach SLM explainability: what the model is training on
        if jira_slm_policy is not None:
            try:
                training_jobs[job_id]["slm_training_context"] = jira_slm_policy.get_training_context()
            except Exception as e:
                training_jobs[job_id]["slm_training_context_error"] = str(e)

        # Calculate final statistics
        if len(total_rewards) > 0:
            mean_reward = sum(total_rewards) / len(total_rewards)
            max_reward = max(total_rewards)
            min_reward = min(total_rewards)
        else:
            mean_reward = 0.0
            max_reward = 0.0
            min_reward = 0.0
        
        # Save model metadata
        model_metadata = {
            "job_id": job_id,
            "environment_name": environment_name,
            "algorithm": algorithm,
            "num_episodes": num_episodes,
            "mean_reward": mean_reward,
            "max_reward": max_reward,
            "min_reward": min_reward,
            "total_episodes_completed": len(total_rewards),
            "training_completed": True,
            "timestamp": str(os.path.getmtime(__file__) if os.path.exists(__file__) else "")
        }
        
        # Ensure models directory exists
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        metadata_path = model_path.replace(".zip", "_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(model_metadata, f, indent=2)

        # For JiraSubtaskManagement, save a subtask action log alongside the model
        if environment_name == "JiraSubtaskManagement" and subtask_episodes:
            subtask_log = {
                "job_id": job_id,
                "environment_name": environment_name,
                "algorithm": algorithm,
                "num_episodes": num_episodes,
                "subtask_episodes": subtask_episodes,
            }
            subtask_log_path = model_path.replace(".zip", "_subtasks.json")
            try:
                with open(subtask_log_path, "w") as f:
                    json.dump(subtask_log, f, indent=2)
                # Expose download URL in training job payload
                rel_url = f"/models/{algorithm.lower()}/" + os.path.basename(subtask_log_path)
                training_jobs[job_id]["subtask_log_path"] = subtask_log_path
                training_jobs[job_id]["subtask_log_url"] = rel_url
            except Exception as e:
                training_jobs[job_id]["subtask_log_error"] = str(e)
        
        # Store results
        training_jobs[job_id]["status"] = "completed"
        training_jobs[job_id]["results"] = {
            "mean_reward": mean_reward,
            "max_reward": max_reward,
            "min_reward": min_reward,
            "total_episodes": num_episodes,
            "episodes_completed": len(total_rewards)
        }
        training_jobs[job_id]["model_saved"] = True
        training_jobs[job_id]["model_metadata"] = model_metadata
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        training_jobs[job_id]["status"] = "failed"
        training_jobs[job_id]["error"] = str(e)
        training_jobs[job_id]["error_traceback"] = error_trace
        print(f"Training failed for {environment_name}: {error_trace}")


@app.get("/training/{job_id}")
async def get_training_status(job_id: str):
    """Get training job status"""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return training_jobs[job_id]


class StepScore(BaseModel):
    """Per-step score for reasoning step evaluation."""
    step_index: int
    score: str  # "correct" | "flawed" | "critical_error"


class HumanEvalRequest(BaseModel):
    """Request model for human evaluation of a training job."""
    decision: str  # "yes" (approved) or "no" (rejected)
    comments: Optional[str] = None
    step_scores: Optional[List[StepScore]] = None  # per-step scores for reasoning steps


@app.post("/human-eval/{job_id}")
async def submit_human_eval(job_id: str, req: HumanEvalRequest):
    """
    Persist a human evaluation for a training job.
    Used after verifier step to capture human judgment (for RLHF / model selection).
    Supports optional per-step scores for reasoning steps.
    """
    job = training_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    decision_normalized = (req.decision or "").strip().lower()
    if decision_normalized not in ("yes", "no"):
        raise HTTPException(status_code=400, detail="decision must be 'yes' or 'no'")

    from datetime import datetime

    entry = {
        "decision": decision_normalized,
        "comments": req.comments or "",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if req.step_scores:
        entry["step_scores"] = [{"step_index": s.step_index, "score": s.score} for s in req.step_scores]

    # Append to per-job human evaluations list
    evals = job.get("human_evaluations") or []
    evals.append(entry)
    job["human_evaluations"] = evals
    # Store latest for quick access
    job["last_human_evaluation"] = entry

    return {
        "success": True,
        "job_id": job_id,
        "evaluation": entry,
        "total_evaluations": len(evals),
    }


@app.get("/kpis/{environment_name}")
async def get_kpis(
    environment_name: str, 
    episode_id: Optional[int] = None,
    verifier_type: Optional[str] = None,
    verifier_config: Optional[str] = None  # JSON string of verifier config
):
    """Get KPI metrics for an environment"""
    try:
        env_class = get_environment_class(environment_name)
        if env_class is None:
            raise HTTPException(status_code=404, detail=f"Environment {environment_name} not found")
        
        # Parse verifier config if provided
        verifier = None
        if verifier_type or verifier_config:
            try:
                config_dict = json.loads(verifier_config) if verifier_config else {}
                if verifier_type == "ensemble" or verifier_type is None:
                    # Default to ensemble if not specified
                    verifier = VerifierRegistry.create_default_ensemble(
                        configs=config_dict.get("verifiers", {})
                    )
                else:
                    verifier_config_obj = VerifierConfig(
                        weights=config_dict.get("weights", {}),
                        thresholds=config_dict.get("thresholds", {}),
                        enabled=config_dict.get("enabled", True),
                        metadata=config_dict.get("metadata", {})
                    )
                    verifier = VerifierRegistry.create_verifier(verifier_type, verifier_config_obj)
            except Exception as e:
                # If verifier creation fails, use default (environment will create its own)
                print(f"Warning: Failed to create verifier: {e}")
                verifier = None
        
        # Create environment instance with verifier if provided
        try:
            if verifier is not None and hasattr(env_class, '__init__'):
                # Check if constructor accepts verifier parameter
                import inspect
                sig = inspect.signature(env_class.__init__)
                if 'verifier' in sig.parameters:
                    env = env_class(verifier=verifier)
                else:
                    env = env_class()
            else:
                env = env_class()
        except TypeError:
            # Fallback if verifier parameter not supported
            env = env_class()
        
        state, info = env.reset()
        
        # Run a few steps to generate KPIs
        for _ in range(10):
            action = env.action_space.sample()
            state, reward, terminated, truncated, info = env.step(action)
            if terminated or truncated:
                break
        
        # Get KPIs
        kpis = env.get_kpis()
        
        return {
            "environment_name": environment_name,
            "kpis": kpis.__dict__,
            "episode_summary": env.get_episode_summary(),
            "verifier_used": verifier.__class__.__name__ if verifier else "default"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/environment/{environment_name}/metadata")
async def get_environment_metadata(environment_name: str):
    """Get metadata for an environment"""
    try:
        from portal.environment_registry import get_environment_metadata
        metadata = get_environment_metadata(environment_name)
        if metadata is None:
            raise HTTPException(status_code=404, detail=f"Environment {environment_name} not found")
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/{algorithm}/{model_filename}")
async def download_model(algorithm: str, model_filename: str):
    """Download a trained model"""
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", algorithm.lower())
    model_path = os.path.join(models_dir, model_filename)
    
    if not os.path.exists(model_path):
        # Try metadata file
        metadata_path = model_path.replace(".zip", "_metadata.json")
        if os.path.exists(metadata_path):
            return FileResponse(metadata_path, media_type="application/json")
        raise HTTPException(status_code=404, detail="Model not found")
    
    return FileResponse(model_path, media_type="application/zip", filename=model_filename)


@app.get("/validate/{environment_name}")
async def validate_environment(environment_name: str):
    """Validate that an environment can be loaded and instantiated"""
    try:
        env_class = get_environment_class(environment_name)
        if env_class is None:
            return {
                "valid": False,
                "environment_name": environment_name,
                "error": "Environment class not found in registry"
            }
        
        # Try to instantiate
        try:
            env = env_class()
        except TypeError:
            try:
                env = env_class(max_steps=1000)
            except Exception as e:
                return {
                    "valid": False,
                    "environment_name": environment_name,
                    "error": f"Failed to instantiate: {str(e)}"
                }
        except Exception as e:
            return {
                "valid": False,
                "environment_name": environment_name,
                "error": f"Failed to instantiate: {str(e)}"
            }
        
        # Try to reset
        try:
            reset_result = env.reset()
            if isinstance(reset_result, tuple):
                state, info = reset_result
            else:
                state = reset_result
                info = {}
        except Exception as e:
            return {
                "valid": False,
                "environment_name": environment_name,
                "error": f"Failed to reset: {str(e)}"
            }
        
        # Try to take a step
        try:
            action = env.action_space.sample()
            step_result = env.step(action)
            if len(step_result) not in [4, 5]:
                return {
                    "valid": False,
                    "environment_name": environment_name,
                    "error": f"Step returned {len(step_result)} values, expected 4 or 5"
                }
        except Exception as e:
            return {
                "valid": False,
                "environment_name": environment_name,
                "error": f"Failed to step: {str(e)}"
            }
        
        return {
            "valid": True,
            "environment_name": environment_name,
            "observation_space": str(env.observation_space),
            "action_space": str(env.action_space),
            "message": "Environment is valid and ready for training"
        }
        
    except Exception as e:
        import traceback
        return {
            "valid": False,
            "environment_name": environment_name,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.get("/validate-all")
async def validate_all_environments():
    """Validate all environments can be loaded"""
    all_envs = list_all_environments()
    results = []
    
    for env_data in all_envs:
        env_name = env_data["name"]
        validation = await validate_environment(env_name)
        results.append(validation)
    
    valid_count = sum(1 for r in results if r.get("valid", False))
    failed_count = len(results) - valid_count
    
    return {
        "total": len(results),
        "valid": valid_count,
        "failed": failed_count,
        "results": results
    }


# ============================================================================
# VERIFIER ARCHITECTURE ENDPOINTS
# ============================================================================

@app.get("/verifiers")
async def list_verifiers():
    """List all available verifier types"""
    verifier_types = VerifierRegistry.list_verifier_types()
    instances = VerifierRegistry.list_instances()
    
    return {
        "verifier_types": verifier_types,
        "instances": instances,
        "count": len(instances)
    }


class VerifierConfigRequest(BaseModel):
    """Request model for verifier configuration"""
    verifier_type: str
    environment_name: str
    weights: Dict[str, float]
    thresholds: Optional[Dict[str, float]] = None
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


@app.post("/verifiers/configure")
async def configure_verifier(request: VerifierConfigRequest):
    """Configure a verifier for an environment"""
    try:
        config = VerifierConfig(
            weights=request.weights,
            thresholds=request.thresholds or {},
            enabled=request.enabled,
            metadata=request.metadata or {}
        )
        
        verifier = VerifierRegistry.create_verifier(
            verifier_type=request.verifier_type,
            config=config,
            instance_id=f"{request.environment_name}_{request.verifier_type}"
        )
        
        return {
            "success": True,
            "verifier_type": request.verifier_type,
            "environment_name": request.environment_name,
            "instance_id": f"{request.environment_name}_{request.verifier_type}",
            "config": {
                "weights": request.weights,
                "thresholds": request.thresholds,
                "enabled": request.enabled
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/episodes/{episode_id}/reward-breakdown")
async def get_reward_breakdown(episode_id: str):
    """Get reward breakdown for an episode"""
    # Find reward logger for this episode
    # In production, this would query the database
    for logger in reward_loggers.values():
        breakdown = logger.get_reward_breakdown(episode_id, 0)  # Get first step as example
        if breakdown:
            episode_logs = logger.get_episode_rewards(episode_id)
            return {
                "episode_id": episode_id,
                "total_steps": len(episode_logs),
                "reward_breakdowns": [
                    {
                        "step_id": log.step_id,
                        "reward": log.reward,
                        "breakdown": log.reward_breakdown,
                        "verifier": log.verifier_name
                    }
                    for log in episode_logs
                ],
                "summary": logger.get_episode_summary(episode_id)
            }
    
    raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")


@app.get("/episodes/{episode_id}/audit-log")
async def get_audit_log(episode_id: str):
    """Get audit log for an episode"""
    # Find audit logger for this episode
    for logger in audit_loggers.values():
        audit_log = logger.get_episode_audit_log(episode_id)
        if audit_log:
            return {
                "episode_id": episode_id,
                "events": [
                    {
                        "event_type": log.event_type.value,
                        "message": log.message,
                        "details": log.details,
                        "timestamp": log.timestamp.isoformat(),
                        "step_id": log.step_id
                    }
                    for log in audit_log
                ]
            }
    
    raise HTTPException(status_code=404, detail=f"Audit log for episode {episode_id} not found")


@app.get("/environments/{environment_name}/risk-report")
async def get_risk_report(environment_name: str):
    """Get risk report for an environment"""
    try:
        # Get risk thresholds
        risk_thresholds = RiskThresholds()
        
        # Get compliance violations
        compliance_rules = ComplianceRules()
        violations = compliance_rules.get_violations(environment_name=environment_name)
        
        return {
            "environment_name": environment_name,
            "risk_thresholds": {
                "max_risk_score": risk_thresholds.config.max_risk_score,
                "critical_threshold": risk_thresholds.config.critical_risk_threshold,
                "warning_threshold": risk_thresholds.config.warning_risk_threshold
            },
            "compliance_violations": {
                "total": len(violations),
                "by_severity": {
                    "critical": len([v for v in violations if v.get('severity') == 'critical']),
                    "error": len([v for v in violations if v.get('severity') == 'error']),
                    "warning": len([v for v in violations if v.get('severity') == 'warning'])
                },
                "recent_violations": violations[-10:] if len(violations) > 10 else violations
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GovernanceConfigRequest(BaseModel):
    """Request model for governance configuration"""
    environment_name: str
    max_risk_threshold: float = 0.8
    compliance_hard_stop: bool = True
    human_in_the_loop: bool = False
    override_actions: Optional[Dict[str, str]] = None


@app.post("/governance/configure")
async def configure_governance(request: GovernanceConfigRequest):
    """Configure governance settings for an environment"""
    try:
        safety_config = SafetyConfig(
            max_risk_threshold=request.max_risk_threshold,
            compliance_hard_stop=request.compliance_hard_stop,
            human_in_the_loop=request.human_in_the_loop,
            override_actions=request.override_actions or {}
        )
        
        governance_configs[request.environment_name] = {
            "safety_config": safety_config.__dict__,
            "environment_name": request.environment_name
        }
        
        return {
            "success": True,
            "environment_name": request.environment_name,
            "config": {
                "max_risk_threshold": request.max_risk_threshold,
                "compliance_hard_stop": request.compliance_hard_stop,
                "human_in_the_loop": request.human_in_the_loop
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/governance")
async def get_governance_configs():
    """Get all governance configurations"""
    return {
        "configs": governance_configs,
        "count": len(governance_configs)
    }


if __name__ == "__main__":
    # Allow port to be configured via environment variable (for cloud platforms)
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

