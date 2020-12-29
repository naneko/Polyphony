"""
Admin commands to configure polyphony
"""
import asyncio
import logging
import pprint
import random

import discord
from discord.ext import commands

from polyphony.helpers.checks import is_mod
from polyphony.helpers.database import conn
from polyphony.helpers.log_message import LogMessage
from polyphony.helpers.pluralkit import (
    pk_get_system,
    pk_get_system_members,
    pk_get_member,
)
from polyphony.instance.bot import PolyphonyInstance

log = logging.getLogger("polyphony." + __name__)


class Debug(commands.Cog):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @commands.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def getsystem(self, ctx: commands.context, system):
        system_out = pprint.pformat(await pk_get_system(system))
        log.debug(f"\n{system_out}")
        await ctx.send(f"```python\n{system_out}```")

    @commands.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def getsystemmembers(self, ctx: commands.context, system):
        system_out = pprint.pformat(await pk_get_system_members(system))
        log.debug(f"\n{system_out}")
        await ctx.send(f"```python\n{system_out}```")

    @commands.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def getmember(self, ctx: commands.context, member):
        member_out = pprint.pformat(await pk_get_member(member))
        log.debug(f"\n{member_out}")
        await ctx.send(f"```python\n{member_out}```")

    @commands.command()
    @commands.is_owner()
    async def upgrade(self, ctx: commands.context):
        from git import Repo

        with ctx.channel.typing():
            log.warning("Upgrading bot from git repo")
            repo = Repo("..")
            o = repo.remotes.origin
            o.pull()

        log.info(f"Pulled update successfully ({repo.heads[0].commit})")

        await ctx.send(
            f"`POLYPHONY SYSTEM UTILITIES` Polyphony pulled `{repo.heads[0].commit}` from master branch. Run `;;reload` to complete upgrade."
        )

    @commands.command(aliases=["unregister"])
    @commands.is_owner()
    async def deregister(self, ctx: commands.context, ctx_member: discord.Member):
        # TODO: Option to delete all old messages
        member = conn.execute(
            "SELECT * FROM members WHERE id = ?", [ctx_member.id]
        ).fetchone()
        if member:
            logger = LogMessage(ctx, title="Deregistering...")
            await logger.init()
            with ctx.channel.typing():
                instance = PolyphonyInstance(member["pk_member_id"])
                asyncio.run_coroutine_threadsafe(
                    instance.start(member["token"]), self.bot.loop
                )
                await instance.wait_until_ready()

                await logger.log("Updating Random Username...")
                await instance.update_username(f"{random.randint(0000, 9999)}")
                await logger.log("Clearing Nickname...")
                await instance.update_nickname(None)
                await logger.log("Updating Random Avatar...")
                await instance.update_avatar(
                    "https://picsum.photos/256", no_timeout=True
                )

                await logger.log("Updating Roles...")
                roles = []
                for role in ctx_member.roles[1:]:
                    if role.name is not role.managed:
                        roles.append(role)
                await ctx_member.remove_roles(*roles)
                await instance.update_default_roles()

                await logger.log("Freeing Token...")
                conn.execute(
                    "UPDATE tokens SET used = 0 WHERE token = ?",
                    [member["token"]],
                )
                conn.execute(
                    "DELETE FROM members WHERE token = ?",
                    [member["token"]],
                )
                conn.commit()

                await instance.close()

                await logger.message.delete()
                await ctx.channel.send(
                    f"`POLYPHONY SYSTEM UTILITIES` {ctx_member.mention} has been deregistered and the token has been made available"
                )
        else:
            await ctx.channel.send(
                f"`POLYPHONY SYSTEM UTILITIES` Database record for {ctx_member.mention} not found."
            )

    @commands.command()
    @commands.is_owner()
    async def removeuser(self, ctx: commands.context, member: discord.Member):
        conn.execute(
            "DELETE FROM users WHERE id = ?",
            [member.id],
        )
        conn.commit()
        await ctx.channel.send(
            f"`POLYPHONY SYSTEM UTILITIES` {member.mention} has been removed from the collection of Polyphony users."
        )


def setup(bot: commands.bot):
    log.debug("Debug module loaded")
    bot.add_cog(Debug(bot))


def teardown(bot):
    log.debug("Debug module unloaded")
