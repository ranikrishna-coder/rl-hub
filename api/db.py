"""
MariaDB connection helper for the AgentWork Simulator.
Uses configuration from api.config (env: MARIADB_*).
"""
import pymysql
from pymysql.cursors import DictCursor

from api.config import (
    MARIADB_DATABASE,
    MARIADB_HOST,
    MARIADB_PASSWORD,
    MARIADB_PORT,
    MARIADB_USER,
)


def get_connection():
    """Return a MariaDB connection with DictCursor. Caller must close it."""
    return pymysql.connect(
        host=MARIADB_HOST,
        port=MARIADB_PORT,
        user=MARIADB_USER,
        password=MARIADB_PASSWORD,
        database=MARIADB_DATABASE,
        cursorclass=DictCursor,
        autocommit=False,
    )


def get_cursor(conn):
    """Return a cursor for the given connection (DictCursor already set on conn)."""
    return conn.cursor()
