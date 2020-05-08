"""
Contains all database functions.

SQL should only exist in this file
"""

import logging
import sqlite3

from .settings import DATABASE_URI

conn = sqlite3.connect(DATABASE_URI)
c = conn.cursor()


def init_db():
    """Initialize database tables from schema.sql."""
    with open('./schema.sql', 'r') as schema_file:
        schema = schema_file.read()

    c.executescript(schema)
    logging.debug('Database initialized from schema.sqlite')
