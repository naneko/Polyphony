"""
Contains all configuration for bot.

All settings should be loaded from enviroment variables.
For development, create a .env file in the package and make sure python-dotenv is installed.
"""

import logging
import os

# from polyphony.helpers.helpers import DiscordLoggerHandler
from pathlib import Path

log = logging.getLogger(__name__)

# Check for python-dotenv
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    logging.debug("python-dotenv not loaded. Hope you set your environment variables.")

# Get config from environment variables (returns none if not found)
DEBUG: bool = bool(os.getenv("DEBUG", False))
TOKEN: str = os.getenv("TOKEN")
# TODO: Replace guild-specific checks to just use configured Guild ID (and once this happens, don't allow the bot to start without it)
# TODO: Log warning when running in guild that is not specified guild ID
GUILD_ID: int = int(os.getenv("GUILD_ID", 0))
DATABASE_URI: str = os.getenv("DATABASE_URI")
MODERATOR_ROLES: list = os.getenv("MODERATOR_ROLES", "Moderator,Moderators").split(",")
INSTANCE_ADD_ROLES: list = os.getenv("INSTANCE_ADD_ROLES", "").split(",")
INSTANCE_REMOVE_ROLES: list = os.getenv("INSTANCE_REMOVE_ROLES", "").split(",")
ALWAYS_SYNC_ROLES: list = os.getenv("ALWAYS_SYNC_ROLES", "").split(",")
NEVER_SYNC_ROLES: list = os.getenv("NEVER_SYNC_ROLES", "").split(",")
DISABLE_ROLESYNC_ROLES: list = os.getenv("DISABLE_ROLESYNC_ROLES", "").split(",")
DEFAULT_INSTANCE_PERMS: int = os.getenv("DEFAULT_INSTANCE_PERMS", 0)
COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", ";;")
ADMIN_LOGS_CHANNEL_ID: int = int(os.getenv("ADMIN_LOGS_CHANNEL_ID", 0))
# 0 to prevent accidental "None" value from API:
DELETE_LOGS_CHANNEL_ID: int = int(os.getenv("DELETE_LOGS_CHANNEL_ID", 0))
DELETE_LOGS_USER_ID: int = int(os.getenv("DELETE_LOGS_USER_ID", 0))
SYNC_BATCH_SIZE: int = int(os.getenv('SYNC_BATCH_SIZE', 5))
EMOTE_CACHE_MAX: int = int(os.getenv('EMOTE_CACHE_MAX', 5))

# Debug Mode Setup
if DEBUG is True:
    # Set Logger Level
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("discord")
    logger.setLevel(logging.WARN)
    logger = logging.getLogger("websockets")
    logger.setLevel(logging.WARN)
    log.info("Debug Mode Enabled")

# Check for token and exit if not exists
if TOKEN is None:
    log.error("Discord API token not set")
    exit()

# Check for database URI
if DATABASE_URI is None:
    log.warning(
        "Database URI was not set and hence is in the default location in the root directory of Polyphony"
    )
    DATABASE_URI = str(f"{Path(os.path.dirname(os.path.realpath(__file__))).parent.absolute()}/polyphony.db")

if GUILD_ID == 0:
    log.error("Guild ID is not set")
    exit()