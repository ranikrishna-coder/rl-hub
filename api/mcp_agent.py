"""
MCP Environment Health Agent.

Provides tools for environment management, health monitoring, and backups.
Registered as a FastAPI APIRouter on the main app.

Endpoints:
    GET  /api/agent/tools              – list available tools
    POST /api/agent/invoke             – invoke a tool by name
    GET  /api/agent/health             – quick health status
    GET  /api/agent/health/history     – health metrics over time
    GET  /api/agent/stats              – environment statistics
    GET  /api/agent/backups            – list backups
    POST /api/agent/backups            – create a backup
    POST /api/agent/backups/{id}/restore – restore from backup
"""

import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/agent", tags=["MCP Agent"])

# These are injected by main.py at startup via init_agent()
_env_store = None          # EnvironmentStore instance
_custom_envs_ref = None    # reference to the in-memory custom_environments list
_catalog_count_fn = None   # callable returning catalog environment count
_classify_fn = None        # callable for deep classification
_hf_spaces_dir = ""        # path to hf_spaces directory


def init_agent(
    env_store,
    custom_envs: list,
    catalog_count_fn,
    classify_fn=None,
    hf_spaces_dir: str = "",
):
    """Inject dependencies from main.py so the agent can access shared state."""
    global _env_store, _custom_envs_ref, _catalog_count_fn, _classify_fn, _hf_spaces_dir
    _env_store = env_store
    _custom_envs_ref = custom_envs
    _catalog_count_fn = catalog_count_fn
    _classify_fn = classify_fn
    _hf_spaces_dir = hf_spaces_dir


# ======================================================================
# Tool registry
# ======================================================================

AGENT_TOOLS: Dict[str, Dict[str, Any]] = {
    "list_environments": {
        "description": "List all user-created and imported environments with metadata",
        "parameters": {},
    },
    "check_health": {
        "description": "Run health checks on all environments and return a status report",
        "parameters": {},
    },
    "backup_state": {
        "description": "Create a backup snapshot of all user environments",
        "parameters": {"label": {"type": "string", "description": "Optional backup label"}},
    },
    "restore_state": {
        "description": "Restore user environments from a previous backup",
        "parameters": {"backup_id": {"type": "integer", "description": "ID of backup to restore"}},
    },
    "classify_environment": {
        "description": "Run AI classification on a specific environment",
        "parameters": {"name": {"type": "string", "description": "Environment name"}},
    },
    "get_stats": {
        "description": "Get aggregated environment statistics and metrics",
        "parameters": {},
    },
}


# ======================================================================
# Tool implementations
# ======================================================================

def _tool_list_environments() -> dict:
    envs = _env_store.list_all() if _env_store else []
    return {"count": len(envs), "environments": envs}


def _tool_check_health() -> dict:
    """Compute comprehensive health metrics."""
    envs = _env_store.list_all() if _env_store else []
    catalog_count = _catalog_count_fn() if _catalog_count_fn else 0

    health: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "status": "healthy",
        "catalog_environments": catalog_count,
        "user_environments": len(envs),
        "total_environments": catalog_count + len(envs),
        "classification_coverage": 0,
        "hf_imports": 0,
        "hf_imports_with_files": 0,
        "custom_created": 0,
        "missing_classification": [],
        "orphaned_dirs": [],
        "last_backup": None,
        "db_size_bytes": _env_store.db_size_bytes() if _env_store else 0,
        "warnings": [],
    }

    # --- Analyse environments ---
    classified_count = 0
    hf_env_names = set()
    for env in envs:
        if env.get("source") == "huggingface":
            health["hf_imports"] += 1
            hf_env_names.add(env.get("name", ""))
            lp = env.get("local_path", "")
            if lp and os.path.isdir(lp):
                health["hf_imports_with_files"] += 1
            elif lp:
                health["warnings"].append(
                    f"HF import '{env.get('name')}' missing local files at {lp}"
                )
        else:
            health["custom_created"] += 1

        has_cls = (
            env.get("system") and env["system"] not in ("Custom", "")
        )
        if has_cls:
            classified_count += 1
        else:
            health["missing_classification"].append(env.get("name", "?"))

    if envs:
        health["classification_coverage"] = round(classified_count / len(envs) * 100, 1)

    # --- Orphaned hf_spaces dirs ---
    if _hf_spaces_dir and os.path.isdir(_hf_spaces_dir):
        try:
            for d in os.listdir(_hf_spaces_dir):
                full = os.path.join(_hf_spaces_dir, d)
                if os.path.isdir(full) and d not in hf_env_names:
                    health["orphaned_dirs"].append(d)
        except OSError:
            pass
    if health["orphaned_dirs"]:
        health["warnings"].append(
            f"{len(health['orphaned_dirs'])} orphaned hf_spaces director(ies)"
        )

    # --- Backup freshness ---
    if _env_store:
        backups = _env_store.list_backups()
        if backups:
            health["last_backup"] = backups[0]["created_at"]
        else:
            health["warnings"].append("No backups exist — create one for safety")

    # --- Overall status ---
    if not _env_store or health["db_size_bytes"] == 0:
        health["status"] = "unhealthy"
    elif health["orphaned_dirs"] or health["missing_classification"]:
        health["status"] = "degraded"
    elif not health["last_backup"]:
        health["status"] = "degraded"
    else:
        health["status"] = "healthy"

    # Record snapshot
    if _env_store:
        _env_store.record_health(health)

    return health


def _tool_backup_state(label: Optional[str] = None) -> dict:
    if not _env_store:
        raise RuntimeError("Store not initialised")
    bid = _env_store.create_backup(label=label)
    return {"backup_id": bid, "label": label, "status": "created"}


def _tool_restore_state(backup_id: int) -> dict:
    if not _env_store:
        raise RuntimeError("Store not initialised")
    count = _env_store.restore_backup(backup_id)
    # Refresh the in-memory list
    if _custom_envs_ref is not None:
        _custom_envs_ref.clear()
        _custom_envs_ref.extend(_env_store.list_all())
    return {"restored_count": count, "backup_id": backup_id, "status": "restored"}


def _tool_classify_environment(name: str) -> dict:
    if not _env_store:
        raise RuntimeError("Store not initialised")
    env = _env_store.get(name)
    if not env:
        return {"error": f"Environment '{name}' not found"}
    if _classify_fn:
        result = _classify_fn(env)
        # Apply classification to stored environment
        for key in ("category", "system", "domain", "workflow", "tags"):
            if key in result:
                env[key] = result[key]
        _env_store.upsert(name, env)
        # Update in-memory list
        if _custom_envs_ref is not None:
            for i, e in enumerate(_custom_envs_ref):
                if e.get("name") == name:
                    _custom_envs_ref[i] = env
                    break
        return {"name": name, "classification": result, "status": "classified"}
    return {"name": name, "error": "Classifier not available"}


def _tool_get_stats() -> dict:
    envs = _env_store.list_all() if _env_store else []
    catalog_count = _catalog_count_fn() if _catalog_count_fn else 0

    sources: Dict[str, int] = {}
    systems: Dict[str, int] = {}
    categories: Dict[str, int] = {}
    for env in envs:
        src = env.get("source", "custom")
        sources[src] = sources.get(src, 0) + 1
        sys_ = env.get("system", "Unknown")
        systems[sys_] = systems.get(sys_, 0) + 1
        cat = env.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    backups = _env_store.list_backups() if _env_store else []

    return {
        "catalog_environments": catalog_count,
        "user_environments": len(envs),
        "total_environments": catalog_count + len(envs),
        "by_source": sources,
        "by_system": systems,
        "by_category": categories,
        "backup_count": len(backups),
        "db_size_bytes": _env_store.db_size_bytes() if _env_store else 0,
    }


# Tool dispatcher
_TOOL_DISPATCH = {
    "list_environments": lambda params: _tool_list_environments(),
    "check_health": lambda params: _tool_check_health(),
    "backup_state": lambda params: _tool_backup_state(label=params.get("label")),
    "restore_state": lambda params: _tool_restore_state(backup_id=int(params["backup_id"])),
    "classify_environment": lambda params: _tool_classify_environment(name=params["name"]),
    "get_stats": lambda params: _tool_get_stats(),
}


# ======================================================================
# API endpoints
# ======================================================================

@router.get("/tools")
async def list_tools():
    """List all available MCP agent tools."""
    return {"tools": AGENT_TOOLS}


@router.post("/invoke")
async def invoke_tool(request: Request):
    """Invoke an MCP tool by name.

    Body: ``{"tool": "check_health", "params": {}}``
    """
    body = await request.json()
    tool_name = body.get("tool", "")
    params = body.get("params", {})

    if tool_name not in _TOOL_DISPATCH:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown tool '{tool_name}'. Available: {list(AGENT_TOOLS.keys())}",
        )
    try:
        result = _TOOL_DISPATCH[tool_name](params)
        return {"tool": tool_name, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
async def health_check():
    """Quick environment health status."""
    return _tool_check_health()


@router.get("/health/history")
async def health_history(limit: int = 50):
    """Health metrics over time."""
    if not _env_store:
        return {"history": []}
    return {"history": _env_store.get_health_history(limit=limit)}


@router.get("/stats")
async def environment_stats():
    """Environment statistics."""
    return _tool_get_stats()


@router.get("/backups")
async def list_backups():
    """List all backup snapshots."""
    if not _env_store:
        return {"backups": []}
    return {"backups": _env_store.list_backups()}


@router.post("/backups")
async def create_backup(request: Request):
    """Create a new backup snapshot."""
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    label = body.get("label")
    result = _tool_backup_state(label=label)
    return result


@router.post("/backups/{backup_id}/restore")
async def restore_backup(backup_id: int):
    """Restore environments from a backup."""
    try:
        result = _tool_restore_state(backup_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
