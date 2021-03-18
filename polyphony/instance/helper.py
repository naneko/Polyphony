import asyncio
import logging

import discord
import discord.ext

from polyphony.settings import (
    TOKEN,
)

log = logging.getLogger(__name__)


class HelperInstance(discord.Client):
    def __init__(
        self,
        **options,
    ):
        super().__init__(**options)
        self.lock = asyncio.Lock()
        self.invisible = False
        log.debug(f"Helper initialized")

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        log.info(f"Started as {self.user}")

    async def edit_as(self, message: discord.Message, content, token, files=None):
        await self.wait_until_ready()
        msg = await self.get_channel(message.channel.id).fetch_message(message.id)
        async with self.lock:
            self.http.token = token
            await msg.edit(content=content, files=files)
            self.http.token = TOKEN
        if not self.invisible:
            await self.change_presence(status=discord.Status.invisible)

    async def send_as(
        self, message: discord.Message, content, token, files=None, reference=None
    ):
        await self.wait_until_ready()
        chan = self.get_channel(message.channel.id)
        async with self.lock:
            self.http.token = token
            await chan.trigger_typing() if len(message.attachments) > 0 else None
            await chan.send(content=content, files=files, reference=reference)
            self.http.token = TOKEN
        if not self.invisible:
            await self.change_presence(status=discord.Status.invisible)
