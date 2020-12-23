"""
Contains all database functions.
"""
import json
import logging
import pathlib
import sqlite3

from polyphony.settings import DATABASE_URI

conn = sqlite3.connect(DATABASE_URI)
conn.row_factory = sqlite3.Row
c = conn.cursor()

log = logging.getLogger(__name__)

schema_version = 3


def init_db():
    """Initialize database tables migrations directory schema"""
    version = conn.execute("SELECT * FROM meta").fetchone()
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
            with open(
                f"{pathlib.Path().absolute()}/migrations/v{v}.sqlite", "r"
            ) as schema_file:
                schema = schema_file.read()
            conn.executescript(schema)
    conn.commit()
    log.info(f"Database initialized (Version {schema_version})")


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
