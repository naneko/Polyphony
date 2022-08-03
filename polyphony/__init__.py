"""
Polyphony: A more robust version of PluralKit.

Created for The Valley discord server
"""
import logging
import os
from pathlib import Path

import tomli
from git import Repo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord")
logger.setLevel(logging.ERROR)
logger = logging.getLogger("websockets")
logger.setLevel(logging.ERROR)

log = logging.getLogger(__name__)

with open(f'{Path(os.path.dirname(os.path.abspath(__file__))).parent.absolute()}/pyproject.toml', 'rb') as f:
    repo = Repo("..")
    pyproject = tomli.load(f)
    log.info(f"Polyphony Version {pyproject['tool']['poetry']['version']} ({str(repo.head.commit)[0:6]})")

try:
    import polyphony.bot
    import polyphony.commands
    import polyphony.settings
except ImportError:
    log.error(f"Polyphony sub-modules Not Found. Are you in the right working directory?")
