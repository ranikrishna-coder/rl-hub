"""
Centralized configuration for the AgentWork Simulator.
Reads from environment variables with sensible defaults.
"""
import os

# Load .env from project root so MARIADB_*, SSO_*, etc. are set when running uvicorn
try:
    from dotenv import load_dotenv
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_root, ".env"))
except ImportError:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(API_DIR, "data")
HF_SPACES_DIR = os.path.join(PROJECT_ROOT, "hf_spaces")

# Storage backend: "json" (default) – no external DB required
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "json")

# MariaDB connection (used for environments, scenarios, verifiers, contact form)
MARIADB_HOST = os.getenv("MARIADB_HOST", "localhost")
MARIADB_PORT = int(os.getenv("MARIADB_PORT", "3306"))
MARIADB_USER = os.getenv("MARIADB_USER", "agentwork")
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD", "")
MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "agentwork_simulator")
# Connection pool size (reduces latency by reusing connections)
MARIADB_POOL_SIZE = int(os.getenv("MARIADB_POOL_SIZE", "10"))

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

# SQLite database path for user tool definitions (gitignored by *.db rule)
TOOL_STORE_DB_PATH = os.getenv(
    "TOOL_STORE_DB_PATH",
    os.path.join(DATA_DIR, "tools.db"),
)

# SQLite database path for training run records (gitignored by *.db rule)
TRAINING_RUN_DB_PATH = os.getenv(
    "TRAINING_RUN_DB_PATH",
    os.path.join(DATA_DIR, "training_runs.db"),
)

# SQLite database path for episode rollout records (gitignored by *.db rule)
ROLLOUT_STORE_DB_PATH = os.getenv(
    "ROLLOUT_STORE_DB_PATH",
    os.path.join(DATA_DIR, "rollouts.db"),
)

# SQLite database path for contact form submissions (gitignored by *.db rule)
CONTACT_STORE_DB_PATH = os.getenv(
    "CONTACT_STORE_DB_PATH",
    os.path.join(DATA_DIR, "contact.db"),
)

# SQLite database path for governance configurations (gitignored by *.db rule)
GOVERNANCE_STORE_DB_PATH = os.getenv(
    "GOVERNANCE_STORE_DB_PATH",
    os.path.join(DATA_DIR, "governance.db"),
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
