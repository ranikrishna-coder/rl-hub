"""
Persistence layer for user-created environments and scenarios.

Stores data in SQLite (gitignored by *.db rule) so it survives code
deployments that run ``git reset --hard``.

Usage
-----
    from api.persistence import EnvironmentStore, ScenarioStore, migrate_json_to_sqlite

    store = EnvironmentStore()              # uses default path
    store.upsert("my-env", {...})
    envs = store.list_all()

    scenarios = ScenarioStore()
    scenarios.upsert("my-scenario", {...})
    all_scenarios = scenarios.list_all()
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class EnvironmentStore:
    """SQLite-backed store for user / imported environments."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from api.config import ENV_STORE_DB_PATH
            db_path = ENV_STORE_DB_PATH
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_environments (
                    name       TEXT PRIMARY KEY,
                    data       TEXT NOT NULL,
                    source     TEXT DEFAULT 'custom',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS environment_backups (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_data TEXT NOT NULL,
                    env_count   INTEGER NOT NULL DEFAULT 0,
                    created_at  TEXT NOT NULL,
                    label       TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_snapshots (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot   TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    # ------------------------------------------------------------------
    # CRUD for environments
    # ------------------------------------------------------------------

    def list_all(self) -> List[Dict[str, Any]]:
        """Return every user environment as a dict."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM user_environments ORDER BY created_at"
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT data FROM user_environments WHERE name = ?", (name,)
            ).fetchone()
        return json.loads(row["data"]) if row else None

    def upsert(self, name: str, data: dict) -> None:
        now = _utcnow_iso()
        blob = json.dumps(data, default=str)
        source = data.get("source", "custom")
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO user_environments (name, data, source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       data       = excluded.data,
                       source     = excluded.source,
                       updated_at = excluded.updated_at
                """,
                (name, blob, source, now, now),
            )

    def delete(self, name: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM user_environments WHERE name = ?", (name,)
            )
        return cur.rowcount > 0

    def count(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM user_environments").fetchone()
        return row["c"]

    # ------------------------------------------------------------------
    # Backups
    # ------------------------------------------------------------------

    def create_backup(self, label: Optional[str] = None) -> int:
        """Snapshot all current environments. Returns the new backup id."""
        envs = self.list_all()
        now = _utcnow_iso()
        blob = json.dumps(envs, default=str)
        with self._conn() as conn:
            cur = conn.execute(
                """INSERT INTO environment_backups (backup_data, env_count, created_at, label)
                   VALUES (?, ?, ?, ?)""",
                (blob, len(envs), now, label),
            )
            backup_id = cur.lastrowid

            # Enforce maximum backup count
            from api.config import MAX_BACKUPS
            conn.execute(
                """DELETE FROM environment_backups
                   WHERE id NOT IN (
                       SELECT id FROM environment_backups
                       ORDER BY id DESC LIMIT ?
                   )""",
                (MAX_BACKUPS,),
            )
        return backup_id

    def restore_backup(self, backup_id: int) -> int:
        """Replace all environments with the snapshot in the given backup.
        Returns the count of restored environments.
        """
        with self._conn() as conn:
            row = conn.execute(
                "SELECT backup_data FROM environment_backups WHERE id = ?",
                (backup_id,),
            ).fetchone()
            if not row:
                raise ValueError(f"Backup {backup_id} not found")

            envs = json.loads(row["backup_data"])

            # Clear current environments and re-insert from backup
            conn.execute("DELETE FROM user_environments")
            now = _utcnow_iso()
            for env in envs:
                name = env.get("name", "")
                source = env.get("source", "custom")
                blob = json.dumps(env, default=str)
                conn.execute(
                    """INSERT INTO user_environments
                       (name, data, source, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (name, blob, source, now, now),
                )
        return len(envs)

    def list_backups(self) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT id, env_count, created_at, label
                   FROM environment_backups ORDER BY id DESC"""
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_backup(self, backup_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM environment_backups WHERE id = ?", (backup_id,)
            )
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Health snapshots
    # ------------------------------------------------------------------

    def record_health(self, snapshot: dict) -> None:
        now = _utcnow_iso()
        blob = json.dumps(snapshot, default=str)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO health_snapshots (snapshot, created_at) VALUES (?, ?)",
                (blob, now),
            )
            # Keep only last 500 snapshots
            conn.execute(
                """DELETE FROM health_snapshots
                   WHERE id NOT IN (
                       SELECT id FROM health_snapshots
                       ORDER BY id DESC LIMIT 500
                   )"""
            )

    def get_health_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT snapshot, created_at FROM health_snapshots ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for r in rows:
            s = json.loads(r["snapshot"])
            s["_recorded_at"] = r["created_at"]
            result.append(s)
        return result

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def db_size_bytes(self) -> int:
        try:
            return os.path.getsize(self.db_path)
        except OSError:
            return 0


class ScenarioStore:
    """SQLite-backed store for user / imported scenarios."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from api.config import SCENARIO_STORE_DB_PATH
            db_path = SCENARIO_STORE_DB_PATH
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_scenarios (
                    id         TEXT PRIMARY KEY,
                    data       TEXT NOT NULL,
                    product    TEXT DEFAULT '',
                    source     TEXT DEFAULT 'custom',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    # ------------------------------------------------------------------
    # CRUD for scenarios
    # ------------------------------------------------------------------

    def list_all(self) -> List[Dict[str, Any]]:
        """Return every user scenario as a dict."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM user_scenarios ORDER BY created_at"
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def get(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT data FROM user_scenarios WHERE id = ?", (scenario_id,)
            ).fetchone()
        return json.loads(row["data"]) if row else None

    def upsert(self, scenario_id: str, data: dict) -> None:
        now = _utcnow_iso()
        blob = json.dumps(data, default=str)
        product = data.get("product", "")
        source = data.get("source", "custom")
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO user_scenarios (id, data, product, source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       data       = excluded.data,
                       product    = excluded.product,
                       source     = excluded.source,
                       updated_at = excluded.updated_at
                """,
                (scenario_id, blob, product, source, now, now),
            )

    def delete(self, scenario_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM user_scenarios WHERE id = ?", (scenario_id,)
            )
        return cur.rowcount > 0

    def count(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM user_scenarios").fetchone()
        return row["c"]

    def list_by_product(self, product: str) -> List[Dict[str, Any]]:
        """Return scenarios filtered by product name."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM user_scenarios WHERE product = ? ORDER BY created_at",
                (product,),
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def db_size_bytes(self) -> int:
        try:
            return os.path.getsize(self.db_path)
        except OSError:
            return 0


class VerifierStore:
    """SQLite-backed store for user / custom verifier definitions."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            from api.config import VERIFIER_STORE_DB_PATH
            db_path = VERIFIER_STORE_DB_PATH
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_verifiers (
                    id          TEXT PRIMARY KEY,
                    data        TEXT NOT NULL,
                    environment TEXT DEFAULT '',
                    source      TEXT DEFAULT 'custom',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                )
            """)

    def list_all(self) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM user_verifiers ORDER BY created_at"
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def get(self, verifier_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT data FROM user_verifiers WHERE id = ?", (verifier_id,)
            ).fetchone()
        return json.loads(row["data"]) if row else None

    def upsert(self, verifier_id: str, data: dict) -> None:
        now = _utcnow_iso()
        blob = json.dumps(data, default=str)
        environment = data.get("environment", "")
        source = data.get("source", "custom")
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO user_verifiers (id, data, environment, source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       data        = excluded.data,
                       environment = excluded.environment,
                       source      = excluded.source,
                       updated_at  = excluded.updated_at
                """,
                (verifier_id, blob, environment, source, now, now),
            )

    def delete(self, verifier_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "DELETE FROM user_verifiers WHERE id = ?", (verifier_id,)
            )
        return cur.rowcount > 0

    def count(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM user_verifiers").fetchone()
        return row["c"]

    def list_by_environment(self, environment: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT data FROM user_verifiers WHERE environment = ? ORDER BY created_at",
                (environment,),
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def db_size_bytes(self) -> int:
        try:
            return os.path.getsize(self.db_path)
        except OSError:
            return 0


# ======================================================================
# JSON → SQLite migration
# ======================================================================

def migrate_json_to_sqlite(json_path: str, store: EnvironmentStore) -> int:
    """One-time migration: import JSON file entries into SQLite.

    Only runs when the JSON file has data AND the SQLite table is empty.
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
    # Only migrate if the SQLite store is empty (avoid duplicating)
    if store.count() > 0:
        return 0

    for env in data:
        name = env.get("name")
        if name:
            store.upsert(name, env)

    # Rename the JSON so migration doesn't re-run
    migrated_path = json_path + ".migrated"
    try:
        os.rename(json_path, migrated_path)
    except OSError:
        pass  # non-critical; the count-guard prevents re-migration anyway

    print(f"[Persistence] Migrated {len(data)} environment(s) from JSON → SQLite")
    return len(data)
