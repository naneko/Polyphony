"""
Contains all database functions.

SQL should only exist in this file
"""
import json
import logging
import pathlib
import sqlite3
from typing import List

from polyphony.settings import DATABASE_URI

conn = sqlite3.connect(DATABASE_URI)
conn.row_factory = sqlite3.Row
c = conn.cursor()

log = logging.getLogger(__name__)


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


def get_enabled_members() -> List[sqlite3.Row]:
    c.execute("SELECT * FROM members WHERE member_enabled == 1")
    log.debug("Fetching enabled members from database")
    return c.fetchall()


def get_member_by_discord_id(discord_bot_account_id: int) -> sqlite3.Row:
    c.execute(
        "SELECT * FROM members WHERE member_account_id = ?", [discord_bot_account_id]
    )
    return c.fetchone()


def get_users() -> List[sqlite3.Row]:
    c.execute("SELECT * FROM users")
    log.debug("Fetching users from database")
    return c.fetchall()


def get_user(discord_account_id: int) -> sqlite3.Row:
    log.debug(f"Fetching user {discord_account_id} from database")
    c.execute("SELECT * FROM users WHERE discord_account_id = ?", [discord_account_id])
    return c.fetchone()


def insert_user(discord_account_id: int):
    log.debug(f"Inserting user {discord_account_id} into database")
    with conn:
        c.execute("INSERT INTO users VALUES(?)", [discord_account_id])


def suspend_member(discord_account_id: int):
    log.debug(f"Suspending user {discord_account_id} in database")
    with conn:
        c.execute(
            "UPDATE members SET member_enabled = 0 WHERE discord_account_id = ?",
            [discord_account_id],
        )


def get_member(pk_id: str) -> sqlite3.Row:
    log.debug(f"Fetching PK member {pk_id} from database")
    c.execute("SELECT * FROM members WHERE pk_member_id == ?", [pk_id])
    return c.fetchone()


def get_unused_tokens() -> List[sqlite3.Row]:
    c.execute("SELECT * FROM tokens WHERE used == 0")
    log.debug("Fetching unused tokens from database")
    return c.fetchall()


def get_used_tokens() -> List[sqlite3.Row]:
    c.execute("SELECT * FROM tokens WHERE used == 1")
    log.debug("Fetching unused tokens from database")
    return c.fetchall()


def get_token(token: str) -> sqlite3.Row:
    log.debug(f"Fetching token {token} from database")
    c.execute("SELECT * FROM tokens WHERE token = ?", [token])
    return c.fetchone()


def insert_token(token: str, used: bool):
    log.debug(f"Inserting token {token} into database")
    with conn:
        c.execute("INSERT INTO tokens VALUES(?, ?)", [token, used])


def update_token_as_used(token: str):
    log.debug(f"Setting token {token} to used")
    with conn:
        c.execute("UPDATE tokens SET used = 1 WHERE token = ?", [token])


def insert_member(
    token: str,
    pk_member_id: str,
    discord_account_id: int,
    member_account_id: int,
    member_name: str,
    display_name: str,
    pk_avatar_url: str,
    pk_proxy_tags: dict,
    pk_keep_proxy: bool,
    member_enabled: bool,
):
    log.debug(f"Inserting member {member_name} ({pk_member_id}) into database...")
    with conn:
        c.execute(
            "INSERT INTO members VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                token,
                pk_member_id,
                discord_account_id,
                member_account_id,
                member_name,
                display_name,
                pk_avatar_url,
                json.dumps(pk_proxy_tags),
                pk_keep_proxy,
                member_enabled,
            ],
        )
