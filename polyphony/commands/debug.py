"""
Admin commands to configure polyphony
"""
import logging
import pprint
import random

import discord
from discord.ext import commands

from polyphony.helpers.database import conn
from polyphony.helpers.instances import instances
from polyphony.helpers.pluralkit import (
    pk_get_system,
    pk_get_system_members,
    pk_get_member,
)

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
            f"`POLYPHONY SYSTEM UTILITIES` Polyphony pulled `{repo.heads[0].commit}` from master branch. Run `;;reload` or `;;reload all` to complete upgrade."
        )

    @commands.command(aliases=["unregister"])
    @commands.is_owner()
    async def deregister(self, ctx: commands.context, member: discord.Member):
        with ctx.channel.typing():
            for i, instance in enumerate(instances):
                if instance.user.id == member.id:
                    instance.member_name = f"{random.randint(0000, 9999)}"
                    instance.nickname = ""
                    instance.display_name = ""
                    instance.pk_avatar_url = "https://picsum.photos/256"
                    await instance.update()
                    roles = []
                    for role in member.roles[1:]:
                        if role.name is not role.managed:
                            roles.append(role)
                    await instance.update_default_roles()
                    await member.remove_roles(*roles)
                    conn.execute(
                        "UPDATE tokens SET used = 0 WHERE token = ?",
                        [instance.get_token()],
                    )
                    conn.execute(
                        "DELETE FROM members WHERE token = ?", [instance.get_token()],
                    )
                    conn.commit()
                    await instance.close()
                    instances.pop(i)
                    await ctx.channel.send(
                        f"`POLYPHONY SYSTEM UTILITIES` {member.mention} has been deregistered and the token has been made available"
                    )
                    return
        await ctx.channel.send(
            f"`POLYPHONY SYSTEM UTILITIES` {member.mention} not found in active instances. Please start the instance before deregistering."
        )

    @commands.command()
    @commands.is_owner()
    async def removeuser(self, ctx: commands.context, member: discord.Member):
        conn.execute(
            "DELETE FROM users WHERE discord_account_id = ?", [member.id],
        )
        await ctx.channel.send(
            f"`POLYPHONY SYSTEM UTILITIES` {member.mention} has been removed from the collection of Polyphony users."
        )


def setup(bot: commands.bot):
    log.debug("Debug module loaded")
    bot.add_cog(Debug(bot))


def teardown(bot):
    log.warning("Debug module unloaded")
