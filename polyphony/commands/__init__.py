"""
Discord Commands
"""
import logging

import discord
from discord.ext import commands

from polyphony.commands.admin.disable import Disable
from polyphony.commands.admin.enable import Enable
from polyphony.commands.admin.invite import Invite
from polyphony.commands.admin.list import List
from polyphony.commands.admin.register import Register
from polyphony.commands.admin.reset import Reset
from polyphony.commands.admin.suspend import Suspend
from polyphony.settings import GUILD_ID

log = logging.getLogger(__name__)

cogs = [Disable, Enable, Invite, List, Register, Reset, Suspend]


async def setup(bot: commands.bot):
    log.debug("Loading commands...")
    for cog in cogs:
        log.debug(f"Adding cog {cog.__name__}")
        await bot.add_cog(cog(bot), guild=discord.Object(id=GUILD_ID))
    log.debug("Commands loaded")


async def teardown(bot: commands.bot):
    log.debug("Unloading commands...")
    for cog in cogs:
        log.debug(f"Removing cog {cog.__name__}")
        await bot.remove_cog(cog.__name__)
    log.warning("Commands unloaded")
