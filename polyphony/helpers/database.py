"""
Contains all database functions.

SQL should only exist in this file
"""

import logging
import pathlib
import sqlite3
from typing import List, Tuple

from settings import DATABASE_URI

conn = sqlite3.connect(DATABASE_URI)
c = conn.cursor()

log = logging.getLogger(__name__)


def dict_factory(cursor, row):
    """
    Return query rows as dictionaries

    Unused
    """
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


conn.row_factory = sqlite3.Row


def init_db():
    """Initialize database tables from schema.sql."""
    with open(pathlib.Path().absolute() / "schema.sqlite", "r") as schema_file:
        schema = schema_file.read()

    c.executescript(schema)
    log.debug("Database initialized from schema.sqlite")


# Future Migrations:
#   Someday the database might be in need of an update.
#   To do this, create a migrations directory and insert v1.sqlite, v2.sqlite, etc... This schema should alter the
#   existing tables if needed. Never update schema.sqlite.
#
#   Then create a function that checks the current database version from the meta table and performs the appropriate
#   migrations in order. Also make sure to update the meta table. Schema Version 0 has an empty meta table.


def get_members() -> List[sqlite3.Row]:
    c.execute("SELECT * FROM members")
    log.debug("Fetching members from database")
    return c.fetchall()


def get_users() -> List[sqlite3.Row]:
    c.execute("SELECT * FROM users")
    log.debug("Fetching users from database")
    return c.fetchall()
