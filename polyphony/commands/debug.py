"""
Admin commands to configure polyphony
"""
import asyncio
import logging
import pprint
import random
from typing import Union

import discord
from discord.ext import commands

from polyphony.helpers.database import conn
from polyphony.helpers.instances import instances, update_presence
from polyphony.helpers.pluralkit import (
    pk_get_system,
    pk_get_system_members,
    pk_get_member,
)
from polyphony.settings import GUILD_ID

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
            for instance in instances:
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
                    await instance.change_presence(
                        status=discord.Status.offline, activity=None
                    )
                    await instance.close()
                    instances.remove(instance)
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
        conn.commit()
        await ctx.channel.send(
            f"`POLYPHONY SYSTEM UTILITIES` {member.mention} has been removed from the collection of Polyphony users."
        )

    @commands.command()
    @commands.is_owner()
    async def restart(
        self, ctx: commands.context, system_member: Union[discord.Member, str]
    ):
        if system_member == "stagnant":
            log.info("Restarting stagnant instances")
            instance_queue = []
            with ctx.channel.typing():
                for i, instance in enumerate(instances):
                    if instance.user is None:
                        instance_queue.append(self.restart_helper(instance))
            await asyncio.gather(*instance_queue)
            await ctx.send(
                "`POLYPHONY SYSTEM UTILITIES` Finished attempting to restart stagnant instances"
            )
            log.info("Finished attempting to restart stagnant instances")
            return
        if system_member == "all":
            log.info("Restarting all instances")
            instance_queue = []
            with ctx.channel.typing():
                for i, instance in enumerate(instances):
                    instance_queue.append(self.restart_helper(instance))
            await asyncio.gather(*instance_queue)
            await ctx.send(
                "`POLYPHONY SYSTEM UTILITIES` Finished attempting to restart all instances"
            )
            log.info("Finished attempting to restart all instances")
            return
        if system_member == "presence":
            with ctx.channel.typing():
                instance_queue = []
                for i, instance in enumerate(instances):
                    instance_queue.append(
                        update_presence(
                            instance,
                            name=self.bot.get_user(instance.user.id),
                            status=self.bot.get_guild(GUILD_ID)
                            .get_member(instance.user.id)
                            .status,
                        )
                    )
            await asyncio.gather(*instance_queue)
            await ctx.send("Done")
            return
        for i, instance in enumerate(instances):
            if instance.user.id == system_member.id:
                with ctx.channel.typing():
                    log.info(f"{system_member} restarting...")
                    instance.clear()
                    log.debug(f"{system_member} stopped. Starting...")
                    asyncio.run_coroutine_threadsafe(
                        instance.start(instance.get_token()), self.bot.loop
                    )
                    log.debug(f"{system_member} waiting to be ready...")
                    await instance.wait_until_ready()
                    log.debug(f"{system_member} updating presence...")
                    await update_presence(
                        instance, name=self.bot.get_user(instance.user.id)
                    )
                    await ctx.send(
                        f"`POLYPHONY SYSTEM UTILITIES` {system_member.mention} restarted"
                    )

                    log.info(f"{system_member} restarted")
                    break

    async def restart_helper(self, instance):
        instance.clear()
        asyncio.run_coroutine_threadsafe(
            instance.start(instance.get_token()), self.bot.loop
        )
        await instance.wait_until_ready()
        await update_presence(
            instance, name=self.bot.get_user(instance.main_user_account_id)
        )

    @commands.command()
    @commands.is_owner()
    async def statecheck(self, ctx: commands.context):
        state_check = []
        for instance in instances:
            state_check.append(instance.check_for_invalid_states())
            await asyncio.gather(*state_check)
        await ctx.channel.send("`POLYPHONY SYSTEM UTILITIES` State check complete")


def setup(bot: commands.bot):
    log.debug("Debug module loaded")
    bot.add_cog(Debug(bot))


def teardown(bot):
    log.debug("Debug module unloaded")
