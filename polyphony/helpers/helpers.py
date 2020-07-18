import asyncio
import logging
import sqlite3
from typing import List

import discord
from discord.ext import commands

from polyphony.instance.bot import PolyphonyInstance

log = logging.getLogger(__name__)

# List of Instance Threads
instances: List[PolyphonyInstance] = []


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


def create_member_instance(member: sqlite3.Row) -> PolyphonyInstance:
    """
    Create member instance threads from dictionary that is returned from database
    :param member: directory that is returned from database functions
    """
    if not member["member_enabled"]:
        pass
    log.debug(
        f"Creating member instance {member['member_name']} ({member['pk_member_id']})"
    )
    new_instance = PolyphonyInstance(
        member["token"],
        member["pk_member_id"],
        member["discord_account_id"],
        member["member_name"],
        member["display_name"],
        member["pk_avatar_url"],
        member["pk_proxy_tags"],
    )
    loop = asyncio.get_event_loop()
    loop.create_task(new_instance.start(member["token"]))
    instances.append(new_instance)
    return new_instance
