"""
FastAPI Backend for AgentWork Simulator
Provides endpoints for training, monitoring, and KPI retrieval
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uvicorn
import json
import os
import sys
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

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

app = FastAPI(title="RL Environment & Agent API", version="1.0.0")

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
    "http://127.0.0.1:8000",
    "https://ranikrishna-coder.github.io",
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

# ---------------------------------------------------------------------------
# MCP Agent – environment health, backups, tools
# ---------------------------------------------------------------------------
from api.mcp_agent import router as _agent_router, init_agent as _init_agent  # noqa: E402

app.include_router(_agent_router)

# Training jobs storage (in production, use database)
training_jobs: Dict[str, Dict[str, Any]] = {}  # Clean slate — populated by POST /train

# Observability storage (in production, use database)
reward_loggers: Dict[str, RewardLogger] = {}
action_trace_loggers: Dict[str, ActionTraceLogger] = {}
episode_metrics_trackers: Dict[str, EpisodeMetricsTracker] = {}
audit_loggers: Dict[str, AuditLogger] = {}

# Governance storage
governance_configs: Dict[str, Dict[str, Any]] = {}

# Rollout storage: { environment_name: [ rollout_dict, ... ] }
rollout_store: Dict[str, List[Dict[str, Any]]] = {}  # Clean slate — populated during training

_archived_seed_rollouts = {
    "JiraIssueResolution": [
        {
            "id": "bl_seed_001",
            "environment_name": "JiraIssueResolution",
            "episode_number": 0,
            "total_reward": 0.12,
            "total_steps": 3,
            "status": "completed",
            "source": "training",
            "policy_name": "qwen-1.7b-instruct",
            "checkpoint_label": "base",
            "scenario_name": "Resolve Jira ticket ISK2",
            "timestamp": "2026-01-16T08:00:00Z",
            "steps": [
                {"step": 1, "action": None, "reward": 0.02, "timeline_events": [
                    {"timestamp_ms": 0, "event_type": "SYSTEM", "content": "User request received: \"Resolve Jira ticket ISK2\""},
                    {"timestamp_ms": 412, "event_type": "MODEL_THOUGHT", "content": "Need to resolve the ticket."}
                ]},
                {"step": 2, "action": None, "reward": 0.05, "timeline_events": [
                    {"timestamp_ms": 913, "event_type": "MODEL_THOUGHT", "content": "Should check possible transitions."}
                ]},
                {"step": 3, "action": None, "reward": 0.05, "timeline_events": [
                    {"timestamp_ms": 1284, "event_type": "MODEL_THOUGHT", "content": "No further action taken."}
                ]},
            ],
            "final_outcome": {"reward": 0.12, "steps": 3, "resolved": False},
            "final_environment_state": {"issue_key": "ISK2", "status": "In Progress"},
            "verifier_results": [
                {"check": "Tool Sequence Validator", "passed": False, "detail": "No tool calls observed"},
                {"check": "Transition Validator", "passed": False, "detail": "transition_issue was never invoked"},
            ],
        },
        {
            "id": "tr_seed_001",
            "environment_name": "JiraIssueResolution",
            "episode_number": 287,
            "total_reward": 0.91,
            "total_steps": 3,
            "status": "completed",
            "source": "training",
            "policy_name": "qwen-1.7b-instruct",
            "checkpoint_label": "jira_grpo_step_300",
            "scenario_name": "Resolve Jira ticket ISK2",
            "timestamp": "2026-01-16T08:42:00Z",
            "steps": [
                {"step": 1, "action": "get_issue_summary_and_description", "reward": 0.15, "timeline_events": [
                    {"timestamp_ms": 0, "event_type": "SYSTEM", "content": "User request received: \"Resolve Jira ticket ISK2\""},
                    {"timestamp_ms": 88, "event_type": "TOOL_CALL", "tool_name": "get_issue_summary_and_description", "tool_args": {"issue_key": "ISK2"}},
                    {"timestamp_ms": 168, "event_type": "TOOL_RESULT", "content": "ISK-2: \"Login page error\" — Status: Open, Priority: High"},
                ]},
                {"step": 2, "action": "get_transitions", "reward": 0.20, "timeline_events": [
                    {"timestamp_ms": 248, "event_type": "TOOL_CALL", "tool_name": "get_transitions", "tool_args": {"issue_key": "ISK2"}},
                    {"timestamp_ms": 338, "event_type": "TOOL_RESULT", "content": "valid_transitions:\n  - id: 61\n    name: Done"},
                ]},
                {"step": 3, "action": "transition_issue", "reward": 0.56, "timeline_events": [
                    {"timestamp_ms": 418, "event_type": "TOOL_CALL", "tool_name": "transition_issue", "tool_args": {"issue_key": "ISK2", "transition_id": "61"}},
                    {"timestamp_ms": 508, "event_type": "TOOL_RESULT", "content": "Status changed: Open → Done"},
                ]},
            ],
            "final_outcome": {"reward": 0.91, "steps": 3, "resolved": True},
            "final_environment_state": {"issue_status": "Done", "resolution": "Fixed", "comments": 0},
            "verifier_results": [
                {"check": "Tool sequence order", "passed": True, "detail": "get_issue → get_transitions → transition_issue — correct order"},
                {"check": "Valid transitions only", "passed": True, "detail": "All transition_ids from get_transitions result"},
                {"check": "Issue resolved", "passed": True, "detail": "Issue moved to Done status"},
            ],
        },
    ],
    "TreatmentPathwayOptimization": [
        {
            "id": "bl_seed_003",
            "environment_name": "TreatmentPathwayOptimization",
            "episode_number": 0,
            "total_reward": 0.15,
            "total_steps": 3,
            "status": "completed",
            "source": "training",
            "policy_name": "mistral-7b-instruct-v0.3",
            "checkpoint_label": "base",
            "scenario_name": "Optimize treatment pathway",
            "timestamp": "2026-01-12T10:00:00Z",
            "steps": [
                {"step": 1, "action": None, "reward": 0.03, "timeline_events": [
                    {"timestamp_ms": 0, "event_type": "SYSTEM", "content": "Patient case loaded: chronic condition management"},
                    {"timestamp_ms": 350, "event_type": "MODEL_THOUGHT", "content": "Reviewing patient history for treatment options."},
                ]},
                {"step": 2, "action": None, "reward": 0.06, "timeline_events": [
                    {"timestamp_ms": 780, "event_type": "MODEL_THOUGHT", "content": "Multiple pathways available but unclear which to select."},
                ]},
                {"step": 3, "action": None, "reward": 0.06, "timeline_events": [
                    {"timestamp_ms": 1100, "event_type": "MODEL_THOUGHT", "content": "No treatment action taken — session ended."},
                ]},
            ],
            "final_outcome": {"reward": 0.15, "steps": 3, "resolved": False},
            "final_environment_state": {"pathway_status": "Incomplete", "interventions": 0},
            "verifier_results": [
                {"check": "Treatment Selection", "passed": False, "detail": "No treatment pathway selected"},
                {"check": "Protocol Compliance", "passed": False, "detail": "No clinical actions observed"},
            ],
        },
        {
            "id": "tr_seed_003",
            "environment_name": "TreatmentPathwayOptimization",
            "episode_number": 180,
            "total_reward": 0.78,
            "total_steps": 3,
            "status": "completed",
            "source": "training",
            "policy_name": "mistral-7b-instruct-v0.3",
            "checkpoint_label": "treatment_ppo_step_200",
            "scenario_name": "Optimize treatment pathway",
            "timestamp": "2026-01-12T11:30:00Z",
            "steps": [
                {"step": 1, "action": "get_patient_summary", "reward": 0.18, "timeline_events": [
                    {"timestamp_ms": 0, "event_type": "SYSTEM", "content": "Patient case loaded: chronic condition management"},
                    {"timestamp_ms": 95, "event_type": "TOOL_CALL", "tool_name": "get_patient_summary", "tool_args": {"patient_id": "PT-4421"}},
                    {"timestamp_ms": 180, "event_type": "TOOL_RESULT", "content": "Patient PT-4421: Age 58, Dx: Type 2 Diabetes, HbA1c: 8.2%"},
                ]},
                {"step": 2, "action": "list_treatment_options", "reward": 0.22, "timeline_events": [
                    {"timestamp_ms": 260, "event_type": "TOOL_CALL", "tool_name": "list_treatment_options", "tool_args": {"condition": "Type 2 Diabetes", "hba1c": 8.2}},
                    {"timestamp_ms": 350, "event_type": "TOOL_RESULT", "content": "Options: 1) Metformin + lifestyle, 2) Add GLP-1 agonist, 3) Insulin therapy"},
                ]},
                {"step": 3, "action": "select_pathway", "reward": 0.38, "timeline_events": [
                    {"timestamp_ms": 430, "event_type": "TOOL_CALL", "tool_name": "select_pathway", "tool_args": {"pathway": "Metformin + GLP-1 agonist", "rationale": "HbA1c > 7.5, oral therapy preferred"}},
                    {"timestamp_ms": 520, "event_type": "TOOL_RESULT", "content": "Treatment pathway selected and scheduled. Follow-up in 3 months."},
                ]},
            ],
            "final_outcome": {"reward": 0.78, "steps": 3, "resolved": True},
            "final_environment_state": {"pathway_status": "Active", "interventions": 2, "follow_up": "3 months"},
            "verifier_results": [
                {"check": "Treatment Selection", "passed": True, "detail": "Appropriate pathway selected for HbA1c level"},
                {"check": "Protocol Compliance", "passed": True, "detail": "All clinical guidelines followed"},
                {"check": "Patient Safety", "passed": True, "detail": "No contraindicated treatments selected"},
            ],
        },
    ],
}

# Seed rollout store with demo data for sample training runs
rollout_store.update({k: list(v) for k, v in _archived_seed_rollouts.items()})


class TrainingRequest(BaseModel):
    environment_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    algorithm: str = "PPO"
    model: Optional[str] = None
    num_episodes: int = 100
    max_steps: int = 1000
    dataset_url: Optional[str] = None
    verifier_config: Optional[Dict[str, Any]] = None  # Verifier configuration
    run_name: Optional[str] = None
    category: Optional[str] = None  # Environment category (jira, clinical, etc.)


class TrainingResponse(BaseModel):
    job_id: str
    status: str
    environment_name: str
    message: str


class RolloutStepData(BaseModel):
    """Single step within a rollout."""
    step: int
    action: Any = None
    reward: float = 0.0
    state_summary: Optional[Dict[str, Any]] = None
    reward_breakdown: Optional[Dict[str, float]] = None
    timeline_events: Optional[List[Dict[str, Any]]] = None


class RolloutRecord(BaseModel):
    """A complete rollout (episode run) for an environment."""
    environment_name: str
    episode_number: int = 1
    steps: List[RolloutStepData] = []
    initial_state: Optional[Dict[str, Any]] = None
    final_outcome: Optional[Dict[str, Any]] = None
    total_reward: float = 0.0
    total_steps: int = 0
    status: str = "completed"  # completed | failed | in_progress
    source: str = "simulation"  # simulation | training
    job_id: Optional[str] = None
    timestamp: Optional[str] = None
    policy_name: Optional[str] = None
    checkpoint_label: Optional[str] = None
    scenario_name: Optional[str] = None
    verifier_results: Optional[List[Dict[str, Any]]] = None
    final_environment_state: Optional[Dict[str, Any]] = None



@app.get("/")
async def root():
    """Root endpoint - serves the landing page"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    landing_path = os.path.join(static_dir, "landing.html")
    if os.path.exists(landing_path):
        return FileResponse(landing_path)
    return {"message": "RL Environment & Agent API", "version": "1.0.0"}


@app.get("/environments")
async def environments_page():
    """Environments UI - user journey: Industry → Persona → RL environments"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Environments page not found")



@app.get("/training-console")
async def training_console_page():
    """Serve the Training Console UI."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    path = os.path.join(static_dir, "training.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Training console not found")


@app.get("/contact")
async def contact_page():
    """Serve the Contact us page (form only)."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    path = os.path.join(static_dir, "contact.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Contact page not found")


@app.get("/agent-dashboard")
async def agent_dashboard_page():
    """Serve the MCP Agent Health Dashboard."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    path = os.path.join(static_dir, "agent-dashboard.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Agent dashboard not found")

@app.get("/agent-console")
async def agent_console_page():
    """Serve the Agent Console page."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    path = os.path.join(static_dir, "agent.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Agent console not found")


# Legacy: redirect old references
@app.get("/index.html")
async def index_redirect():
    """Redirect to environments"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/environments", status_code=302)


@app.get("/catalog")
async def catalog_redirect():
    """Redirect old /catalog URL to /environments"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/environments", status_code=301)


@app.get("/api")
async def api_info():
    return {
        "message": "RL Environment & Agent API",
        "version": "1.0.0",
        "endpoints": {
            "landing": "/",
            "simulation_console": "/test-console",
            "studio": "/studio",
            "environments_page": "/environments",
            "environments_api": "/api/environments",
            "scenarios_api": "/api/scenarios",
            "jira_mock_data": "/jira-mock-data",
            "train": "/train/{environment_name}",
            "kpis": "/kpis/{environment_name}",
            "training_status": "/training/{job_id}",
            "validate": "/validate/{environment_name}",
            "validate_all": "/validate-all",
            "download_model": "/models/{algorithm}/{model_filename}"
        }
    }


# ---------- Contact form: save to DB + email ----------

CONTACT_EMAIL_TO = "kausalyarani.k@centific.com"


def _contact_db_path() -> str:
    p = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(p, exist_ok=True)
    return os.path.join(p, "contact_submissions.db")


def _init_contact_db() -> None:
    with sqlite3.connect(_contact_db_path()) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contact_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                organization TEXT NOT NULL,
                subject TEXT,
                use_case TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


class ContactSubmissionRequest(BaseModel):
    name: str
    email: str
    organization: str
    subject: Optional[str] = None
    use_case: str


def _send_contact_email(sub: ContactSubmissionRequest) -> None:
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("CONTACT_EMAIL_FROM", user or "noreply@agentwork.local").strip()
    if not host and not user:
        return
    try:
        body = f"""Name: {sub.name}
Email: {sub.email}
Organization: {sub.organization}
Subject: {sub.subject or '(not provided)'}

Describe your use case:
{sub.use_case}
"""
        msg = MIMEMultipart()
        msg["Subject"] = f"RL Environment & Agent contact: {sub.name} ({sub.organization})"
        msg["From"] = from_addr
        msg["To"] = CONTACT_EMAIL_TO
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(host, port) as server:
            if user and password:
                server.starttls()
                server.login(user, password)
            server.sendmail(from_addr, [CONTACT_EMAIL_TO], msg.as_string())
    except Exception:
        pass


@app.post("/api/contact")
async def api_contact_submit(body: ContactSubmissionRequest, background_tasks: BackgroundTasks):
    """Save contact form to DB and send email to kausalyarani.k@centific.com."""
    name = (body.name or "").strip()
    email = (body.email or "").strip()
    organization = (body.organization or "").strip()
    use_case = (body.use_case or "").strip()
    if not name or not email or not organization or not use_case:
        raise HTTPException(
            status_code=400,
            detail="name, email, organization, and use case are required",
        )
    created_at = datetime.utcnow().isoformat() + "Z"
    _init_contact_db()
    with sqlite3.connect(_contact_db_path()) as conn:
        conn.execute(
            """INSERT INTO contact_submissions (name, email, organization, subject, use_case, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, email, organization, body.subject or "", use_case, created_at),
        )
    background_tasks.add_task(_send_contact_email, body)
    return {"ok": True, "message": "Thank you. Your message has been submitted."}


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
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="The 'requests' library is required for Jira API calls. Install with: pip install requests"
        ) from e
    try:
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
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="The 'requests' library is required for Jira API calls. Install with: pip install requests"
        ) from e
    try:
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
    api_url = os.getenv("API_URL", "")
    
    # If API_URL is not set, try to construct from request
    # This will be handled by the JavaScript auto-detection
    
    config_content = f"""// API Configuration
// This can be overridden by setting window.API_BASE before loading app.js
window.API_BASE = window.API_BASE || '{api_url}';
console.log('🚀 RL Environment & Agent - API Base URL:', window.API_BASE);
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


@app.get("/api/environments")
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


def _build_step_timeline(action, reward: float, transition_info: dict, step_idx: int) -> list:
    """Build rich timeline events from env transition_info for rollout comparison.

    Uses ``event_type`` / ``content`` keys to match the mock-data format that
    rollout-comparison.js already renders.
    """
    events: list[dict] = []
    tool_used = transition_info.get("tool_used")
    valid_step = transition_info.get("valid_step", False)
    issue_key = transition_info.get("current_issue_key")
    # Approximate timestamp (ms) using step index
    ts_base = (step_idx - 1) * 400

    if tool_used:
        # Named tool call
        args = {}
        if issue_key:
            args["issue_key"] = issue_key
        tids = transition_info.get("valid_transition_ids")
        if tool_used == "transition_issue" and tids:
            args["transition_id"] = str(tids[0]) if tids else ""
        events.append({
            "timestamp_ms": ts_base,
            "event_type": "TOOL_CALL",
            "tool_name": tool_used,
            "tool_args": args,
            "content": tool_used,
        })
        # Result
        if valid_step:
            result_content = f"Step {step_idx} completed: {tool_used}"
            achieved = transition_info.get("achieved_status")
            if achieved:
                result_content += f" → status: {achieved}"
        else:
            result_content = f"Invalid step: {tool_used} (wrong order)"
        events.append({
            "timestamp_ms": ts_base + 200,
            "event_type": "TOOL_RESULT",
            "content": result_content,
        })
    else:
        # Numeric action (no tool mapping available)
        events.append({"timestamp_ms": ts_base, "event_type": "TOOL_CALL", "content": f"action={action}"})
        events.append({"timestamp_ms": ts_base + 200, "event_type": "TOOL_RESULT", "content": f"reward={reward:.4f}"})
    return events


def _build_final_env_state(env, info: dict, environment_name: str) -> Optional[dict]:
    """Extract final environment state from the last step info."""
    ti = info.get("transition_info", {})
    state: dict = {}
    # Jira-specific fields
    issue_key = ti.get("current_issue_key")
    if issue_key:
        state["issue_key"] = issue_key
    tool_seq = ti.get("tool_sequence_after", [])
    if tool_seq:
        state["tool_sequence"] = tool_seq
    achieved = ti.get("achieved_status")
    if achieved:
        state["status"] = achieved
    resolved = ti.get("valid_step") and ti.get("tool_used") in ("transition_issue", "create_subtask")
    if "issue_key" in state:
        state["resolved"] = bool(resolved)
    # KPI info
    kpis = info.get("kpis", {})
    eff = kpis.get("operational_efficiency", {})
    if eff:
        state["steps_completed"] = eff.get("steps_completed", 0)
        state["expected_steps"] = eff.get("expected_steps", 0)
    return state if state else None


def _build_verifier_results(env, info: dict, environment_name: str) -> Optional[list]:
    """Build verifier results from the final episode info."""
    ti = info.get("transition_info", {})
    tool_seq = ti.get("tool_sequence_after", [])
    expected_order = getattr(env, "_expected_order", None)
    if not expected_order:
        return None
    results = []
    # Check 1: Tool sequence order
    seq_correct = tool_seq == expected_order[:len(tool_seq)] and len(tool_seq) >= len(expected_order)
    results.append({
        "check": "Tool sequence order",
        "passed": seq_correct,
        "detail": " → ".join(tool_seq) + (" — correct order" if seq_correct else " — incomplete or wrong order")
    })
    # Check 2: Valid transitions
    has_transition = "transition_issue" in tool_seq
    results.append({
        "check": "Valid transitions only",
        "passed": has_transition and ti.get("valid_step", False),
        "detail": "transition_issue invoked" if has_transition else "transition_issue was never invoked"
    })
    # Check 3: Issue resolved
    resolved = ti.get("achieved_status") in ("Done", "Resolved", "Closed") or (
        ti.get("tool_used") in ("transition_issue", "create_subtask") and ti.get("valid_step", False)
    )
    results.append({
        "check": "Issue resolved",
        "passed": resolved,
        "detail": f"Status: {ti.get('achieved_status', 'unknown')}" if resolved else "Issue not resolved"
    })
    return results


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
        
        # Store job info (include verifier_config so we can require human eval when type is human_evaluation)
        _hil_required = (req.verifier_config or {}).get("type") == "human_evaluation"
        training_jobs[job_id] = {
            "job_id": job_id,
            "environment_name": final_env_name,
            "run_name": req.run_name or "",
            "category": req.category or "",
            "status": "running",
            "algorithm": req.algorithm,
            "model": req.model or "",
            "num_episodes": req.num_episodes,
            "progress": 0,
            "results": None,
            "model_path": model_path,
            "model_url": f"/models/{req.algorithm.lower()}/{model_filename}",
            "dataset_url": req.dataset_url,
            "verifier_config": req.verifier_config,
            "hil_required": _hil_required,
            "started_at": datetime.now().isoformat(),
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
            # Jira environments: use Jira verifier from workflow_definitions
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
                # Human evaluation: use ensemble for in-loop rewards; final gate is human eval after training
                if verifier_type == "human_evaluation":
                    verifier_type = "ensemble"
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

        # Pre-training baseline: run a few episodes with random policy for comparison
        baseline_episodes = min(5, max(1, num_episodes // 20))
        baseline_rewards: list[float] = []
        _baseline_steps: list[Dict[str, Any]] = []
        try:
            for be in range(baseline_episodes):
                reset_result = env.reset(seed=1000 + be)
                if isinstance(reset_result, tuple):
                    state, _ = reset_result
                else:
                    state = reset_result
                ep_rew = 0.0
                _bl_step_idx = 0
                _bl_last_info: Dict[str, Any] = {}
                for _ in range(max_steps):
                    action = env.action_space.sample()
                    step_result = env.step(action)
                    if len(step_result) == 5:
                        state, reward, terminated, truncated, _bl_info = step_result
                    else:
                        state, reward, done, _bl_info = step_result
                        terminated = done
                        truncated = False
                    _bl_last_info = _bl_info if isinstance(_bl_info, dict) else {}
                    ep_rew += float(reward)
                    _bl_step_idx += 1
                    # Capture per-step data for the first baseline episode only
                    if be == 0:
                        _bl_ti = _bl_last_info.get("transition_info", {})
                        _bl_events = _build_step_timeline(action, float(reward), _bl_ti, _bl_step_idx)
                        # Add SYSTEM event on first step
                        if _bl_step_idx == 1:
                            _issue_key = _bl_ti.get("current_issue_key", "")
                            _sys_msg = f"Environment: {environment_name}"
                            if _issue_key:
                                _sys_msg = f"Task: Resolve {_issue_key} in {environment_name}"
                            _bl_events.insert(0, {"timestamp_ms": 0, "event_type": "SYSTEM", "content": _sys_msg})
                        _baseline_steps.append({
                            "step": _bl_step_idx,
                            "action": _bl_ti.get("tool_used") or (int(action) if hasattr(action, '__int__') else action),
                            "reward": float(reward),
                            "state_summary": None,
                            "reward_breakdown": None,
                            "timeline_events": _bl_events,
                        })
                    if terminated or truncated:
                        break
                baseline_rewards.append(ep_rew)
            if baseline_rewards:
                training_jobs[job_id]["baseline_results"] = {
                    "mean_reward": sum(baseline_rewards) / len(baseline_rewards),
                    "max_reward": max(baseline_rewards),
                    "min_reward": min(baseline_rewards),
                    "episodes": len(baseline_rewards),
                }
            # Store a rich baseline rollout entry for comparison
            if _baseline_steps:
                import uuid as _uuid_bl
                from datetime import timezone as _tz_bl
                _baseline_rollout = {
                    "id": str(_uuid_bl.uuid4()),
                    "environment_name": environment_name,
                    "episode_number": 0,
                    "total_reward": baseline_rewards[0] if baseline_rewards else 0.0,
                    "total_steps": len(_baseline_steps),
                    "status": "completed",
                    "source": "training",
                    "job_id": job_id,
                    "timestamp": datetime.now(_tz_bl.utc).isoformat().replace("+00:00", "Z"),
                    "steps": _baseline_steps,
                    "initial_state": None,
                    "final_outcome": {"reward": baseline_rewards[0] if baseline_rewards else 0.0, "steps": len(_baseline_steps)},
                    "policy_name": "Random Baseline",
                    "checkpoint_label": "base",
                    "scenario_name": None,
                    "verifier_results": _build_verifier_results(env, _bl_last_info, environment_name),
                    "final_environment_state": _build_final_env_state(env, _bl_last_info, environment_name),
                }
                if environment_name not in rollout_store:
                    rollout_store[environment_name] = []
                rollout_store[environment_name].append(_baseline_rollout)
                training_jobs[job_id]["baseline_rollout_id"] = _baseline_rollout["id"]
        except Exception as e:
            print(f"Baseline run skipped: {e}")
            training_jobs[job_id]["baseline_results"] = None

        # Jira policy via model endpoint when algorithm is SLM (no local model; set JIRA_MODEL_ENDPOINT)
        jira_slm_policy = None
        JIRA_ENVS_FOR_SLM = ("JiraIssueResolution", "JiraStatusUpdate", "JiraCommentManagement", "JiraSubtaskManagement")
        if algorithm.upper() == "SLM" and environment_name in JIRA_ENVS_FOR_SLM and hasattr(env, "_expected_order"):
            try:
                from policies.jira_slm_policy import JiraSLMPolicy
                jira_slm_policy = JiraSLMPolicy(env._expected_order)
            except Exception as e:
                print(f"Warning: Jira policy creation failed: {e}. Using random actions.")

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
                _sampled_steps: list[Dict[str, Any]] = []

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

                    # Capture per-step data for sampled episodes
                    _sample_interval_check = max(1, num_episodes // 10)
                    if episode == 0 or episode == num_episodes - 1 or (episode + 1) % _sample_interval_check == 0:
                        _step_info = info if isinstance(info, dict) else {}
                        _step_ti = _step_info.get("transition_info", {})
                        _step_events = _build_step_timeline(action, float(reward), _step_ti, episode_steps)
                        # Add SYSTEM event on first step
                        if episode_steps == 1:
                            _issue_key = _step_ti.get("current_issue_key", "")
                            _sys_msg = f"Environment: {environment_name}"
                            if _issue_key:
                                _sys_msg = f"Task: Resolve {_issue_key} in {environment_name}"
                            _step_events.insert(0, {"timestamp_ms": 0, "event_type": "SYSTEM", "content": _sys_msg})
                        _sampled_steps.append({
                            "step": episode_steps,
                            "action": _step_ti.get("tool_used") or (int(action) if hasattr(action, '__int__') else action),
                            "reward": float(reward),
                            "state_summary": None,
                            "reward_breakdown": None,
                            "timeline_events": _step_events,
                        })

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

                # Store rollout for sampled episodes (first, last, every 10th)
                _sample_interval = max(1, num_episodes // 10)
                if episode == 0 or episode == num_episodes - 1 or (episode + 1) % _sample_interval == 0:
                    import uuid as _uuid
                    from datetime import timezone as _tz
                    _rollout_entry = {
                        "id": str(_uuid.uuid4()),
                        "environment_name": environment_name,
                        "episode_number": episode + 1,
                        "total_reward": episode_reward,
                        "total_steps": step + 1,
                        "status": "completed",
                        "source": "training",
                        "job_id": job_id,
                        "timestamp": datetime.now(_tz.utc).isoformat().replace("+00:00", "Z"),
                        "steps": _sampled_steps,
                        "initial_state": None,
                        "final_outcome": {"reward": episode_reward, "steps": step + 1},
                        "policy_name": algorithm,
                        "checkpoint_label": f"step_{episode+1}",
                        "scenario_name": None,
                        "verifier_results": _build_verifier_results(env, info if isinstance(info, dict) else {}, environment_name),
                        "final_environment_state": _build_final_env_state(env, info if isinstance(info, dict) else {}, environment_name),
                    }
                    if environment_name not in rollout_store:
                        rollout_store[environment_name] = []
                    rollout_store[environment_name].append(_rollout_entry)
                    # Cap at 100 rollouts per environment
                    if len(rollout_store[environment_name]) > 100:
                        rollout_store[environment_name] = rollout_store[environment_name][-100:]
                    # Save the last stored rollout as the trained rollout for comparison
                    training_jobs[job_id]["trained_rollout_id"] = _rollout_entry["id"]

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
        
        # Store results; if verifier is human_evaluation, wait for human eval before marking completed
        job = training_jobs[job_id]
        job["results"] = {
            "mean_reward": mean_reward,
            "max_reward": max_reward,
            "min_reward": min_reward,
            "total_episodes": num_episodes,
            "episodes_completed": len(total_rewards)
        }
        job["model_saved"] = True
        job["model_metadata"] = model_metadata

        requires_human_eval = (job.get("verifier_config") or {}).get("type") == "human_evaluation"
        if requires_human_eval:
            job["status"] = "awaiting_human_eval"
        else:
            job["status"] = "completed"

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


@app.get("/api/training/jobs")
async def list_training_jobs():
    """Return all training jobs (summary view for the training runs table)."""
    jobs = []
    for jid, job in training_jobs.items():
        jobs.append({
            "job_id": jid,
            "run_name": job.get("run_name", ""),
            "status": job.get("status", "unknown"),
            "environment_name": job.get("environment_name", ""),
            "category": job.get("category", ""),
            "algorithm": job.get("algorithm", ""),
            "model": job.get("model", ""),
            "progress": job.get("progress", 0),
            "results": job.get("results"),
            "baseline_results": job.get("baseline_results"),
            "hil_required": job.get("hil_required", False),
            "model_saved": job.get("model_saved", False),
            "model_url": job.get("model_url"),
            "model_metadata": job.get("model_metadata"),
            "started_at": job.get("started_at"),
            "error": job.get("error"),
        })
    return {"jobs": jobs}


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

    from datetime import datetime, timezone

    entry = {
        "decision": decision_normalized,
        "comments": req.comments or "",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if req.step_scores:
        entry["step_scores"] = [{"step_index": s.step_index, "score": s.score} for s in req.step_scores]

    # Append to per-job human evaluations list
    evals = job.get("human_evaluations") or []
    evals.append(entry)
    job["human_evaluations"] = evals
    # Store latest for quick access
    job["last_human_evaluation"] = entry

    # If job was awaiting human eval, training is now complete; store human eval on job so model output reflects it
    if job.get("status") == "awaiting_human_eval":
        job["status"] = "completed"
        job["human_eval_decision"] = entry["decision"]
        job["human_eval_completed_at"] = entry["timestamp"]

    return {
        "success": True,
        "job_id": job_id,
        "evaluation": entry,
        "total_evaluations": len(evals),
        "training_completed": job.get("status") == "completed",
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
# VERIFIER ARCHITECTURE ENDPOINTS (CRUD + lifecycle)
# ============================================================================

# In-memory verifier definitions store (seeded from frontend verifier-data.js schema)
_verifier_store: Dict[str, dict] = {}


class VerifierDefinition(BaseModel):
    """Verifier definition model"""
    id: Optional[str] = None
    name: str
    type: str  # rule-based, trajectory-based, llm-judge
    system: str
    environment: str
    version: int = 1
    status: str = "active"
    used_in_scenarios: list = []
    description: str = ""
    metadata: dict = {}
    logic: dict = {}
    example_input: dict = {}
    example_output: dict = {}
    failure_policy: dict = {"hard_fail": False, "penalty": 0.0, "log_failure": True}


class VerifierConfigRequest(BaseModel):
    """Request model for verifier configuration (legacy compat)"""
    verifier_type: str
    environment_name: str
    weights: Dict[str, float]
    thresholds: Optional[Dict[str, float]] = None
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


@app.get("/api/verifiers")
async def list_verifier_definitions(system: Optional[str] = None, type: Optional[str] = None):
    """List all verifier definitions with optional system/type filters"""
    verifiers = list(_verifier_store.values())
    if system:
        verifiers = [v for v in verifiers if v.get("system", "").lower() == system.lower()]
    if type:
        verifiers = [v for v in verifiers if v.get("type", "").lower() == type.lower()]
    return {"verifiers": verifiers, "count": len(verifiers)}


@app.get("/api/verifiers/{verifier_id}")
async def get_verifier_definition(verifier_id: str):
    """Get a single verifier by ID"""
    v = _verifier_store.get(verifier_id)
    if not v:
        raise HTTPException(status_code=404, detail=f"Verifier {verifier_id} not found")
    return v


@app.post("/api/verifiers")
async def create_verifier_definition(request: VerifierDefinition):
    """Create a new verifier definition"""
    import uuid
    vid = request.id or f"custom-{uuid.uuid4().hex[:12]}"
    vdata = request.dict()
    vdata["id"] = vid
    vdata["version"] = 1
    vdata["status"] = "active"
    _verifier_store[vid] = vdata
    return {"success": True, "verifier": vdata}


@app.put("/api/verifiers/{verifier_id}")
async def edit_verifier_definition(verifier_id: str, request: VerifierDefinition):
    """Edit a verifier (creates new immutable version with verifier_version++)"""
    existing = _verifier_store.get(verifier_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Verifier {verifier_id} not found")
    vdata = request.dict()
    vdata["id"] = verifier_id
    vdata["version"] = existing.get("version", 1) + 1
    _verifier_store[verifier_id] = vdata
    return {"success": True, "verifier": vdata}


@app.post("/api/verifiers/{verifier_id}/duplicate")
async def duplicate_verifier(verifier_id: str):
    """Duplicate a verifier (new verifier_id, seeded from existing config)"""
    import uuid
    existing = _verifier_store.get(verifier_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Verifier {verifier_id} not found")
    new_id = f"dup-{uuid.uuid4().hex[:12]}"
    new_v = dict(existing)
    new_v["id"] = new_id
    new_v["name"] = existing.get("name", "") + " (Copy)"
    new_v["version"] = 1
    _verifier_store[new_id] = new_v
    return {"success": True, "verifier": new_v}


@app.patch("/api/verifiers/{verifier_id}/disable")
async def disable_verifier(verifier_id: str):
    """Disable a verifier (prevents selection in new runs, preserves history)"""
    existing = _verifier_store.get(verifier_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Verifier {verifier_id} not found")
    current_status = existing.get("status", "active")
    new_status = "disabled" if current_status == "active" else "active"
    existing["status"] = new_status
    return {"success": True, "verifier_id": verifier_id, "status": new_status}


# Legacy endpoints (backward compatible)
@app.get("/verifiers")
async def list_verifiers_legacy():
    """List all available verifier types (legacy)"""
    verifier_types = VerifierRegistry.list_verifier_types()
    instances = VerifierRegistry.list_instances()
    return {"verifier_types": verifier_types, "instances": instances, "count": len(instances)}


@app.post("/verifiers/configure")
async def configure_verifier(request: VerifierConfigRequest):
    """Configure a verifier for an environment (legacy)"""
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
            "config": {"weights": request.weights, "thresholds": request.thresholds, "enabled": request.enabled}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# ROLLOUT ENDPOINTS (episode runs per environment)
# ============================================================================


@app.post("/api/rollouts")
async def store_rollout(rollout: RolloutRecord):
    """Store a rollout (episode run) for an environment."""
    import uuid as _uuid
    from datetime import timezone as _tz

    entry = rollout.dict()
    entry["id"] = str(_uuid.uuid4())
    entry["timestamp"] = entry.get("timestamp") or datetime.now(_tz.utc).isoformat().replace("+00:00", "Z")

    env_name = rollout.environment_name
    if env_name not in rollout_store:
        rollout_store[env_name] = []
    rollout_store[env_name].append(entry)

    # Cap at 100 rollouts per environment
    if len(rollout_store[env_name]) > 100:
        rollout_store[env_name] = rollout_store[env_name][-100:]

    return {"success": True, "id": entry["id"], "environment_name": env_name}


@app.get("/api/rollouts-all")
async def get_all_rollouts(environment_name: Optional[str] = None, limit: int = 50, offset: int = 0):
    """Get rollouts across all (or one) environment. Returns summaries for list view."""
    all_rollouts = []
    sources = rollout_store.items()
    if environment_name:
        sources = [(environment_name, rollout_store.get(environment_name, []))]
    for env_name, env_rollouts in sources:
        for r in env_rollouts:
            ti = (r.get("steps") or [{}])[-1] if r.get("steps") else {}
            last_events = ti.get("timeline_events", [])
            tool_calls = sum(1 for e in last_events if e.get("event_type") == "TOOL_CALL")
            for s in (r.get("steps") or [])[:-1]:
                tool_calls += sum(1 for e in s.get("timeline_events", []) if e.get("event_type") == "TOOL_CALL")
            fs = r.get("final_environment_state") or {}
            final_state_label = fs.get("status") or fs.get("issue_status") or ("Resolved" if fs.get("resolved") else "")
            if not final_state_label and (r.get("final_outcome") or {}).get("resolved"):
                final_state_label = "Resolved"
            all_rollouts.append({
                "id": r["id"],
                "environment_name": env_name,
                "episode_number": r.get("episode_number", 0),
                "total_reward": round(r.get("total_reward", 0.0), 2),
                "total_steps": r.get("total_steps", 0),
                "tool_calls": tool_calls,
                "status": r.get("status", "completed"),
                "source": r.get("source", "simulation"),
                "policy_name": r.get("policy_name", ""),
                "checkpoint_label": r.get("checkpoint_label", ""),
                "final_state": final_state_label or "N/A",
                "duration_s": round(r.get("total_steps", 0) * 0.7, 1),
                "timestamp": r.get("timestamp"),
                "job_id": r.get("job_id"),
                "issue_key": fs.get("issue_key", ""),
            })
    all_rollouts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    total = len(all_rollouts)
    page = all_rollouts[offset:offset + limit]
    env_names = sorted(rollout_store.keys())
    return {"rollouts": page, "total": total, "environments": env_names}


@app.get("/api/rollouts/{environment_name}")
async def get_rollouts(environment_name: str, limit: int = 20, offset: int = 0):
    """Get rollouts (episode runs) for an environment. Returns summaries (no per-step data)."""
    rollouts = rollout_store.get(environment_name, [])
    rollouts_sorted = sorted(rollouts, key=lambda r: r.get("timestamp", ""), reverse=True)
    page = rollouts_sorted[offset:offset + limit]
    summaries = []
    for r in page:
        summaries.append({
            "id": r["id"],
            "episode_number": r.get("episode_number", 0),
            "total_reward": r.get("total_reward", 0.0),
            "total_steps": r.get("total_steps", 0),
            "status": r.get("status", "completed"),
            "source": r.get("source", "simulation"),
            "timestamp": r.get("timestamp"),
            "job_id": r.get("job_id"),
        })
    return {"environment_name": environment_name, "rollouts": summaries, "total": len(rollouts)}


@app.get("/api/rollouts/{environment_name}/{rollout_id}")
async def get_rollout_detail(environment_name: str, rollout_id: str):
    """Get full rollout detail including step-by-step data."""
    rollouts = rollout_store.get(environment_name, [])
    rollout = next((r for r in rollouts if r["id"] == rollout_id), None)
    if not rollout:
        raise HTTPException(status_code=404, detail="Rollout not found")
    return rollout


@app.get("/api/rollout-comparison/{environment_name}")
async def get_rollout_comparison(
    environment_name: str,
    baseline_id: Optional[str] = None,
    trained_id: Optional[str] = None,
    job_id: Optional[str] = None
):
    """Get two rollouts for side-by-side comparison."""
    rollouts = rollout_store.get(environment_name, [])

    if job_id:
        job = training_jobs.get(job_id)
        if job:
            baseline_id = baseline_id or job.get("baseline_rollout_id")
            trained_id = trained_id or job.get("trained_rollout_id")

    baseline = next((r for r in rollouts if r["id"] == baseline_id), None) if baseline_id else None
    trained = next((r for r in rollouts if r["id"] == trained_id), None) if trained_id else None

    # Fallback: find most recent baseline and trained rollouts
    if not baseline:
        for r in reversed(rollouts):
            if r.get("checkpoint_label") == "base" or r.get("episode_number") == 0:
                baseline = r
                break
    if not trained:
        for r in reversed(rollouts):
            if r.get("source") == "training" and r.get("checkpoint_label") != "base" and r.get("episode_number", 0) > 0:
                trained = r
                break

    return {
        "environment_name": environment_name,
        "baseline": baseline,
        "trained": trained,
    }


@app.get("/human-eval")
async def human_eval_page():
    """Serve the HITL evaluation console."""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    path = os.path.join(static_dir, "human-eval.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Human eval page not found")


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


# ---------- HuggingFace Integration ----------

import urllib.request
import urllib.error
import shutil
import subprocess as _subprocess

# Directory for cloned HF spaces
HF_SPACES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hf_spaces")

# ---------------------------------------------------------------------------
# Persistent environment store  (SQLite – survives git reset --hard deploys)
# ---------------------------------------------------------------------------
_CUSTOM_ENV_STORE_PATH = os.path.join(os.path.dirname(__file__), "data", "custom_environments.json")

from api.persistence import EnvironmentStore, ScenarioStore, migrate_json_to_sqlite  # noqa: E402
from api.config import ENV_STORE_DB_PATH, SCENARIO_STORE_DB_PATH  # noqa: E402

_env_store = EnvironmentStore(ENV_STORE_DB_PATH)
_scenario_store = ScenarioStore(SCENARIO_STORE_DB_PATH)
_migrated = migrate_json_to_sqlite(_CUSTOM_ENV_STORE_PATH, _env_store)


def _load_persisted_environments() -> List[Dict[str, Any]]:
    """Load custom environments from the SQLite store."""
    return _env_store.list_all()


def _persist_environments() -> None:
    """Sync in-memory custom_environments list to the SQLite store."""
    for env in custom_environments:
        name = env.get("name")
        if name:
            _env_store.upsert(name, env)


def _remove_persisted_environment(name: str) -> None:
    """Remove a single environment from the SQLite store."""
    _env_store.delete(name)


# Load previously saved environments on startup
custom_environments: List[Dict[str, Any]] = _load_persisted_environments()


class HuggingFaceImportRequest(BaseModel):
    name: str
    description: Optional[str] = None
    hf_url: str
    hf_owner: str
    hf_repo: str


@app.get("/api/huggingface/space-info")
async def get_huggingface_space_info(owner: str, repo: str):
    """Fetch metadata about a HuggingFace Space via the HF API."""
    hf_api_url = f"https://huggingface.co/api/spaces/{owner}/{repo}"
    try:
        req = urllib.request.Request(hf_api_url, headers={"User-Agent": "AgentWork-Simulator/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        return {
            "id": data.get("id", f"{owner}/{repo}"),
            "owner": owner,
            "repo": repo,
            "author": data.get("author", owner),
            "sdk": data.get("sdk", "unknown"),
            "license": data.get("cardData", {}).get("license", data.get("license", None)),
            "tags": data.get("tags", []),
            "likes": data.get("likes", 0),
            "last_modified": data.get("lastModified"),
            "private": data.get("private", False),
            "disabled": data.get("disabled", False),
        }
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise HTTPException(status_code=404, detail=f"Space '{owner}/{repo}' not found on HuggingFace.")
        raise HTTPException(status_code=exc.code, detail=f"HuggingFace API error (HTTP {exc.code})")
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to reach HuggingFace API: {str(exc.reason)}")


@app.post("/api/huggingface/import")
async def import_huggingface_space(req: HuggingFaceImportRequest, background_tasks: BackgroundTasks):
    """
    Import a HuggingFace Space by downloading files via the HF API.
    No git dependency required — uses HTTP to fetch the file tree and download each file.
    """
    # Validate URL
    if "huggingface.co/spaces/" not in req.hf_url:
        raise HTTPException(status_code=400, detail="Invalid HuggingFace Space URL.")

    # Check for duplicate name
    existing_names = [e["name"] for e in custom_environments]
    if req.name in existing_names:
        raise HTTPException(status_code=409, detail=f"Environment '{req.name}' already exists.")

    os.makedirs(HF_SPACES_DIR, exist_ok=True)
    target_dir = os.path.join(HF_SPACES_DIR, req.name)

    # Download files via HuggingFace API (no git required)
    api_tree_url = f"https://huggingface.co/api/spaces/{req.hf_owner}/{req.hf_repo}/tree/main"
    headers = {"User-Agent": "AgentWork-Simulator/1.0"}
    try:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        os.makedirs(target_dir, exist_ok=True)

        # Fetch file tree from HF API
        tree_req = urllib.request.Request(api_tree_url, headers=headers)
        with urllib.request.urlopen(tree_req, timeout=30) as resp:
            tree = json.loads(resp.read().decode())

        # Download each file (skip LFS blobs > 10MB, skip directories)
        max_file_size = 10 * 1024 * 1024  # 10MB limit per file
        for item in tree:
            if item.get("type") != "file":
                continue
            rpath = item.get("path", "")
            size = item.get("size", 0)
            if size > max_file_size:
                continue  # Skip large LFS files
            file_url = f"https://huggingface.co/spaces/{req.hf_owner}/{req.hf_repo}/resolve/main/{rpath}"
            local_path = os.path.join(target_dir, rpath)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            dl_req = urllib.request.Request(file_url, headers=headers)
            try:
                with urllib.request.urlopen(dl_req, timeout=60) as dl_resp:
                    with open(local_path, "wb") as f:
                        f.write(dl_resp.read())
            except Exception:
                pass  # Skip files that fail to download

    except urllib.error.HTTPError as exc:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)
        if exc.code == 404:
            raise HTTPException(status_code=404, detail=f"Space '{req.hf_owner}/{req.hf_repo}' not found on HuggingFace.")
        raise HTTPException(status_code=500, detail=f"HuggingFace API error (HTTP {exc.code})")
    except urllib.error.URLError as exc:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)
        raise HTTPException(status_code=502, detail=f"Failed to reach HuggingFace: {str(exc.reason)}")
    except Exception as exc:
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(exc)}")

    # Try to read metadata from the cloned repo
    sdk = "unknown"
    readme_path = os.path.join(target_dir, "README.md")
    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r") as f:
                content = f.read(2000)
            # Parse YAML front-matter for sdk
            if content.startswith("---"):
                end = content.find("---", 3)
                if end > 0:
                    front = content[3:end]
                    for line in front.split("\n"):
                        if line.strip().startswith("sdk:"):
                            sdk = line.split(":", 1)[1].strip()
                            break
        except Exception:
            pass

    env_record = {
        "name": req.name,
        "description": req.description or f"Imported from HuggingFace: {req.hf_owner}/{req.hf_repo}",
        "category": "cross_workflow",
        "system": "Custom",
        "sdk": sdk,
        "source": "huggingface",
        "hf_url": req.hf_url,
        "hf_owner": req.hf_owner,
        "hf_repo": req.hf_repo,
        "local_path": target_dir,
        "imported_at": datetime.utcnow().isoformat() + "Z",
    }

    # Deep-classify using the downloaded files (README, deps, tags)
    cls = _deep_classify_environment(env_record)
    env_record["category"] = cls["category"]
    env_record["system"] = cls["system"]
    env_record["domain"] = cls["domain"]
    env_record["workflow"] = cls["workflow"]
    env_record["tags"] = cls["tags"]

    custom_environments.append(env_record)
    _persist_environments()

    return {
        "status": "success",
        "name": req.name,
        "description": env_record["description"],
        "sdk": sdk,
        "category": env_record["category"],
        "system": env_record["system"],
        "workflow": env_record.get("workflow", ""),
        "local_path": target_dir,
        "message": f"Space '{req.hf_owner}/{req.hf_repo}' cloned successfully to {target_dir}.",
    }


# ── AI Environment Classification ──────────────────────────────────

_CATEGORY_KEYWORDS = {
    "clinical": ["patient", "clinical", "hospital", "medical", "health", "ehr", "icu", "sepsis", "treatment", "diagnosis", "pharmacy", "nurse", "doctor", "vitals", "triage", "pathology", "radiology", "oncology", "cardiology", "surgery", "prescription", "discharge", "admission", "lab result", "blood", "imaging"],
    "claims": ["claim", "insurance", "policy", "underwriting", "adjudication", "premium", "coverage", "deductible", "reimbursement", "payer", "copay", "denial", "appeals", "billing"],
    "payment": ["payment", "reconciliation", "transaction", "ledger", "settlement", "invoice", "accounts receivable", "accounts payable", "remittance", "wire transfer", "ach", "fintech"],
    "revenue": ["revenue", "leakage", "billing", "charge", "pricing", "audit", "compliance", "fraud", "anomaly", "discrepancy", "chargeback", "collection"],
    "jira": ["jira", "ticket", "issue", "sprint", "backlog", "kanban", "agile", "scrum", "story point", "epic", "subtask", "assignee", "workflow", "status update"],
    "servicenow": ["servicenow", "incident management", "change request", "cmdb", "itil", "sla breach", "sla compliance", "service desk", "service catalog", "problem management", "configuration item"],
    "devops": ["deploy", "pipeline", "ci/cd", "kubernetes", "terraform", "ansible", "jenkins", "github actions", "helm", "monitoring", "alerting", "infrastructure", "microservice"],
    "hr": ["employee", "onboarding", "payroll", "leave", "attendance", "recruitment", "hiring", "resume", "candidate", "performance review", "compensation", "benefits", "offboarding", "workforce"],
    "crm": ["customer", "salesforce", "hubspot", "lead", "opportunity", "pipeline", "contact", "account", "deal", "engagement", "retention", "churn", "nps", "satisfaction"],
    "supply_chain": ["supply chain", "inventory", "warehouse", "logistics", "shipping", "procurement", "vendor", "purchase order", "forecast", "demand planning", "distribution"],
    "cross_workflow": ["workflow", "automation", "integration", "etl", "data pipeline", "orchestration", "scheduler", "batch", "api", "webhook"],
}

_SYSTEM_KEYWORDS = {
    "Epic": ["epic", "epic systems", "mychart", "hyperspace", "epic ehr"],
    "Cerner": ["cerner", "oracle health", "powerchart"],
    "FHIR": ["fhir", "hl7", "smart on fhir"],
    "Jira": ["jira", "atlassian", "confluence"],
    "ServiceNow": ["servicenow", "snow", "service-now"],
    "Salesforce": ["salesforce", "sfdc", "apex", "soql"],
    "SAP": ["sap", "s4hana", "sap hana", "abap"],
    "Workday": ["workday"],
    "Oracle": ["oracle", "oracle cloud", "peoplesoft"],
    "Stripe": ["stripe", "stripe api"],
    "QuickBooks": ["quickbooks", "qbo", "intuit"],
    "Kubernetes": ["kubernetes", "k8s", "kubectl", "helm"],
    "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "Azure": ["azure", "microsoft azure"],
    "GCP": ["gcp", "google cloud"],
    "GitHub": ["github", "github actions", "git"],
    "Jenkins": ["jenkins", "jenkinsfile"],
    "Docker": ["docker", "dockerfile", "container"],
    "Terraform": ["terraform", "hcl", "tfstate"],
    "HuggingFace": ["huggingface", "hugging face", "transformers", "gradio"],
    "Custom": [],
}

_CATEGORY_TO_DEFAULT_SYSTEM = {
    "clinical": "Epic", "claims": "Custom", "payment": "Custom",
    "revenue": "Custom", "jira": "Jira", "servicenow": "ServiceNow",
    "devops": "Kubernetes", "hr": "Workday", "crm": "Salesforce",
    "supply_chain": "SAP", "cross_workflow": "Custom",
    "financial": "Bloomberg",
}

_CATEGORY_TO_DOMAIN = {
    "clinical": "med-sim", "claims": "fin-sim", "payment": "fin-sim",
    "revenue": "fin-sim", "jira": "dev-sim", "servicenow": "dev-sim",
    "devops": "dev-sim", "hr": "hr-sim", "crm": "fin-sim",
    "supply_chain": "fin-sim", "cross_workflow": "cross-domain",
    "financial": "fin-sim",
}

_CATEGORY_TO_WORKFLOW = {
    "clinical": "Clinical", "claims": "Claims Processing",
    "payment": "Payment Processing", "revenue": "Revenue Audit",
    "jira": "IT Service Management", "servicenow": "True Technologies Inc",
    "devops": "DevOps", "hr": "Human Resources", "crm": "CRM",
    "supply_chain": "Supply Chain", "cross_workflow": "Cross-Workflow",
    "financial": "Financial Trading",
}


_SDK_TO_SYSTEM = {
    "gradio": "HuggingFace",
    "docker": "Docker",
    "static": "Static",
    "custom": "Terraform",
}

_TEMPLATE_TO_SYSTEM = {
    # Docker templates
    "streamlit": "Streamlit", "mlflow": "MLflow", "tensorboard": "TensorFlow",
    "jupyterlab": "Jupyter", "langfuse": "Langfuse", "wandb": "W&B",
    "plotly": "Plotly", "zenml": "ZenML", "labelstudio": "Label Studio",
    "comfyui": "ComfyUI", "argilla": "Argilla", "aimstack": "AimStack",
    "livebook": "Livebook", "marimo": "Marimo", "panel": "Panel",
    "quarto": "Quarto", "shiny-py": "Shiny", "shiny-r": "Shiny",
    "evidence": "Evidence", "giskard": "Giskard", "chatui": "HuggingFace",
    # Static templates
    "react": "React", "nextjs": "Next.js", "vue": "Vue", "svelte": "Svelte",
    "angular": "Angular", "preact": "Preact", "solid": "SolidJS",
    "gradio-lite": "HuggingFace", "transformers-js": "HuggingFace",
    # Gradio templates
    "chatbot": "HuggingFace", "diffusion": "HuggingFace",
    "image-class": "HuggingFace", "text-to-image": "HuggingFace",
    "audio-class": "HuggingFace", "leaderboard": "HuggingFace",
    "trackio": "HuggingFace",
}

# Software systems detectable from README content, tags, file names, and dependencies
_DEEP_SYSTEM_SIGNALS = {
    "Label Studio":   {"tags": ["label-studio", "labelstudio"], "readme": ["label studio", "labelstudio", "data labeling platform"], "deps": ["label-studio"], "files": []},
    "Gradio":         {"tags": ["gradio"], "readme": ["gradio"], "deps": ["gradio"], "files": ["app.py"]},
    "Streamlit":      {"tags": ["streamlit"], "readme": ["streamlit"], "deps": ["streamlit"], "files": ["streamlit_app.py"]},
    "FastAPI":        {"tags": ["fastapi"], "readme": ["fastapi"], "deps": ["fastapi", "uvicorn"], "files": []},
    "Flask":          {"tags": ["flask"], "readme": ["flask"], "deps": ["flask"], "files": []},
    "Django":         {"tags": ["django"], "readme": ["django"], "deps": ["django"], "files": ["manage.py"]},
    "TensorFlow":     {"tags": ["tensorflow", "keras"], "readme": ["tensorflow", "keras"], "deps": ["tensorflow", "keras"], "files": []},
    "PyTorch":        {"tags": ["pytorch", "torch"], "readme": ["pytorch", "torch"], "deps": ["torch", "pytorch"], "files": []},
    "LangChain":      {"tags": ["langchain"], "readme": ["langchain"], "deps": ["langchain", "langchain-core"], "files": []},
    "OpenAI":         {"tags": ["openai", "gpt"], "readme": ["openai", "gpt-4", "gpt-3", "chatgpt"], "deps": ["openai"], "files": []},
    "HuggingFace":    {"tags": ["huggingface", "diffusers"], "readme": ["hugging face", "huggingface.co"], "deps": ["diffusers", "huggingface-hub"], "files": []},
    "Stable Diffusion": {"tags": ["stable-diffusion", "diffusion"], "readme": ["stable diffusion", "sdxl", "sd model"], "deps": ["diffusers", "stable-diffusion"], "files": []},
    "LlamaIndex":     {"tags": ["llamaindex", "llama-index"], "readme": ["llamaindex", "llama_index", "llama index"], "deps": ["llama-index", "llama_index"], "files": []},
    "Kubernetes":     {"tags": ["kubernetes", "k8s"], "readme": ["kubernetes", "k8s", "kubectl"], "deps": [], "files": ["deployment.yaml"]},
    "React":          {"tags": ["react"], "readme": ["react"], "deps": ["react", "react-dom"], "files": ["package.json"]},
    "Next.js":        {"tags": ["nextjs", "next.js"], "readme": ["next.js", "nextjs"], "deps": ["next"], "files": ["next.config.js", "next.config.mjs"]},
    "MedAgentBench":  {"tags": ["openenv", "medagentbench"], "readme": ["medagentbench", "medical agent", "med agent", "openenv"], "deps": ["openenv-core", "openenv"], "files": ["openenv.yaml"]},
    "Gymnasium":      {"tags": ["gymnasium", "gym", "openai-gym"], "readme": ["gymnasium", "openai gym"], "deps": ["gymnasium", "gym"], "files": []},
    "MLflow":         {"tags": ["mlflow"], "readme": ["mlflow"], "deps": ["mlflow"], "files": []},
    "W&B":            {"tags": ["wandb", "weights-and-biases"], "readme": ["wandb", "weights & biases", "weights and biases"], "deps": ["wandb"], "files": []},
    "Jupyter":        {"tags": ["jupyter", "jupyterlab"], "readme": ["jupyter"], "deps": ["jupyter", "jupyterlab"], "files": []},
    "Terraform":      {"tags": ["terraform"], "readme": ["terraform"], "deps": [], "files": ["main.tf", "variables.tf"]},
    "Ansible":        {"tags": ["ansible"], "readme": ["ansible"], "deps": ["ansible"], "files": ["playbook.yml"]},
}


def _classify_environment(name: str, description: str, sdk: str = "", template: str = "") -> dict:
    """Shallow classifier: keyword matching on name + description + SDK/template signals."""
    text = (name + " " + description).lower()

    cat_scores = {}
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            cat_scores[cat] = score

    best_cat = max(cat_scores, key=cat_scores.get) if cat_scores else "cross_workflow"
    confidence = min(cat_scores.get(best_cat, 0) / 3.0, 1.0) if cat_scores else 0.1

    detected_system = None
    best_sys_score = 0
    for sys_name, keywords in _SYSTEM_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_sys_score:
            best_sys_score = score
            detected_system = sys_name

    if best_sys_score == 0:
        tmpl = (template or "").lower().strip()
        sdk_val = (sdk or "").lower().strip()
        if tmpl and tmpl != "blank" and tmpl in _TEMPLATE_TO_SYSTEM:
            detected_system = _TEMPLATE_TO_SYSTEM[tmpl]
        elif sdk_val and sdk_val in _SDK_TO_SYSTEM:
            detected_system = _SDK_TO_SYSTEM[sdk_val]

    system = detected_system if detected_system else _CATEGORY_TO_DEFAULT_SYSTEM.get(best_cat, "Custom")
    domain = _CATEGORY_TO_DOMAIN.get(best_cat, "cross-domain")
    workflow = _CATEGORY_TO_WORKFLOW.get(best_cat, "Cross-Workflow")

    tags = [best_cat, system.lower(), domain]
    if workflow:
        tags.append(workflow.lower().replace(" ", "-"))

    return {
        "category": best_cat,
        "system": system,
        "domain": domain,
        "workflow": workflow,
        "tags": list(set(tags)),
        "confidence": round(confidence, 2),
    }


def _deep_classify_environment(env_record: dict) -> dict:
    """Deep-classify an environment by analyzing README, tags, files, and dependencies.
    Falls back to shallow keyword classifier if no local content is available."""
    name = env_record.get("name", "")
    description = env_record.get("description", "")
    sdk = env_record.get("sdk", "")
    template = env_record.get("template", "")
    local_path = env_record.get("local_path", "")

    # Gather rich signals from local files
    readme_text = ""
    hf_tags = []
    file_names = []
    dependencies = []

    if local_path and os.path.isdir(local_path):
        # Read README
        readme_path = os.path.join(local_path, "README.md")
        if os.path.exists(readme_path):
            try:
                with open(readme_path, "r") as f:
                    raw = f.read(5000)
                readme_text = raw.lower()
                # Extract HF front-matter tags
                if raw.startswith("---"):
                    end = raw.find("---", 3)
                    if end > 0:
                        front = raw[3:end]
                        in_tags = False
                        for line in front.split("\n"):
                            stripped = line.strip()
                            if stripped.startswith("tags:"):
                                in_tags = True
                                continue
                            if in_tags:
                                if stripped.startswith("- "):
                                    hf_tags.append(stripped[2:].lower())
                                else:
                                    in_tags = False
                            # Also check short_description or title
                            if ":" in stripped:
                                k, v = stripped.split(":", 1)
                                if k.strip() in ("short_description", "title"):
                                    readme_text += " " + v.strip().lower()
            except Exception:
                pass

        # Collect file names
        try:
            for root, dirs, files in os.walk(local_path):
                dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "node_modules")]
                for f in files:
                    file_names.append(f)
                if len(file_names) > 200:
                    break
        except Exception:
            pass

        # Parse dependencies from pyproject.toml or requirements.txt
        for depfile in ("pyproject.toml", "requirements.txt"):
            dep_path = os.path.join(local_path, depfile)
            if os.path.exists(dep_path):
                try:
                    with open(dep_path, "r") as f:
                        content = f.read(3000).lower()
                    for line in content.split("\n"):
                        line = line.strip().strip('",')
                        if line and not line.startswith("#") and not line.startswith("["):
                            # Extract package name (before any version specifier)
                            pkg = line.split(">=")[0].split("<=")[0].split("==")[0].split("~=")[0].split(">")[0].split("<")[0].strip()
                            if pkg and len(pkg) < 50:
                                dependencies.append(pkg)
                except Exception:
                    pass

    # Score systems using deep signals
    sys_scores = {}
    for sys_name, signals in _DEEP_SYSTEM_SIGNALS.items():
        score = 0
        # Tag matches (highest weight — explicit metadata)
        for tag in signals["tags"]:
            if tag in hf_tags:
                score += 5
        # README content matches
        for kw in signals["readme"]:
            if kw in readme_text:
                score += 3
        # Dependency matches
        for dep in signals["deps"]:
            if dep in dependencies:
                score += 4
        # File name matches
        for fname in signals["files"]:
            if fname in file_names:
                score += 2
        if score > 0:
            sys_scores[sys_name] = score

    # Clean description of boilerplate before classification
    clean_desc = description
    for boilerplate in ("Imported from HuggingFace:", "Imported from GitHub:", "Imported from URL:", "Custom environment created by"):
        if boilerplate.lower() in clean_desc.lower():
            clean_desc = clean_desc.split(boilerplate)[-1].strip() if boilerplate in clean_desc else clean_desc

    # Run shallow classifier for category detection (uses name + cleaned description + README excerpt)
    full_text = name + " " + clean_desc + " " + readme_text[:500]
    shallow = _classify_environment(name, full_text, sdk=sdk, template=template)

    # Override system if deep analysis found a strong signal
    if sys_scores:
        best_deep_system = max(sys_scores, key=sys_scores.get)
        best_deep_score = sys_scores[best_deep_system]
        if best_deep_score >= 3:  # Meaningful signal threshold
            shallow["system"] = best_deep_system
            # Rebuild tags with the new system
            shallow["tags"] = list(set([
                shallow["category"], best_deep_system.lower(),
                shallow["domain"],
                shallow["workflow"].lower().replace(" ", "-") if shallow.get("workflow") else ""
            ]) - {""})

    return shallow


@app.post("/api/classify-environment")
async def classify_environment_endpoint(request: Request):
    """Classify an environment. Uses deep analysis if the env has local files (HF imports)."""
    data = await request.json()
    env_name = data.get("name", "")
    # Try deep classification if env has local files
    env_record = next((e for e in custom_environments if e["name"] == env_name), None)
    if env_record and env_record.get("local_path") and os.path.isdir(env_record.get("local_path", "")):
        result = _deep_classify_environment(env_record)
    else:
        # Build a pseudo-record for deep classify (will fall back to shallow if no local_path)
        pseudo = dict(data)
        result = _deep_classify_environment(pseudo)
    return result


def _auto_classify_all_environments() -> int:
    """Scan all custom environments and classify any missing system/workflow/tags.
    Returns the number of environments updated."""
    updated = 0
    for env in custom_environments:
        needs_update = False
        # Check if key classification fields are missing or generic
        if not env.get("system") or env.get("system") in ("Custom", ""):
            needs_update = True
        if not env.get("workflow") or env.get("workflow") in ("Cross-Workflow", ""):
            needs_update = True
        if not env.get("domain"):
            needs_update = True
        if not env.get("tags"):
            needs_update = True
        cat = env.get("category", "")
        if not cat or cat in ("custom", "cross_workflow"):
            needs_update = True

        if needs_update:
            cls = _deep_classify_environment(env)
            # Only overwrite if classifier found something meaningful
            if cls["category"] != "cross_workflow" or not env.get("category"):
                env["category"] = cls["category"]
            if cls["system"] != "Custom" or not env.get("system") or env.get("system") == "Custom":
                env["system"] = cls["system"]
            env["domain"] = cls["domain"]
            env["workflow"] = cls["workflow"]
            env["tags"] = cls["tags"]
            updated += 1
    if updated > 0:
        _persist_environments()
    return updated


@app.post("/api/classify-all-environments")
async def classify_all_environments(request: Request):
    """Re-classify all custom environments. Use force=true to reclassify all, not just missing."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    force = data.get("force", False)
    if force:
        updated = 0
        for env in custom_environments:
            cls = _deep_classify_environment(env)
            env["category"] = cls["category"]
            env["system"] = cls["system"]
            env["domain"] = cls["domain"]
            env["workflow"] = cls["workflow"]
            env["tags"] = cls["tags"]
            updated += 1
        if updated > 0:
            _persist_environments()
    else:
        updated = _auto_classify_all_environments()
    return {"status": "ok", "updated": updated, "total": len(custom_environments)}


# --- Startup: auto-classify any existing environments missing tags ---
_startup_classified = _auto_classify_all_environments() if custom_environments else 0
if _startup_classified:
    print(f"[AI Agent] Auto-classified {_startup_classified} environment(s) on startup")

# --- Startup: initialise MCP agent ---
def _get_catalog_count() -> int:
    try:
        return len(list_all_environments())
    except Exception:
        return 0

_init_agent(
    env_store=_env_store,
    custom_envs=custom_environments,
    catalog_count_fn=_get_catalog_count,
    classify_fn=_deep_classify_environment,
    hf_spaces_dir=HF_SPACES_DIR,
)

# Auto-backup on startup
from api.config import AUTO_BACKUP_ON_STARTUP  # noqa: E402
if AUTO_BACKUP_ON_STARTUP and custom_environments:
    _startup_backup_id = _env_store.create_backup(
        label=f"auto-startup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    print(f"[MCP Agent] Startup backup created (id={_startup_backup_id})")


@app.get("/api/custom-environments")
async def list_custom_environments():
    """List all custom / imported environments."""
    return {"count": len(custom_environments), "environments": custom_environments}


@app.delete("/api/custom-environments/{name}")
async def delete_custom_environment(name: str):
    """Delete a custom / imported environment by name."""
    global custom_environments
    env_record = next((e for e in custom_environments if e["name"] == name), None)
    if not env_record:
        raise HTTPException(status_code=404, detail=f"Environment '{name}' not found.")

    # Remove cloned directory if it exists
    local_path = env_record.get("local_path")
    if local_path and os.path.isdir(local_path):
        shutil.rmtree(local_path, ignore_errors=True)

    # Remove from persisted JSON store
    _remove_persisted_environment(name)

    custom_environments = [e for e in custom_environments if e["name"] != name]
    return {"status": "deleted", "name": name}


@app.post("/api/custom-environments")
async def save_custom_environment_config(request: Request):
    """Save or update configuration for a custom environment."""
    try:
        data = await request.json()
        name = data.get("name")
        if not name:
            raise HTTPException(status_code=400, detail="Environment name required")

        # Find existing or create new record
        existing = next((e for e in custom_environments if e["name"] == name), None)
        if existing:
            # Update existing - merge all incoming fields
            for key, val in data.items():
                existing[key] = val
            # Auto-classify if system/workflow still missing after update
            if not existing.get("system") or existing.get("system") in ("Custom", "") or not existing.get("workflow"):
                cls = _deep_classify_environment(existing)
                if cls["system"] != "Custom" or not existing.get("system") or existing.get("system") == "Custom":
                    existing["system"] = cls["system"]
                if not existing.get("workflow"):
                    existing["workflow"] = cls["workflow"]
                if not existing.get("domain"):
                    existing["domain"] = cls["domain"]
                if not existing.get("tags"):
                    existing["tags"] = cls["tags"]
                cur_cat = existing.get("category", "")
                if not cur_cat or cur_cat in ("custom", "cross_workflow"):
                    existing["category"] = cls["category"]
            _persist_environments()
            return {"status": "updated", "name": name}
        else:
            # Create new record - store all incoming data
            record = dict(data)
            record.setdefault("source", "custom")
            # Auto-classify if category is generic or missing
            cur_cat = record.get("category", "")
            if not cur_cat or cur_cat in ("custom", "cross_workflow"):
                cls = _deep_classify_environment(record)
                record["category"] = cls["category"]
                record["system"] = cls["system"]
                record["domain"] = cls["domain"]
                record["workflow"] = cls["workflow"]
                record["tags"] = cls["tags"]
            custom_environments.append(record)
            _persist_environments()
            return {"status": "created", "name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Scenario CRUD (SQLite-persisted, supports any custom JSON structure)
# ---------------------------------------------------------------------------

@app.get("/api/scenarios")
async def list_scenarios(product: Optional[str] = None):
    """List all custom scenarios, optionally filtered by product."""
    if product:
        scenarios = _scenario_store.list_by_product(product)
    else:
        scenarios = _scenario_store.list_all()
    return {"count": len(scenarios), "scenarios": scenarios}


@app.post("/api/scenarios")
async def save_scenarios(request: Request):
    """Save one or more scenarios.

    Accepts two formats:
      - Bulk:   { "scenarios": [ {...}, {...} ] }
      - Single: { "id": "...", "name": "...", ... }
    """
    try:
        data = await request.json()
        items: list = []

        if "scenarios" in data and isinstance(data["scenarios"], list):
            items = data["scenarios"]
        elif "id" in data:
            items = [data]
        else:
            raise HTTPException(
                status_code=400,
                detail="Provide either { scenarios: [...] } or a single object with an 'id' field.",
            )

        created = 0
        updated = 0
        for item in items:
            scenario_id = item.get("id")
            if not scenario_id:
                continue  # skip entries without an id
            existing = _scenario_store.get(scenario_id)
            item.setdefault("source", "custom")
            _scenario_store.upsert(scenario_id, item)
            if existing:
                updated += 1
            else:
                created += 1

        return {"status": "ok", "created": created, "updated": updated}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/scenarios/{scenario_id}")
async def delete_scenario(scenario_id: str):
    """Delete a single scenario by ID."""
    if not _scenario_store.delete(scenario_id):
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found.")
    return {"status": "deleted", "id": scenario_id}


@app.get("/api/environment/{name}/analyze")
async def analyze_environment(name: str):
    """Analyze a cloned HuggingFace space and return rich metadata."""
    import re as _re
    import glob as _glob

    # Find the environment in custom_environments
    env_record = next((e for e in custom_environments if e["name"] == name), None)
    local_path = None
    if env_record and "local_path" in env_record:
        local_path = env_record["local_path"]
    else:
        candidate = os.path.join(HF_SPACES_DIR, name)
        if os.path.isdir(candidate):
            local_path = candidate

    if not local_path or not os.path.isdir(local_path):
        raise HTTPException(status_code=404, detail=f"No cloned environment found for '{name}'")

    result = {
        "name": name,
        "local_path": local_path,
        "readme_raw": "",
        "front_matter": {},
        "openenv": {},
        "pyproject": {},
        "files": [],
        "endpoints": [],
        "models": {},
    }

    # 1) List files (skip .git, __pycache__, .egg-info, uv.lock)
    skip_dirs = {".git", "__pycache__", "node_modules"}
    skip_exts = {".lock", ".pyc"}
    file_list = []
    for root, dirs, files in os.walk(local_path):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.endswith(".egg-info")]
        for f in files:
            if any(f.endswith(ext) for ext in skip_exts):
                continue
            rel = os.path.relpath(os.path.join(root, f), local_path)
            size = os.path.getsize(os.path.join(root, f))
            file_list.append({"path": rel, "size": size})
    result["files"] = sorted(file_list, key=lambda x: x["path"])

    # 2) Parse README.md
    readme_path = os.path.join(local_path, "README.md")
    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r") as f:
                raw = f.read()
            result["readme_raw"] = raw
            if raw.startswith("---"):
                end = raw.find("---", 3)
                if end > 0:
                    front = raw[3:end]
                    fm = {}
                    for line in front.strip().split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            key = key.strip()
                            val = val.strip()
                            if val.startswith("[") or key == "tags":
                                continue
                            fm[key] = val
                    tags = []
                    in_tags = False
                    for line in front.strip().split("\n"):
                        if line.strip().startswith("tags:"):
                            in_tags = True
                            continue
                        if in_tags:
                            if line.strip().startswith("- "):
                                tags.append(line.strip()[2:])
                            else:
                                in_tags = False
                    if tags:
                        fm["tags"] = tags
                    result["front_matter"] = fm
                    result["readme_raw"] = raw[end + 3:].strip()
        except Exception:
            pass

    # 3) Parse openenv.yaml
    oe_path = os.path.join(local_path, "openenv.yaml")
    if os.path.exists(oe_path):
        try:
            with open(oe_path, "r") as f:
                lines = f.readlines()
            oe = {}
            for line in lines:
                if ":" in line and not line.strip().startswith("#"):
                    key, val = line.split(":", 1)
                    oe[key.strip()] = val.strip()
            result["openenv"] = oe
        except Exception:
            pass

    # 4) Parse pyproject.toml (basic)
    pp_path = os.path.join(local_path, "pyproject.toml")
    if os.path.exists(pp_path):
        try:
            with open(pp_path, "r") as f:
                content = f.read()
            pp = {}
            in_project = False
            in_deps = False
            deps = []
            for line in content.split("\n"):
                if line.strip() == "[project]":
                    in_project = True
                    continue
                if line.strip().startswith("[") and line.strip() != "[project]":
                    in_project = False
                    in_deps = False
                if in_project:
                    if line.strip() == "dependencies = [":
                        in_deps = True
                        continue
                    if in_deps:
                        if line.strip() == "]":
                            in_deps = False
                            continue
                        dep = line.strip().strip('",')
                        if dep and not dep.startswith("#"):
                            deps.append(dep)
                    elif "=" in line and not line.strip().startswith("#"):
                        key, val = line.split("=", 1)
                        pp[key.strip()] = val.strip().strip('"')
            if deps:
                pp["dependencies"] = deps
            result["pyproject"] = pp
        except Exception:
            pass

    # 5) Extract endpoints from app.py files
    app_files = _glob.glob(os.path.join(local_path, "**", "app.py"), recursive=True)
    endpoints = []
    for app_file in app_files:
        try:
            with open(app_file, "r") as f:
                code = f.read(10000)
            for m in _re.finditer(r'@\w+\.(get|post|put|delete|websocket)\(["\']([^"\']+)', code):
                endpoints.append({"method": m.group(1).upper(), "path": m.group(2)})
        except Exception:
            pass
    result["endpoints"] = endpoints

    # 6) Extract model definitions from models.py
    models_path = os.path.join(local_path, "models.py")
    if os.path.exists(models_path):
        try:
            with open(models_path, "r") as f:
                code = f.read(15000)
            models = {}
            current_class = None
            current_fields = []
            current_doc = ""
            for line in code.split("\n"):
                class_match = _re.match(r'^class (\w+)\(.*(?:BaseModel|Enum|Action|Observation|State)', line)
                if class_match:
                    if current_class:
                        models[current_class] = {"fields": current_fields, "doc": current_doc}
                    current_class = class_match.group(1)
                    current_fields = []
                    current_doc = ""
                    continue
                if current_class:
                    doc_match = _re.match(r'\s+"""(.+?)"""', line)
                    if doc_match:
                        current_doc = doc_match.group(1)
                        continue
                    enum_match = _re.match(r'\s+(\w+)\s*=\s*["\'](.+?)["\']', line)
                    if enum_match:
                        current_fields.append({"name": enum_match.group(1), "value": enum_match.group(2)})
                        continue
                    field_match = _re.match(r'\s+(\w+):\s*(.+?)(?:\s*=.*)?$', line)
                    if field_match and not line.strip().startswith("#") and not line.strip().startswith('"""'):
                        fname = field_match.group(1)
                        ftype = field_match.group(2).strip().rstrip("=").strip()
                        desc_match = _re.search(r'description=["\'](.+?)["\']', line)
                        desc = desc_match.group(1) if desc_match else ""
                        current_fields.append({"name": fname, "type": ftype, "description": desc})
            if current_class:
                models[current_class] = {"fields": current_fields, "doc": current_doc}
            result["models"] = models
        except Exception:
            pass

    return result


@app.get("/api/environment/{name}/file")
async def read_environment_file(name: str, path: str):
    """Read a specific file from a cloned environment."""
    env_record = next((e for e in custom_environments if e["name"] == name), None)
    local_path = None
    if env_record and "local_path" in env_record:
        local_path = env_record["local_path"]
    else:
        candidate = os.path.join(HF_SPACES_DIR, name)
        if os.path.isdir(candidate):
            local_path = candidate
    if not local_path or not os.path.isdir(local_path):
        raise HTTPException(status_code=404, detail=f"No cloned environment found for '{name}'")
    full_path = os.path.normpath(os.path.join(local_path, path))
    if not full_path.startswith(os.path.normpath(local_path)):
        raise HTTPException(status_code=403, detail="Path traversal not allowed")
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    try:
        size = os.path.getsize(full_path)
        if size > 500_000:
            return {"path": path, "content": None, "truncated": True, "size": size}
        with open(full_path, "r", errors="replace") as f:
            content = f.read()
        return {"path": path, "content": content, "size": size, "truncated": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/huggingface/proxy")
async def proxy_huggingface_app(url: str):
    """Proxy a HuggingFace Space page to avoid X-Frame-Options blocking."""
    import urllib.request
    import urllib.error
    if not url.startswith("https://huggingface.co/"):
        raise HTTPException(status_code=400, detail="Only huggingface.co URLs are allowed")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "text/html")
            body = resp.read(2_000_000).decode("utf-8", errors="replace")
        # Inject a <base> tag so relative resources resolve correctly
        base_url = url.rsplit("/", 1)[0] + "/"
        base_tag = f'<base href="{base_url}">'
        if "<head" in body:
            body = body.replace("<head>", "<head>" + base_tag, 1)
            if "<head>" not in body:
                body = _re.sub(r'(<head[^>]*>)', r'\1' + base_tag, body, count=1)
        else:
            body = base_tag + body
        return HTMLResponse(content=body)
    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=e.code, detail=f"HuggingFace returned {e.code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ===========================================================================
# Gymnasium Custom Environment Upload
# ===========================================================================
import importlib.util as _importlib_util
import re as _re_mod

_CUSTOM_ENVS_DIR = os.path.join(os.path.dirname(__file__), "data", "custom_envs")
os.makedirs(_CUSTOM_ENVS_DIR, exist_ok=True)

# In-memory registry of uploaded gymnasium envs: { name: { class_name, file_path, config, meta } }
_gymnasium_custom_envs: Dict[str, Dict[str, Any]] = {}


def _load_gymnasium_class(file_path: str, class_name: str):
    """Dynamically load a class from a Python file."""
    spec = _importlib_util.spec_from_file_location("custom_env_module", file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    module = _importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    cls = getattr(module, class_name, None)
    if cls is None:
        raise ImportError(f"Class '{class_name}' not found in {file_path}")
    return cls


@app.post("/api/custom-environments/upload-gymnasium")
async def upload_gymnasium_env(
    file: UploadFile = File(...),
    name: str = Form(...),
    class_name: str = Form(...),
    config_json: str = Form("{}"),
    description: str = Form(""),
    owner: str = Form("centific"),
):
    """Upload a Python file containing a gymnasium env class."""
    if not file.filename or not file.filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="File must be a .py file")

    # Sanitize name for filesystem
    safe_name = _re_mod.sub(r"[^a-zA-Z0-9_-]", "_", name)
    file_path = os.path.join(_CUSTOM_ENVS_DIR, f"{safe_name}.py")

    # Save file
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Validate: file parses as Python and contains the class
    try:
        compile(content, file_path, "exec")
    except SyntaxError as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Python syntax error: {e}")

    # Try to load the class and get space info
    obs_dim = 0
    action_dim = 0
    action_type = "unknown"
    try:
        cls = _load_gymnasium_class(file_path, class_name)
        # Try to instantiate with config
        config = json.loads(config_json) if config_json.strip() else {}
        try:
            env_instance = cls(config=config) if config else cls()
        except TypeError:
            env_instance = cls()
        if hasattr(env_instance, "observation_space"):
            obs_dim = env_instance.observation_space.shape[0] if hasattr(env_instance.observation_space, "shape") else 0
        if hasattr(env_instance, "action_space"):
            if hasattr(env_instance.action_space, "n"):
                action_type = "discrete"
                action_dim = int(env_instance.action_space.n)
            elif hasattr(env_instance.action_space, "shape"):
                action_type = "continuous"
                action_dim = int(env_instance.action_space.shape[0]) if len(env_instance.action_space.shape) > 0 else 1
    except Exception as e:
        # Class didn't load/instantiate but file is saved — user can fix config later
        pass

    # Register in memory
    _gymnasium_custom_envs[name] = {
        "class_name": class_name,
        "file_path": file_path,
        "config_json": config_json,
        "description": description,
        "owner": owner,
        "observation_dim": obs_dim,
        "action_dim": action_dim,
        "action_type": action_type,
    }

    # Also register in the financial env meta so it shows in the console
    slug = _re_mod.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")
    _FINANCIAL_ENV_SLUG_MAP[slug] = f"__custom__{name}"
    _FINANCIAL_ENV_META[slug] = {
        "display_name": name,
        "description": description or f"Custom Gymnasium environment: {class_name}",
        "tools": [],
        "observation_dim": obs_dim,
        "action_type": action_type,
        "action_dim": action_dim,
    }

    return {
        "status": "uploaded",
        "name": name,
        "class_name": class_name,
        "file_path": file_path,
        "observation_dim": obs_dim,
        "action_dim": action_dim,
        "action_type": action_type,
    }


# ===========================================================================
# Financial Simulation Console — Gymnasium RL environment API
# ===========================================================================
import time as _time
import uuid as _uuid
import numpy as _np

# In-memory stores for financial env instances and rollouts
_financial_active_envs: Dict[str, Dict[str, Any]] = {}
_financial_rollout_store: Dict[str, Dict[str, Any]] = {}
_financial_start_time: float = _time.time()

# Registry mapping slugs to catalog names
_FINANCIAL_ENV_SLUG_MAP = {
    "delcita": "Delcita",
}

# Metadata for the financial env list endpoint
_FINANCIAL_ENV_META = {
    "delcita": {
        "display_name": "ABC Hedge Funds",
        "description": "Single-asset trading with discrete actions and risk-adjusted rewards",
        "tools": [
            {"name": "get_market_state", "description": "Fetch price, volume, and technical indicators"},
            {"name": "execute_trade", "description": "Buy/sell/hold with position sizing"},
            {"name": "get_portfolio_status", "description": "Current P&L, position, drawdown"},
        ],
        "observation_dim": 22,
        "action_type": "discrete",
        "action_dim": 5,
    },
}


def _fin_ndarray_to_list(obj):
    """Recursively convert numpy types to Python natives."""
    if isinstance(obj, _np.ndarray):
        return obj.tolist()
    if isinstance(obj, (_np.float32, _np.float64)):
        return float(obj)
    if isinstance(obj, (_np.int32, _np.int64, _np.bool_)):
        return int(obj)
    if isinstance(obj, dict):
        return {k: _fin_ndarray_to_list(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_fin_ndarray_to_list(v) for v in obj]
    return obj


@app.get("/financial-console")
async def financial_console_page():
    """Serve the Financial Simulation Console."""
    path = os.path.join(os.path.dirname(__file__), "static", "financial-console.html")
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Financial console not found")


@app.get("/financial/health")
async def financial_health():
    return {
        "status": "online",
        "uptime_seconds": round(_time.time() - _financial_start_time, 1),
        "active_environments": len(_financial_active_envs),
        "total_connections": len(_financial_active_envs),
        "available_env_types": list(_FINANCIAL_ENV_META.keys()),
    }


@app.get("/financial/envs/list")
async def financial_list_envs():
    return {
        name: {
            "display_name": meta["display_name"],
            "description": meta["description"],
            "tools": meta["tools"],
            "observation_dim": meta["observation_dim"],
            "action_type": meta["action_type"],
            "action_dim": meta["action_dim"],
        }
        for name, meta in _FINANCIAL_ENV_META.items()
    }


class _FinCreateEnvRequest(BaseModel):
    env_type: str
    config: Dict[str, Any] = {}


@app.post("/financial/envs/create")
async def financial_create_env(req: _FinCreateEnvRequest):
    if req.env_type not in _FINANCIAL_ENV_SLUG_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown env_type '{req.env_type}'. Choose from: {list(_FINANCIAL_ENV_SLUG_MAP.keys())}",
        )
    catalog_name = _FINANCIAL_ENV_SLUG_MAP[req.env_type]
    config = req.config or {}

    # Custom gymnasium envs start with __custom__
    if catalog_name.startswith("__custom__"):
        custom_name = catalog_name[len("__custom__"):]
        custom_entry = _gymnasium_custom_envs.get(custom_name)
        if not custom_entry:
            raise HTTPException(status_code=404, detail=f"Custom env '{custom_name}' not found")
        try:
            env_class = _load_gymnasium_class(custom_entry["file_path"], custom_entry["class_name"])
            saved_config = json.loads(custom_entry.get("config_json", "{}") or "{}")
            merged_config = {**saved_config, **config}
            try:
                env = env_class(config=merged_config) if merged_config else env_class()
            except TypeError:
                env = env_class()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load custom env: {e}")
    else:
        env_class = get_environment_class(catalog_name)
        if env_class is None:
            raise HTTPException(status_code=500, detail=f"Failed to load environment class for '{catalog_name}'")
        env = env_class(config=config if config else None)
    env_id = str(_uuid.uuid4())[:8]
    rollout_id = str(_uuid.uuid4())[:12]

    obs, info = env.reset()
    _financial_active_envs[env_id] = {
        "env": env,
        "env_type": req.env_type,
        "created_at": _time.time(),
        "steps": 0,
        "last_obs": obs,
        "rollout_id": rollout_id,
    }
    _financial_rollout_store[rollout_id] = {
        "id": rollout_id,
        "env_id": env_id,
        "env_type": req.env_type,
        "status": "in_progress",
        "created_at": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        "steps": [],
        "total_reward": 0.0,
        "total_steps": 0,
    }

    # Determine action space info
    meta = _FINANCIAL_ENV_META[req.env_type]
    action_space_info = {
        "type": meta["action_type"],
        "dim": env.action_space.n if hasattr(env.action_space, "n") else list(env.action_space.shape),
    }

    return {
        "env_id": env_id,
        "env_type": req.env_type,
        "observation_shape": list(env.observation_space.shape),
        "action_space_info": _fin_ndarray_to_list(action_space_info),
        "rollout_id": rollout_id,
    }


class _FinStepRequest(BaseModel):
    action: Any


@app.post("/financial/envs/{env_id}/step")
async def financial_step_env(env_id: str, req: _FinStepRequest):
    if env_id not in _financial_active_envs:
        raise HTTPException(status_code=404, detail=f"Environment '{env_id}' not found")

    entry = _financial_active_envs[env_id]
    raw_action = req.action
    action = raw_action
    if isinstance(raw_action, list):
        action = _np.array(raw_action, dtype=_np.float32)

    obs, reward, terminated, truncated, info = entry["env"].step(action)
    entry["last_obs"] = obs
    entry["steps"] += 1

    info_out = _fin_ndarray_to_list(dict(info) if isinstance(info, dict) else {})

    # Record in rollout
    rollout_id = entry.get("rollout_id")
    rollout = _financial_rollout_store.get(rollout_id) if rollout_id else None
    if rollout is not None:
        rollout["steps"].append({
            "step": int(entry["steps"]),
            "action": _fin_ndarray_to_list(raw_action),
            "reward": float(reward),
        })
        rollout["total_reward"] = float(rollout.get("total_reward", 0.0)) + float(reward)
        rollout["total_steps"] = int(entry["steps"])
        if terminated or truncated:
            rollout["status"] = "completed"

    return {
        "observation": _fin_ndarray_to_list(obs),
        "reward": float(reward),
        "terminated": bool(terminated),
        "truncated": bool(truncated),
        "info": info_out,
    }


@app.post("/financial/envs/{env_id}/reset")
async def financial_reset_env(env_id: str):
    if env_id not in _financial_active_envs:
        raise HTTPException(status_code=404, detail=f"Environment '{env_id}' not found")

    entry = _financial_active_envs[env_id]
    obs, info = entry["env"].reset()
    entry["last_obs"] = obs
    entry["steps"] = 0

    # New rollout
    rollout_id = str(_uuid.uuid4())[:12]
    entry["rollout_id"] = rollout_id
    _financial_rollout_store[rollout_id] = {
        "id": rollout_id,
        "env_id": env_id,
        "env_type": entry["env_type"],
        "status": "in_progress",
        "created_at": _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime()),
        "steps": [],
        "total_reward": 0.0,
        "total_steps": 0,
    }

    return {
        "observation": _fin_ndarray_to_list(obs),
        "info": _fin_ndarray_to_list(dict(info) if isinstance(info, dict) else {}),
    }


@app.delete("/financial/envs/{env_id}")
async def financial_delete_env(env_id: str):
    if env_id not in _financial_active_envs:
        raise HTTPException(status_code=404, detail=f"Environment '{env_id}' not found")

    entry = _financial_active_envs[env_id]
    rollout_id = entry.get("rollout_id")
    rollout = _financial_rollout_store.get(rollout_id) if rollout_id else None
    if rollout is not None and rollout.get("status") == "in_progress":
        rollout["status"] = "aborted"
    del _financial_active_envs[env_id]
    return {"status": "deleted", "env_id": env_id}


if __name__ == "__main__":
    # Allow port to be configured via environment variable (for cloud platforms)
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

