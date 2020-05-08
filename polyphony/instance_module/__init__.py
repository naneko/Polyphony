"""
Instances are individual bots that are created with the purpose.
"""

import discord
import logging


class PolyphonyInstance(discord.Client):
    """Polyphony Member Instance."""

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        logging.info(f'Instance started as {self.user}')
        # TODO: Add more robust startup logging for instance
