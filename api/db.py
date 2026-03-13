"""
MariaDB connection helper for the AgentWork Simulator.
Uses configuration from api.config (env: MARIADB_*).
Connections are pooled so each request reuses a connection instead of opening a new one.
"""
import pymysql
from pymysql.cursors import DictCursor
from pymysql.err import OperationalError

from api.config import (
    MARIADB_DATABASE,
    MARIADB_HOST,
    MARIADB_PASSWORD,
    MARIADB_POOL_SIZE,
    MARIADB_PORT,
    MARIADB_USER,
)


def _create_connection():
    """Create a single MariaDB connection (used by the pool)."""
    return pymysql.connect(
        host=MARIADB_HOST,
        port=MARIADB_PORT,
        user=MARIADB_USER,
        password=MARIADB_PASSWORD,
        database=MARIADB_DATABASE,
        cursorclass=DictCursor,
        autocommit=False,
        connect_timeout=10,
        ssl=False,  # server does not support SSL; use plain TCP
    )


try:
    from DBUtils.PooledDB import PooledDB

    _pool = PooledDB(
        creator=_create_connection,
        maxconnections=MARIADB_POOL_SIZE,
        mincached=0,       # don't pre-create connections at import time
        maxcached=MARIADB_POOL_SIZE,
        blocking=True,
        maxusage=None,
        ping=1,  # check connection is alive when taken from pool
    )
except (ImportError, Exception):
    # ImportError  → DBUtils not installed
    # Exception    → DB unreachable at startup (bad creds, host down, etc.)
    _pool = None


def get_connection():
    """Return a MariaDB connection with DictCursor. Caller must close it (returns to pool)."""
    try:
        if _pool is not None:
            return _pool.connection()
        return _create_connection()
    except OperationalError as e:
        raise RuntimeError(
            "Cannot connect to MariaDB. Ensure MariaDB is running and .env has correct "
            "MARIADB_HOST, MARIADB_PORT, MARIADB_USER, MARIADB_PASSWORD, MARIADB_DATABASE. "
            f"Original error: {e}"
        ) from e


def get_cursor(conn):
    """Return a cursor for the given connection (DictCursor already set on conn)."""
    return conn.cursor()
