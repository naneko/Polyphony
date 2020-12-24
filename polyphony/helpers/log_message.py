import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# TODO: Add comments
# TODO: Reimplement usages using new features


class LogMessage:
    def __init__(self, ctx: commands.Context, title="Loading..."):
        self.message = None
        self.ctx = ctx
        self.title = title
        self.color = discord.Color.orange()
        self.content = []
        self.batches = []

    async def init(self):
        log.debug("Creating LogMessage Instance...")
        await self.send("One sec...")
        log.debug("LogMessage Instance Created.")

    async def send(self, content):
        if len(self.batches) > 0:
            embed = discord.Embed(description=content, color=self.color)
        else:
            embed = discord.Embed(
                title=self.title, description=content, color=self.color
            )
        if self.message is None:
            self.message = await self.ctx.send(embed=embed)
        elif len("\n".join(self.content)) >= 2048:
            self.batches.append([self.message, self.content[:-1]])
            self.content = self.content[-1:]
            embed = discord.Embed(description="\n".join(self.content), color=self.color)
            self.message = await self.ctx.send(embed=embed)
        else:
            await self.message.edit(embed=embed)

    async def log(self, message):
        log.debug(f"LogMessage: {message}")
        self.content.append(message)
        await self.send("\n".join(self.content))

    async def update(self):
        await self.send("\n".join(self.content))

    async def edit(self, index, content):
        self.content[index] = content
        await self.update()

    async def set(self, title=None, color=None):
        if title:
            self.title = title
        if color:
            self.color = color
        await self.update()

        if self.batches:
            embed = discord.Embed(
                title=self.title,
                description="\n".join(self.batches[0][1]),
                color=self.color,
            )
            await self.batches[0][0].edit(embed=embed)

            for message, content in self.batches[1:]:
                embed = discord.Embed(description="\n".join(content), color=self.color)
                await message.edit(embed=embed)
