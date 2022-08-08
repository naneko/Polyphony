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
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.client").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("git.cmd").setLevel(logging.WARNING)
    log.info("Debug Mode Enabled")
else:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("discord").setLevel(logging.ERROR)
    logging.getLogger("websockets").setLevel(logging.ERROR)

with open(
    f"{Path(os.path.dirname(os.path.abspath(__file__))).parent.absolute()}/pyproject.toml",
    "rb",
) as f:
    repo = Repo(Path(os.path.dirname(os.path.abspath(__file__))).parent.absolute())
    pyproject = tomli.load(f)
    log.info(
        f"Polyphony Version {pyproject['tool']['poetry']['version']} ({str(repo.head.commit)[0:6]})"
    )

try:
    import polyphony.bot
    import polyphony.commands
    import polyphony.settings
except ImportError as e:
    log.error(
        f"Polyphony sub-modules Not Found. Are you in the right working directory?\nSubmodule Error: {e}"
    )
