"""
Persistence layer for user-created environments, scenarios, and verifiers.

Uses SQLite (stdlib) — no external database required. Data is stored in
per-collection .db files under api/data/ which already exist from before
the MariaDB migration.

Usage
-----
    from api.persistence import EnvironmentStore, ScenarioStore, migrate_json_to_store

    store = EnvironmentStore()
    store.upsert("my-env", {...})
    envs = store.list_all()
"""

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from api.config import DATA_DIR


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _conn(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


class EnvironmentStore:
    """SQLite-backed store for user / imported environments."""

    def __init__(self, db_path: Optional[str] = None):
        self._db = db_path or os.path.join(DATA_DIR, "environments.db")
        self._init_db()

    def _init_db(self) -> None:
        with _conn(self._db) as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS user_environments (
                    name       TEXT PRIMARY KEY,
                    data       TEXT NOT NULL,
                    source     TEXT DEFAULT 'custom',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS environment_backups (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_data TEXT NOT NULL,
                    env_count   INTEGER NOT NULL DEFAULT 0,
                    created_at  TEXT NOT NULL,
                    label       TEXT
                );
                CREATE TABLE IF NOT EXISTS health_snapshots (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot   TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)

    # ------------------------------------------------------------------
    # Environments
    # ------------------------------------------------------------------

    def list_all(self) -> List[Dict[str, Any]]:
        with _conn(self._db) as c:
            rows = c.execute(
                "SELECT data FROM user_environments ORDER BY created_at"
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        with _conn(self._db) as c:
            row = c.execute(
                "SELECT data FROM user_environments WHERE name = ?", (name,)
            ).fetchone()
        return json.loads(row["data"]) if row else None

    def upsert(self, name: str, data: dict) -> None:
        now = _utcnow_iso()
        blob = json.dumps(data, default=str)
        source = data.get("source", "custom")
        with _conn(self._db) as c:
            c.execute(
                """INSERT INTO user_environments (name, data, source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       data       = excluded.data,
                       source     = excluded.source,
                       updated_at = excluded.updated_at""",
                (name, blob, source, now, now),
            )

    def batch_upsert(self, envs: List[Dict[str, Any]]) -> int:
        now = _utcnow_iso()
        rows = [
            (env["name"], json.dumps(env, default=str), env.get("source", "custom"), now, now)
            for env in envs if env.get("name")
        ]
        if not rows:
            return 0
        with _conn(self._db) as c:
            c.executemany(
                """INSERT INTO user_environments (name, data, source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       data       = excluded.data,
                       source     = excluded.source,
                       updated_at = excluded.updated_at""",
                rows,
            )
        return len(rows)

    def delete(self, name: str) -> bool:
        with _conn(self._db) as c:
            c.execute("DELETE FROM user_environments WHERE name = ?", (name,))
            return c.execute("SELECT changes()").fetchone()[0] > 0

    def count(self) -> int:
        with _conn(self._db) as c:
            return c.execute("SELECT COUNT(*) FROM user_environments").fetchone()[0]

    # ------------------------------------------------------------------
    # Backups
    # ------------------------------------------------------------------

    def create_backup(self, label: Optional[str] = None) -> int:
        from api.config import MAX_BACKUPS
        envs = self.list_all()
        now = _utcnow_iso()
        with _conn(self._db) as c:
            cur = c.execute(
                "INSERT INTO environment_backups (backup_data, env_count, created_at, label) VALUES (?, ?, ?, ?)",
                (json.dumps(envs, default=str), len(envs), now, label),
            )
            backup_id = cur.lastrowid
            c.execute(
                """DELETE FROM environment_backups WHERE id NOT IN (
                       SELECT id FROM environment_backups ORDER BY id DESC LIMIT ?
                   )""",
                (MAX_BACKUPS,),
            )
        return backup_id

    def restore_backup(self, backup_id: int) -> int:
        with _conn(self._db) as c:
            row = c.execute(
                "SELECT backup_data FROM environment_backups WHERE id = ?", (backup_id,)
            ).fetchone()
        if not row:
            raise ValueError(f"Backup {backup_id} not found")
        envs = json.loads(row["backup_data"])
        now = _utcnow_iso()
        with _conn(self._db) as c:
            c.execute("DELETE FROM user_environments")
            c.executemany(
                """INSERT INTO user_environments (name, data, source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    (env.get("name", ""), json.dumps(env, default=str),
                     env.get("source", "custom"), now, now)
                    for env in envs if env.get("name")
                ],
            )
        return len(envs)

    def list_backups(self) -> List[Dict[str, Any]]:
        with _conn(self._db) as c:
            rows = c.execute(
                "SELECT id, env_count, created_at, label FROM environment_backups ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_backup(self, backup_id: int) -> bool:
        with _conn(self._db) as c:
            c.execute("DELETE FROM environment_backups WHERE id = ?", (backup_id,))
            return c.execute("SELECT changes()").fetchone()[0] > 0

    # ------------------------------------------------------------------
    # Health snapshots
    # ------------------------------------------------------------------

    def record_health(self, snapshot: dict) -> None:
        now = _utcnow_iso()
        with _conn(self._db) as c:
            c.execute(
                "INSERT INTO health_snapshots (snapshot, created_at) VALUES (?, ?)",
                (json.dumps(snapshot, default=str), now),
            )
            c.execute(
                """DELETE FROM health_snapshots WHERE id NOT IN (
                       SELECT id FROM health_snapshots ORDER BY id DESC LIMIT 500
                   )"""
            )

    def get_health_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with _conn(self._db) as c:
            rows = c.execute(
                "SELECT snapshot, created_at FROM health_snapshots ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for r in rows:
            s = json.loads(r["snapshot"])
            s["_recorded_at"] = r["created_at"]
            result.append(s)
        return result

    def db_size_bytes(self) -> int:
        try:
            return os.path.getsize(self._db) if os.path.exists(self._db) else 0
        except Exception:
            return 0


class ScenarioStore:
    """SQLite-backed store for user / imported scenarios."""

    def __init__(self, db_path: Optional[str] = None):
        self._db = db_path or os.path.join(DATA_DIR, "scenarios.db")
        self._init_db()

    def _init_db(self) -> None:
        with _conn(self._db) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS user_scenarios (
                    id         TEXT PRIMARY KEY,
                    data       TEXT NOT NULL,
                    product    TEXT DEFAULT '',
                    source     TEXT DEFAULT 'custom',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

    def list_all(self) -> List[Dict[str, Any]]:
        with _conn(self._db) as c:
            rows = c.execute(
                "SELECT data FROM user_scenarios ORDER BY created_at"
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def get(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        with _conn(self._db) as c:
            row = c.execute(
                "SELECT data FROM user_scenarios WHERE id = ?", (scenario_id,)
            ).fetchone()
        return json.loads(row["data"]) if row else None

    def upsert(self, scenario_id: str, data: dict) -> None:
        now = _utcnow_iso()
        blob = json.dumps(data, default=str)
        product = data.get("product", "")
        source = data.get("source", "custom")
        with _conn(self._db) as c:
            c.execute(
                """INSERT INTO user_scenarios (id, data, product, source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       data       = excluded.data,
                       product    = excluded.product,
                       source     = excluded.source,
                       updated_at = excluded.updated_at""",
                (scenario_id, blob, product, source, now, now),
            )

    def delete(self, scenario_id: str) -> bool:
        with _conn(self._db) as c:
            c.execute("DELETE FROM user_scenarios WHERE id = ?", (scenario_id,))
            return c.execute("SELECT changes()").fetchone()[0] > 0

    def count(self) -> int:
        with _conn(self._db) as c:
            return c.execute("SELECT COUNT(*) FROM user_scenarios").fetchone()[0]

    def list_by_product(self, product: str) -> List[Dict[str, Any]]:
        with _conn(self._db) as c:
            rows = c.execute(
                "SELECT data FROM user_scenarios WHERE product = ? ORDER BY created_at",
                (product,),
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def db_size_bytes(self) -> int:
        try:
            return os.path.getsize(self._db) if os.path.exists(self._db) else 0
        except Exception:
            return 0


class VerifierStore:
    """SQLite-backed store for user / custom verifier definitions."""

    def __init__(self, db_path: Optional[str] = None):
        self._db = db_path or os.path.join(DATA_DIR, "verifiers.db")
        self._init_db()

    def _init_db(self) -> None:
        with _conn(self._db) as c:
            c.execute("""
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
        with _conn(self._db) as c:
            rows = c.execute(
                "SELECT data FROM user_verifiers ORDER BY created_at"
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def get(self, verifier_id: str) -> Optional[Dict[str, Any]]:
        with _conn(self._db) as c:
            row = c.execute(
                "SELECT data FROM user_verifiers WHERE id = ?", (verifier_id,)
            ).fetchone()
        return json.loads(row["data"]) if row else None

    def upsert(self, verifier_id: str, data: dict) -> None:
        now = _utcnow_iso()
        blob = json.dumps(data, default=str)
        environment = data.get("environment", "")
        source = data.get("source", "custom")
        with _conn(self._db) as c:
            c.execute(
                """INSERT INTO user_verifiers (id, data, environment, source, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       data        = excluded.data,
                       environment = excluded.environment,
                       source      = excluded.source,
                       updated_at  = excluded.updated_at""",
                (verifier_id, blob, environment, source, now, now),
            )

    def delete(self, verifier_id: str) -> bool:
        with _conn(self._db) as c:
            c.execute("DELETE FROM user_verifiers WHERE id = ?", (verifier_id,))
            return c.execute("SELECT changes()").fetchone()[0] > 0

    def count(self) -> int:
        with _conn(self._db) as c:
            return c.execute("SELECT COUNT(*) FROM user_verifiers").fetchone()[0]

    def list_by_environment(self, environment: str) -> List[Dict[str, Any]]:
        with _conn(self._db) as c:
            rows = c.execute(
                "SELECT data FROM user_verifiers WHERE environment = ? ORDER BY created_at",
                (environment,),
            ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def db_size_bytes(self) -> int:
        try:
            return os.path.getsize(self._db) if os.path.exists(self._db) else 0
        except Exception:
            return 0


# ======================================================================
# JSON → Store migration (legacy: import from old JSON file)
# ======================================================================

def migrate_json_to_store(json_path: str, store: EnvironmentStore) -> int:
    """One-time migration: import JSON file entries into the store.

    Only runs when the JSON file has data AND the store is empty.
    After migration the JSON file is renamed to ``*.json.migrated``.
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

    print(f"[Persistence] Migrated {len(data)} environment(s) from JSON → SQLite")
    return len(data)
