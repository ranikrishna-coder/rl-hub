"""
Persistence layer for user-created environments, scenarios, and verifiers.

Stores data in MariaDB (configured via MARIADB_* env vars) so it survives
code deployments and supports multi-instance deployments.

Usage
-----
    from api.persistence import EnvironmentStore, ScenarioStore, migrate_json_to_store

    store = EnvironmentStore()
    store.upsert("my-env", {...})
    envs = store.list_all()

    scenarios = ScenarioStore()
    scenarios.upsert("my-scenario", {...})
    all_scenarios = scenarios.list_all()
"""

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from api.db import get_connection


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@contextmanager
def _conn():
    """Context manager yielding a MariaDB connection with DictCursor. Commits on success."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class EnvironmentStore:
    """MariaDB-backed store for user / imported environments."""

    def __init__(self, db_path: Optional[str] = None):
        # db_path ignored; kept for API compatibility
        self._init_db()

    def _init_db(self) -> None:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_environments (
                        name       VARCHAR(255) PRIMARY KEY,
                        data       LONGTEXT NOT NULL,
                        source     VARCHAR(64) DEFAULT 'custom',
                        created_at VARCHAR(32) NOT NULL,
                        updated_at VARCHAR(32) NOT NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS environment_backups (
                        id          INT AUTO_INCREMENT PRIMARY KEY,
                        backup_data LONGTEXT NOT NULL,
                        env_count   INT NOT NULL DEFAULT 0,
                        created_at  VARCHAR(32) NOT NULL,
                        label       VARCHAR(255) NULL
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS health_snapshots (
                        id         INT AUTO_INCREMENT PRIMARY KEY,
                        snapshot   LONGTEXT NOT NULL,
                        created_at VARCHAR(32) NOT NULL
                    )
                """)

    def list_all(self) -> List[Dict[str, Any]]:
        """Return every user environment as a dict."""
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM user_environments ORDER BY created_at"
                )
                rows = cur.fetchall()
        return [json.loads(r["data"]) for r in rows]

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM user_environments WHERE name = %s",
                    (name,),
                )
                row = cur.fetchone()
        return json.loads(row["data"]) if row else None

    def upsert(self, name: str, data: dict) -> None:
        now = _utcnow_iso()
        blob = json.dumps(data, default=str)
        source = data.get("source", "custom")
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO user_environments (name, data, source, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                           data       = VALUES(data),
                           source     = VALUES(source),
                           updated_at = VALUES(updated_at)
                    """,
                    (name, blob, source, now, now),
                )

    def delete(self, name: str) -> bool:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_environments WHERE name = %s",
                    (name,),
                )
                return cur.rowcount > 0

    def count(self) -> int:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM user_environments")
                row = cur.fetchone()
        return row["c"] if row else 0

    def create_backup(self, label: Optional[str] = None) -> int:
        """Snapshot all current environments. Returns the new backup id."""
        envs = self.list_all()
        now = _utcnow_iso()
        blob = json.dumps(envs, default=str)
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO environment_backups (backup_data, env_count, created_at, label)
                       VALUES (%s, %s, %s, %s)""",
                    (blob, len(envs), now, label),
                )
                backup_id = cur.lastrowid
                from api.config import MAX_BACKUPS
                cur.execute(
                    """DELETE FROM environment_backups
                       WHERE id NOT IN (
                           SELECT id FROM (
                               SELECT id FROM environment_backups
                               ORDER BY id DESC LIMIT %s
                           ) AS t
                       )""",
                    (MAX_BACKUPS,),
                )
        return backup_id

    def restore_backup(self, backup_id: int) -> int:
        """Replace all environments with the snapshot in the given backup."""
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT backup_data FROM environment_backups WHERE id = %s",
                    (backup_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Backup {backup_id} not found")

                envs = json.loads(row["backup_data"])
                cur.execute("DELETE FROM user_environments")
                now = _utcnow_iso()
                for env in envs:
                    name = env.get("name", "")
                    source = env.get("source", "custom")
                    blob = json.dumps(env, default=str)
                    cur.execute(
                        """INSERT INTO user_environments
                           (name, data, source, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (name, blob, source, now, now),
                    )
        return len(envs)

    def list_backups(self) -> List[Dict[str, Any]]:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT id, env_count, created_at, label
                       FROM environment_backups ORDER BY id DESC"""
                )
                rows = cur.fetchall()
        return [dict(r) for r in rows]

    def delete_backup(self, backup_id: int) -> bool:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM environment_backups WHERE id = %s",
                    (backup_id,),
                )
                return cur.rowcount > 0

    def record_health(self, snapshot: dict) -> None:
        now = _utcnow_iso()
        blob = json.dumps(snapshot, default=str)
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO health_snapshots (snapshot, created_at) VALUES (%s, %s)",
                    (blob, now),
                )
                cur.execute(
                    """DELETE FROM health_snapshots
                       WHERE id NOT IN (
                           SELECT id FROM (
                               SELECT id FROM health_snapshots
                               ORDER BY id DESC LIMIT 500
                           ) AS t
                       )"""
                )

    def get_health_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT snapshot, created_at FROM health_snapshots ORDER BY id DESC LIMIT %s",
                    (limit,),
                )
                rows = cur.fetchall()
        result = []
        for r in rows:
            s = json.loads(r["snapshot"])
            s["_recorded_at"] = r["created_at"]
            result.append(s)
        return result

    def db_size_bytes(self) -> int:
        """Approximate size of environment tables in bytes (MariaDB)."""
        try:
            with _conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT COALESCE(SUM(data_length + index_length), 0) AS size
                           FROM information_schema.tables
                           WHERE table_schema = DATABASE()
                             AND table_name IN ('user_environments', 'environment_backups', 'health_snapshots')"""
                    )
                    row = cur.fetchone()
                    return int(row["size"]) if row and row.get("size") else 0
        except Exception:
            return 0


class ScenarioStore:
    """MariaDB-backed store for user / imported scenarios."""

    def __init__(self, db_path: Optional[str] = None):
        # db_path ignored; kept for API compatibility
        self._init_db()

    def _init_db(self) -> None:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_scenarios (
                        id         VARCHAR(255) PRIMARY KEY,
                        data       LONGTEXT NOT NULL,
                        product    VARCHAR(255) DEFAULT '',
                        source     VARCHAR(64) DEFAULT 'custom',
                        created_at VARCHAR(32) NOT NULL,
                        updated_at VARCHAR(32) NOT NULL
                    )
                """)

    def list_all(self) -> List[Dict[str, Any]]:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM user_scenarios ORDER BY created_at"
                )
                rows = cur.fetchall()
        return [json.loads(r["data"]) for r in rows]

    def get(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM user_scenarios WHERE id = %s",
                    (scenario_id,),
                )
                row = cur.fetchone()
        return json.loads(row["data"]) if row else None

    def upsert(self, scenario_id: str, data: dict) -> None:
        now = _utcnow_iso()
        blob = json.dumps(data, default=str)
        product = data.get("product", "")
        source = data.get("source", "custom")
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO user_scenarios (id, data, product, source, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                           data       = VALUES(data),
                           product    = VALUES(product),
                           source     = VALUES(source),
                           updated_at = VALUES(updated_at)
                    """,
                    (scenario_id, blob, product, source, now, now),
                )

    def delete(self, scenario_id: str) -> bool:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_scenarios WHERE id = %s",
                    (scenario_id,),
                )
                return cur.rowcount > 0

    def count(self) -> int:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM user_scenarios")
                row = cur.fetchone()
        return row["c"] if row else 0

    def list_by_product(self, product: str) -> List[Dict[str, Any]]:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM user_scenarios WHERE product = %s ORDER BY created_at",
                    (product,),
                )
                rows = cur.fetchall()
        return [json.loads(r["data"]) for r in rows]

    def db_size_bytes(self) -> int:
        try:
            with _conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT COALESCE(SUM(data_length + index_length), 0) AS size
                           FROM information_schema.tables
                           WHERE table_schema = DATABASE()
                             AND table_name = 'user_scenarios'"""
                    )
                    row = cur.fetchone()
                    return int(row["size"]) if row and row.get("size") else 0
        except Exception:
            return 0


class VerifierStore:
    """MariaDB-backed store for user / custom verifier definitions."""

    def __init__(self, db_path: Optional[str] = None):
        # db_path ignored; kept for API compatibility
        self._init_db()

    def _init_db(self) -> None:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_verifiers (
                        id          VARCHAR(255) PRIMARY KEY,
                        data        LONGTEXT NOT NULL,
                        environment VARCHAR(255) DEFAULT '',
                        source      VARCHAR(64) DEFAULT 'custom',
                        created_at  VARCHAR(32) NOT NULL,
                        updated_at  VARCHAR(32) NOT NULL
                    )
                """)
                # Ensure columns exist (migrate from older schema)
                cur.execute(
                    """SELECT COLUMN_NAME FROM information_schema.COLUMNS
                       WHERE table_schema = DATABASE() AND table_name = 'user_verifiers'"""
                )
                cols = {r["COLUMN_NAME"] for r in cur.fetchall()}
                if "environment" not in cols:
                    cur.execute(
                        "ALTER TABLE user_verifiers ADD COLUMN environment VARCHAR(255) DEFAULT ''"
                    )
                if "source" not in cols:
                    cur.execute(
                        "ALTER TABLE user_verifiers ADD COLUMN source VARCHAR(64) DEFAULT 'custom'"
                    )

    def list_all(self) -> List[Dict[str, Any]]:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM user_verifiers ORDER BY created_at"
                )
                rows = cur.fetchall()
        return [json.loads(r["data"]) for r in rows]

    def get(self, verifier_id: str) -> Optional[Dict[str, Any]]:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM user_verifiers WHERE id = %s",
                    (verifier_id,),
                )
                row = cur.fetchone()
        return json.loads(row["data"]) if row else None

    def upsert(self, verifier_id: str, data: dict) -> None:
        now = _utcnow_iso()
        blob = json.dumps(data, default=str)
        environment = data.get("environment", "")
        source = data.get("source", "custom")
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO user_verifiers (id, data, environment, source, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON DUPLICATE KEY UPDATE
                           data        = VALUES(data),
                           environment = VALUES(environment),
                           source      = VALUES(source),
                           updated_at  = VALUES(updated_at)
                    """,
                    (verifier_id, blob, environment, source, now, now),
                )

    def delete(self, verifier_id: str) -> bool:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM user_verifiers WHERE id = %s",
                    (verifier_id,),
                )
                return cur.rowcount > 0

    def count(self) -> int:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) AS c FROM user_verifiers")
                row = cur.fetchone()
        return row["c"] if row else 0

    def list_by_environment(self, environment: str) -> List[Dict[str, Any]]:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM user_verifiers WHERE environment = %s ORDER BY created_at",
                    (environment,),
                )
                rows = cur.fetchall()
        return [json.loads(r["data"]) for r in rows]

    def db_size_bytes(self) -> int:
        try:
            with _conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT COALESCE(SUM(data_length + index_length), 0) AS size
                           FROM information_schema.tables
                           WHERE table_schema = DATABASE()
                             AND table_name = 'user_verifiers'"""
                    )
                    row = cur.fetchone()
                    return int(row["size"]) if row and row.get("size") else 0
        except Exception:
            return 0


# ======================================================================
# JSON → MariaDB migration (legacy: import from old JSON file)
# ======================================================================

def migrate_json_to_store(json_path: str, store: EnvironmentStore) -> int:
    """One-time migration: import JSON file entries into MariaDB.

    Only runs when the JSON file has data AND the store table is empty.
    After migration the JSON file is renamed to ``*.json.migrated``.

    Returns the count of migrated environments.
    """
    if not os.path.exists(json_path):
        return 0
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
    except Exception:
        return 0
    if not data or not isinstance(data, list):
        return 0
    if store.count() > 0:
        return 0

    for env in data:
        name = env.get("name")
        if name:
            store.upsert(name, env)

    migrated_path = json_path + ".migrated"
    try:
        os.rename(json_path, migrated_path)
    except OSError:
        pass

    print(f"[Persistence] Migrated {len(data)} environment(s) from JSON → MariaDB")
    return len(data)
