"""
Instances are individual bots accounts that act as system members.
"""
import logging
import sqlite3

import discord

log = logging.getLogger(__name__)


class PolyphonyInstance(discord.Client):
    """Polyphony Member Instance."""

    def __init__(self, store: sqlite3.Row, **options):
        """
        :param store: (dict) Instance information from Database
        :param options: Discord Client Options
        """
        super().__init__(**options)
        self.store: sqlite3.Row = store

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        log.info(f"Instance started as {self.user}")
