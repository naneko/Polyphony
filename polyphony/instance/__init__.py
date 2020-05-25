"""
Instances are individual bots that are created with the purpose.
"""

import discord
import logging

log = logging.getLogger(__name__)


class PolyphonyInstance(discord.Client):
    """Polyphony Member Instance."""

    def __init__(self, store, **options):
        """
        :param store: (dict) Instance information from Database
        :param options: Discord Client Options
        """
        super().__init__(**options)
        self.store = store

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        log.info(f"Instance started as {self.user}")
