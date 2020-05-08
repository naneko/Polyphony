"""
Contains all configuration for bot.

All settings should be loaded from enviroment variables.
For development, create a .env file in the package and make sure python-dotenv is installed.
"""

import logging
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logging.debug("python-dotenv not loaded. Hope you set your enviroment variables.")

# TODO: Logging configuration

DEBUG = os.getenv("DEBUG")
TOKEN = os.getenv("TOKEN")
DATABASE_URI = os.getenv("DATABASE_URI")
MESSAGE_CACHE_SIZE = os.getenv("MESSAGE_CACHE_SIZE")
