"""
Centralized configuration for the AgentWork Simulator.
Reads from environment variables with sensible defaults.
"""
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(API_DIR, "data")
HF_SPACES_DIR = os.path.join(PROJECT_ROOT, "hf_spaces")

# Storage backend: "sqlite" (default, survives git deployments) or "json" (legacy)
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "sqlite")

# SQLite database path for user environment state (gitignored by *.db rule)
ENV_STORE_DB_PATH = os.getenv(
    "ENV_STORE_DB_PATH",
    os.path.join(DATA_DIR, "environments.db"),
)

# SQLite database path for user scenario state (gitignored by *.db rule)
SCENARIO_STORE_DB_PATH = os.getenv(
    "SCENARIO_STORE_DB_PATH",
    os.path.join(DATA_DIR, "scenarios.db"),
)

# SQLite database path for user verifier state (gitignored by *.db rule)
VERIFIER_STORE_DB_PATH = os.getenv(
    "VERIFIER_STORE_DB_PATH",
    os.path.join(DATA_DIR, "verifiers.db"),
)

# Legacy JSON path (used for migration and as fallback)
CUSTOM_ENV_JSON_PATH = os.path.join(DATA_DIR, "custom_environments.json")

# Backup settings
MAX_BACKUPS = int(os.getenv("MAX_BACKUPS", "20"))
AUTO_BACKUP_ON_STARTUP = os.getenv("AUTO_BACKUP_ON_STARTUP", "true").lower() == "true"

# Health check settings
HEALTH_SNAPSHOT_INTERVAL = int(os.getenv("HEALTH_SNAPSHOT_INTERVAL", "300"))  # seconds

# Server settings (existing, centralised for reference)
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
