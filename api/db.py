"""
Database connection stub.

MariaDB has been removed. Persistence is now handled via JSON files
(see api/persistence.py). This module is kept as a stub so that any
legacy imports do not cause ImportError.
"""


def get_connection():
    raise RuntimeError(
        "MariaDB has been removed. Persistence now uses JSON file storage. "
        "See api/persistence.py."
    )


def get_cursor(conn):
    raise RuntimeError("MariaDB has been removed.")
