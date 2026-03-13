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

# Storage backend: "mariadb" (default) or "json" (legacy for migration only)
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "mariadb")

# MariaDB connection (used for environments, scenarios, verifiers, contact form)
MARIADB_HOST = os.getenv("MARIADB_HOST", "localhost")
MARIADB_PORT = int(os.getenv("MARIADB_PORT", "3306"))
MARIADB_USER = os.getenv("MARIADB_USER", "agentwork")
MARIADB_PASSWORD = os.getenv("MARIADB_PASSWORD", "")
MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "agentwork_simulator")

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
