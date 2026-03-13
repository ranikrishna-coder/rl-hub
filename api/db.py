"""
MariaDB connection helper for the AgentWork Simulator.
Uses configuration from api.config (env: MARIADB_*).
"""
import pymysql
from pymysql.cursors import DictCursor
from pymysql.err import OperationalError

from api.config import (
    MARIADB_DATABASE,
    MARIADB_HOST,
    MARIADB_PASSWORD,
    MARIADB_PORT,
    MARIADB_USER,
)


def get_connection():
    """Return a MariaDB connection with DictCursor. Caller must close it."""
    try:
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
    except OperationalError as e:
        raise RuntimeError(
            "Cannot connect to MariaDB. Ensure MariaDB is running and .env has correct "
            "MARIADB_HOST, MARIADB_PORT, MARIADB_USER, MARIADB_PASSWORD, MARIADB_DATABASE. "
            f"Original error: {e}"
        ) from e


def get_cursor(conn):
    """Return a cursor for the given connection (DictCursor already set on conn)."""
    return conn.cursor()
