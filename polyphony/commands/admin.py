"""
Admin commands to configure polyphony
"""
import logging
from typing import Union, List

import discord
from discord.ext import commands

from helpers.checks import is_mod

log = logging.getLogger("polyphony." + __name__)


class Admin(commands.Cog):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    @commands.command()
    @is_mod()
    async def list(
        self,
        ctx: commands.context,
        arg1: Union[discord.Member, str] = None,
        arg2: discord.Member = None,
    ):
        """
        p! list: Shows all active Polyphony members sorted by main account
        p! list inactive: Shows systems and main accounts that haven’t been used in n number of days defined in the config or at all or where the main user has left the server
        p! list [main account]: Lists all polyphony system members for a given main account
        p! list all [main account]: Lists all PluralKit system members for a given main account

        TODO: Add configuration option for auto-disable inactive users

        :param ctx: Discord Context
        :param arg1: None/"inactive"/Discord Account
        :param arg2: None/Discord Account
        """
        # TODO: Implement
        await ctx.send("Sync command unimplemented")
        log.warning("Sync command unimplemented")

    @commands.command()
    @is_mod()
    async def extend(
        self,
        ctx: commands.context,
        account: discord.Member,
        pk_id: str,
        bot_token: str = None,
    ):
        """
        p! extend [main account] [pk system or member id] (bot token): Creates a new Polyphony member instance and show invite link for bot

        Using a system ID will attempt to create a bot for all system members using the token queue. Will fail immediately if the queue is too short.

        Will fail if bot token argument is given for system ID.

        If bot token is not included for individual member, will use token queue.

        Checks to make sure system/member belongs to the main account

        Checks to make sure token is not in the database AND marked as used

        Checks token is valid

        :param ctx: Discord Context
        :param account: Main Account to be extended from
        :param pk_id: PluralKit system or member id
        :param bot_token: Bot token to use to create the instance (optional)
        """
        # TODO: Implement
        await ctx.send("Sync command unimplemented")
        log.warning("Sync command unimplemented")

    @commands.command()
    @is_mod()
    async def suspend(self, ctx: commands.context, system_member: discord.Member):
        """
        p! suspend [system member]: Sets member_enabled to false. Pulls the member instance offline.

        :param ctx: Discord Context
        :param system_member: System Member
        """
        # TODO: Implement
        await ctx.send("Sync command unimplemented")
        log.warning("Sync command unimplemented")

    @commands.command()
    @is_mod()
    async def disable(self, ctx: commands.context, system_member: discord.Member):
        """
        p! disable [system member]: Disables a system member by deleting it from the database and kicking it from the server. Bot token cannot be reused.

        :param ctx: Discord Context
        :param system_member: System Member
        """
        # TODO: Implement
        await ctx.send("Sync command unimplemented")
        log.warning("Sync command unimplemented")

    @commands.command()
    @is_mod()
    async def queue(self, ctx: commands.context, *tokens: List[str]):
        """
        p! queue [bot token] (bot token)...: Queues bot tokens for usage

        Checks tokens are valid

        :param ctx: Discord Context
        :param tokens: Discord Bot Tokens
        :return:
        """
        # TODO: Implement
        await ctx.send("Sync command unimplemented")
        log.warning("Sync command unimplemented")

    @commands.command()
    @is_mod()
    async def manageroles(self, ctx: commands.context, action: str, *roles: List[str]):
        """
        p! manageroles add/remove [role id(:index)] (role id(:index))...: Allows/disallows a role to be assigned to a Polyphony system member.

        p! remove all: Remove all options from list

        Index will determine the order the roles are inserted into the list (defaults to end of list).

        p! remove does not unassign roles

        :param ctx: Discord Context
        :param action: add/remove
        :param roles: role id(:index) (index is optional)
        """
        # TODO: Implement
        await ctx.send("Sync command unimplemented")
        log.warning("Sync command unimplemented")


def setup(bot: commands.bot):
    log.debug("Admin module loaded")
    bot.add_cog(Admin(bot))


def teardown(bot):
    log.warning("Admin module unloaded")
