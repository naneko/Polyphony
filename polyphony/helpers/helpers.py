import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class LogMessage:
    def __init__(self, ctx: commands.Context, title="Loading..."):
        self.message = None
        self.ctx = ctx
        self.title = title
        self.color = discord.Color.orange()
        self.content = []

    async def init(self):
        log.debug("Creating LogMessage Instance...")
        await self.send("One sec...")
        log.debug("LogMessage Instance Created.")

    async def send(self, message):
        embed = discord.Embed(title=self.title, description=message, color=self.color)
        if self.message is None:
            self.message = await self.ctx.send(embed=embed)
        else:
            await self.message.edit(embed=embed)

    async def log(self, message):
        log.debug(f"LogMessage: {message}")
        self.content.append(message)
        await self.send("\n".join(self.content))

    async def update(self):
        await self.send("\n".join(self.content))
