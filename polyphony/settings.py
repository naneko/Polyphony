"""
Contains all configuration for bot.

All settings should be loaded from enviroment variables.
For development, create a .env file in the package and make sure python-dotenv is installed.
"""

import logging
import os

log = logging.getLogger(__name__)

# Check for python-dotenv
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    logging.debug("python-dotenv not loaded. Hope you set your environment variables.")

# Get config from environment variables (returns none if not found)
DEBUG = os.getenv("DEBUG")
TOKEN = os.getenv("TOKEN")
DATABASE_URI = os.getenv("DATABASE_URI")
MESSAGE_CACHE_SIZE = os.getenv("MESSAGE_CACHE_SIZE", 20)
MODERATOR_ROLES = os.getenv("MODERATOR_ROLES", ["Moderator"])

# Debug Mode Setup
if DEBUG:
    # Set Logger Level
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("discord")
    logger.setLevel(logging.WARN)
    logger = logging.getLogger("websockets")
    logger.setLevel(logging.WARN)
    log.info("Debug Mode Enabled")
else:
    logging.basicConfig(level=logging.INFO)

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
