"""
Polyphony: A more robust version of PluralKit.

Created for The Valley discord server
"""

import logging
import discord

from .settings import TOKEN


class Polyphony(discord.Client):
    """Polyphony Core."""

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        logging.info(f"Polyphony started as {self.user}")


client = Polyphony()

client.run(TOKEN)
