"""
User commands to configure Polyphony
"""
import logging

import discord
from discord.ext import commands

log = logging.getLogger("polyphony." + __name__)


class User(commands.Cog):
    def __init__(self, bot: discord.ext.commands.bot):
        self.bot = bot

    @commands.command()
    async def sync(self, ctx: commands.context):
        pass

    @commands.command()
    async def nick(self, ctx: commands.context):
        pass

    @commands.command()
    async def ping(self, ctx: commands.context):
        await ctx.send(embed=discord.Embed(title=f"Pong ({self.bot.latency} ms)"))

    @commands.command()
    async def listroles(self, ctx: commands.context):
        pass

    @commands.command()
    async def role(self, ctx: commands.context):
        pass

    @commands.command()
    async def edit(self, ctx: commands.context):
        pass

    @commands.command(name="del")
    async def delete(self, ctx: commands.context):
        pass


def setup(bot):
    log.debug("User module loaded")
    bot.add_cog(User(bot))


def teardown(bot):
    log.warning("User module unloaded")
