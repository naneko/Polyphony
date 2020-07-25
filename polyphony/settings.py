"""
Contains all configuration for bot.

All settings should be loaded from enviroment variables.
For development, create a .env file in the package and make sure python-dotenv is installed.
"""

import logging
import os

# from polyphony.helpers.helpers import DiscordLoggerHandler

log = logging.getLogger(__name__)

# Check for python-dotenv
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    logging.debug("python-dotenv not loaded. Hope you set your environment variables.")

# Get config from environment variables (returns none if not found)
DEBUG = bool(os.getenv("DEBUG", False))
TOKEN = os.getenv("TOKEN")
DATABASE_URI = os.getenv("DATABASE_URI")
MODERATOR_ROLES = os.getenv("MODERATOR_ROLES", ["Moderator", "Moderators"])
ALWAYS_SYNC_ROLES = os.getenv("ALWAYS_SYNC_ROLES", [])
NEVER_SYNC_ROLES = os.getenv("NEVER_SYNC_ROLES", [])
DEFAULT_INSTANCE_PERMS = os.getenv("DEFAULT_INSTANCE_PERMS", 0)
SUSPEND_ON_LEAVE = os.getenv("SUSPEND_ON_LEAVE", True)  # TODO: Implement
SUSPEND_INACTIVE_DAYS = os.getenv("SUSPEND_INACTIVE_DAYS", 14)
LOGGING_CHANNEL_ID = os.getenv("LOGGING_CHANNEL_ID")
COMMAND_PREFIX = os.getenv("COMMAND_PREFIX", ";;")
# 0 to prevent accidental "None" value from API:
DELETE_LOGS_CHANNEL_ID = os.getenv("DELETE_LOGS_CHANNEL_ID", 0)
DELETE_LOGS_USER_ID = os.getenv("DELETE_LOGS_USER_ID", 0)

# Debug Mode Setup
if DEBUG is True:
    # Set Logger Level
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("discord")
    logger.setLevel(logging.WARN)
    logger = logging.getLogger("websockets")
    logger.setLevel(logging.WARN)
    log.info("Debug Mode Enabled")
else:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("discord")
    logger.setLevel(logging.WARN)
    logger = logging.getLogger("websockets")
    logger.setLevel(logging.WARN)

# Check for token and exit if not exists
if TOKEN is None:
    log.error("Discord API token not set")
    exit()

# Check for database URI
if DATABASE_URI is None:
    log.warning(
        "Database URI was not set and hence is in the default location in the root directory of Polyphony"
    )
    DATABASE_URI = "../polyphony.db"
