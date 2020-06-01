"""
Admin commands to configure polyphony
"""
import logging
import pprint

from discord.ext import commands

from helpers.pluralkit import pk_get_system, pk_get_system_members, pk_get_member

log = logging.getLogger("polyphony." + __name__)


class Debug(commands.Cog):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @commands.command()
    async def getsystem(self, ctx: commands.context, system):
        system_out = pprint.pformat(await pk_get_system(system))
        log.debug(f"\n{system_out}")
        await ctx.send(f"```python\n{system_out}```")

    @commands.command()
    async def getsystemmembers(self, ctx: commands.context, system):
        system_out = pprint.pformat(await pk_get_system_members(system))
        log.debug(f"\n{system_out}")
        await ctx.send(f"```python\n{system_out}```")

    @commands.command()
    async def getmember(self, ctx: commands.context, member):
        member_out = pprint.pformat(await pk_get_member(member))
        log.debug(f"\n{member_out}")
        await ctx.send(f"```python\n{member_out}```")


def setup(bot: commands.bot):
    log.debug("Debug module loaded")
    bot.add_cog(Debug(bot))


def teardown(bot):
    log.warning("Debug module unloaded")
