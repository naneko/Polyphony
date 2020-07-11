"""
User commands to configure Polyphony
"""
import logging
from datetime import timedelta
from typing import Optional

import discord
from discord.ext import commands

from polyphony.helpers.checks import is_polyphony_user
from polyphony.helpers.database import c
from polyphony.helpers.helpers import instances

log = logging.getLogger("polyphony." + __name__)


class User(commands.Cog):

    # TODO: When member instance joins guild, allow a default set of roles to be assigned from settings.py

    # TODO: Slots command: will show how many tokens are available. (maybe also show with register command)

    def __init__(self, bot: discord.ext.commands.bot):
        self.bot = bot

    @commands.command()
    @is_polyphony_user()
    async def sync(self, ctx: commands.context):
        """
        Sync system members with PluralKit

        :param ctx: Discord Context
        """
        status = await ctx.send(
            embed=discord.Embed(
                title="Syncing",
                description="This may take a while...",
                color=discord.Color.purple(),
            )
        )
        for instance in instances:
            if instance._discord_account_id == ctx.author.id:
                await instance.sync()
                embed = discord.Embed(color=discord.Color.purple())
                embed.set_author(
                    name=str(instance.user), icon_url=instance.pk_avatar_url,
                )
                embed.set_footer(text="Synced")
                await ctx.send(embed=embed)
        await status.edit(
            embed=discord.Embed(title="Done", color=discord.Color.green())
        )

    @commands.command()
    @is_polyphony_user()
    async def whoarewe(self, ctx: commands.context):
        """
        List members of system belonging to user who executes command

        :param ctx: Discord Context
        """
        log.debug(f"Listing members for {ctx.author.display_name}...")
        c.execute(
            "SELECT * FROM members WHERE discord_account_id == ?",
            [ctx.author.id],
        )
        member_list = c.fetchall()
        embed = discord.Embed(title=f"Members of System")
        embed.set_author(name=f"{ctx.author}", icon_url=ctx.author.avatar_url)

        if member_list is None:
            embed.add_field(name="No members where found")

        inline = True
        for member in member_list:
            member_user = ctx.guild.get_member_named(
                f"p.{member['member_name']}"
            )
            owner_user = ctx.guild.get_member(member["discord_account_id"])
            embed.add_field(
                name=member["display_name"],
                value=f"""User: {member_user.mention}\nPluralKit Member ID: `{member['pk_member_id']}`\nEnabled: `{"Yes" if member['member_enabled'] else "No"}`""",
                inline=inline,
            )
            inline = not inline

        await ctx.send(embed=embed)

    @commands.command()
    @is_polyphony_user(allow_mods=True)
    async def ping(self, ctx: commands.context):
        """
        ping: Pings the core bot

        :param ctx: Discord Context
        """
        await ctx.send(
            embed=discord.Embed(
                title=f"Pong ({timedelta(seconds=self.bot.latency)})"
            )
        )

    @commands.command()
    @is_polyphony_user()
    async def role(
        self, ctx: commands.context, system_member: discord.Member = None
    ):
        """
        role add/remove [system member]: Enters role edit mode by saving current roles in memory and then syncing any changes with the member instance. Run again with no arguments or wait 5 minutes to retore user roles.

        :param system_member: System member to sync roles with
        :param ctx: Discord Context
        """
        # TODO: Implement
        await ctx.send("Role command unimplemented")
        log.warning("Role command unimplemented")

    @commands.command()
    @is_polyphony_user()
    async def edit(
        self,
        ctx: commands.context,
        message_id: Optional[discord.Message] = None,
        *,
        message: str,
    ):
        """
        edit (message id) [message]: Edits the last message or message with ID
        
        :param ctx: Discord Context
        :param message_id: (optional) ID of message
        :param message: Message Content
        """
        # TODO: Implement
        await ctx.send("Edit command unimplemented")
        log.warning("Edit command unimplemented")

    @commands.command(name="del")
    @is_polyphony_user()
    async def delete(
        self,
        ctx: commands.context,
        message_id: Optional[discord.Message] = None,
    ):
        """
        del (id): Deletes the last message unless a message ID parameter is provided. Can be run multiple times. n max limited by config.

        :param ctx: Discord Context
        :param message_id: ID of message to delete
        """
        # TODO: Implement
        await ctx.send("Delete command unimplemented")
        log.warning("Delete command unimplemented")


def setup(bot):
    log.debug("User module loaded")
    bot.add_cog(User(bot))


def teardown(bot):
    log.warning("User module unloaded")
