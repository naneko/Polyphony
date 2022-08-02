"""
Contains all database functions.
"""
import json
import logging
import os
import shutil
from pathlib import Path
import sqlite3

from polyphony.settings import DATABASE_URI

conn = sqlite3.connect(DATABASE_URI)
conn.row_factory = sqlite3.Row
c = conn.cursor()

log = logging.getLogger(__name__)

schema_version = 5


def init_db():
    """Initialize database tables migrations directory schema"""
    try:
        version = conn.execute("SELECT * FROM meta").fetchone()
    except sqlite3.OperationalError:
        log.warning(
            "Database version not found in database. This probably means a new database is being created. Initializing from version 0."
        )
        with open(
            f"{Path(os.path.dirname(os.path.abspath(__file__))).parent.absolute()}/migrations/v0.sqlite", "r"
        ) as schema_file:
            schema = schema_file.read()
        conn.executescript(schema)
        conn.commit()
        version = None

    if version is not None:
        version = version["version"]
    else:
        version = 0

    if version > schema_version:
        log.error(
            f"Database version {version} is newer than version {schema_version} supported by this version of Polyphony. Polyphony does not support downgrading database versions. Please update Polyphony."
        )
        exit()

    for v in range(0, schema_version + 1):
        if version < v:
            log.info(f"Updating database to schema version {v}")
            shutil.copyfile(DATABASE_URI, f"{DATABASE_URI}.v{version}.bak")
            with open(
                f"{Path(os.path.dirname(os.path.abspath(__file__))).parent.absolute()}/migrations/v{v}.sqlite", "r"
            ) as schema_file:
                schema = schema_file.read()
            conn.executescript(schema)
    conn.commit()
    log.info(f"Database initialized (Version {schema_version})")
    return schema_version


def insert_member(
    token: str,
    pk_member_id: str,
    main_account_id: int,
    id: int,
    member_name: str,
    display_name: str,
    pk_avatar_url: str,
    pk_proxy_tags: dict,
    pk_keep_proxy: bool,
    member_enabled: bool,
):
    log.debug(f"Inserting member {member_name} ({pk_member_id}) into database...")
    conn.execute(
        "INSERT INTO members VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            token,
            pk_member_id,
            main_account_id,
            id,
            member_name,
            display_name,
            pk_avatar_url,
            json.dumps(pk_proxy_tags),
            pk_keep_proxy,
            member_enabled,
            None,
        ],
    )
    conn.commit()
