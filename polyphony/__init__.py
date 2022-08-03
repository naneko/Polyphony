"""
Polyphony: A more robust version of PluralKit.

Created for The Valley discord server
"""
import logging
import os
from pathlib import Path

import tomli
from git import Repo

DEBUG: bool = bool(os.getenv("DEBUG", False))

log = logging.getLogger(__name__)

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
    logger.setLevel(logging.ERROR)
    logger = logging.getLogger("websockets")
    logger.setLevel(logging.ERROR)

with open(f'{Path(os.path.dirname(os.path.abspath(__file__))).parent.absolute()}/pyproject.toml', 'rb') as f:
    repo = Repo(Path(os.path.dirname(os.path.abspath(__file__))).parent.absolute())
    pyproject = tomli.load(f)
    log.info(f"Polyphony Version {pyproject['tool']['poetry']['version']} ({str(repo.head.commit)[0:6]})")

try:
    import polyphony.bot
    import polyphony.commands
    import polyphony.settings
except ImportError:
    log.error(f"Polyphony sub-modules Not Found. Are you in the right working directory?")
