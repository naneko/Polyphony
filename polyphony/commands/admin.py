"""
Admin commands to configure polyphony
"""
import logging
from typing import Union, List

import discord
from discord.ext import commands
from disputils import BotConfirmation

from polyphony.bot import create_member_instance
from polyphony.helpers.checks import is_mod, check_token
from polyphony.helpers.database import (
    insert_member,
    get_unused_tokens,
    update_token_as_used,
    get_member,
    insert_user,
    get_user,
    get_token,
    insert_token,
)
from polyphony.helpers.helpers import LogMessage
from polyphony.helpers.pluralkit import pk_get_member, pk_get_system_members

log = logging.getLogger("polyphony." + __name__)

# TODO: Error Handling
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
        mode: str,
        account: discord.Member,
        pk_id: str,
        bot_token: str = None,
    ):
        """
        p! extend [system/member] [main account] [pk system or member id] (bot token): Creates a new Polyphony member instance and show invite link for bot

        Using a system ID will attempt to create a bot for all system members using the token queue. Will fail immediately if the queue is too short.

        Will fail if bot token argument is given for system ID.

        If bot token is not included for individual member, will use token queue.

        Checks to make sure system/member belongs to the main account

        Checks to make sure token is not in the database AND marked as used

        Checks token is valid

        :param mode: System or Member
        :param ctx: Discord Context
        :param account: Main Account to be extended from
        :param pk_id: PluralKit system or member id
        :param bot_token: Bot token to use to create the instance (optional)
        """

        log.debug("Extending new member...")

        logger = LogMessage(ctx, title="Extending...")
        await logger.init()

        async with ctx.channel.typing():
            if bot_token:
                await ctx.message.delete()
                await logger.log(
                    "Command deleted to hide token. Check your server logs too."
                )

            if mode not in ["system", "member"]:
                logger.title = "Error Extending: Syntax Error"
                logger.color = discord.Color.red()
                await logger.log('First argument must either be "system" or "member"')
                return

            if mode == "system":
                await logger.log("Fetching system from PluralKit...")
                system = await pk_get_system_members(pk_id)
                if system is not None:
                    system = list(system)
                    system_names = [
                        f"{member['name']} (`{member['id']}`)" for member in system
                    ]
                    await logger.log(
                        f"Fetched system {pk_id} -> {', '.join(system_names)}"
                    )
                    if bot_token:
                        await logger.log(
                            "**WARNING** Bot token provided for system creation. Token will be ignored..."
                        )
                    tokens = get_unused_tokens()
                    if len(system) > len(tokens):
                        logger.title = "Error Extending: Not enough tokens"
                        logger.color = discord.Color.red()
                        await logger.log(
                            f"The system has {len(system)} members and there are only {len(tokens)} available"
                        )
                        return
                    if get_user(account.id) is None:
                        await logger.log(
                            f"{account.mention} is a new user! Registering them with Polyphony"
                        )
                        insert_user(account.id)
                    for member, token in zip(system, tokens):
                        # TODO: Skip if member exists
                        insert_member(
                            token["token"],
                            member["id"],
                            account.id,
                            member["name"],
                            member["display_name"],
                            member["avatar_url"],
                            member["proxy_tags"],
                            member["keep_proxy"],
                            member_enabled=True,
                        )
                        update_token_as_used(token["token"])
                        await logger.log("Creating member instance...")
                        create_member_instance(get_member(member["id"]))
                else:
                    logger.title = "Error Extending: System ID invalid"
                    logger.color = discord.Color.red()
                    await logger.log(f"System ID `{pk_id}` was not found")
                    return

            if mode == "member":
                await logger.log("Fetching member from PluralKit...")
                member = await pk_get_member(pk_id)
                if member is not None:
                    system_names = [f"{member['name']} (`{member['id']}`)"]
                    await logger.log(
                        f"Fetched member -> {member['name']} (`{member['id']}`)"
                    )
                    if bot_token:
                        # Check token
                        await logger.log("Checking token...")
                        if not await check_token(bot_token):
                            logger.title = "Error Extending: Bot Token Invalid"
                            logger.color = discord.Color.red()
                            await logger.log("Bot token is invalid")
                            return
                        else:
                            await logger.log("Bot token valid")
                            if get_token(bot_token) is None:
                                log.info("Adding new token to database")
                                insert_token(bot_token, True)
                            elif get_token(bot_token)["used"]:
                                logger.title = (
                                    "Error Extending: Bot Token Already In Use"
                                )
                                logger.color = discord.Color.red()
                                await logger.log("Token already in-use")
                                return
                            else:
                                update_token_as_used(bot_token)
                    # TODO: If no token is provided
                    if get_user(account.id) is None:
                        await logger.log(
                            f"{account.mention} is a new user! Registering them with Polyphony"
                        )
                        insert_user(account.id)
                    if get_member(pk_id) is None:
                        insert_member(
                            bot_token,
                            member["id"],
                            account.id,
                            member["name"],
                            member["display_name"],
                            member["avatar_url"],
                            member["proxy_tags"],
                            member["keep_proxy"],
                            member_enabled=True,
                        )
                    else:
                        logger.title = "Member Already Registered with Polyphony"
                        logger.color = discord.Color.light_grey()
                        await logger.log(
                            f"Member ID `{pk_id}` was already registered with Polyphony"
                        )
                        return
                    await logger.log("Creating member instance...")
                    create_member_instance(get_member(member["id"]))
                else:
                    logger.title = "Error Extending: Member ID invalid"
                    logger.color = discord.Color.red()
                    await logger.log(f"Member ID `{pk_id}` was not found")
                    return

            confirmation = BotConfirmation(ctx, discord.Color.blue())
            await confirmation.confirm(
                f"Create {mode} for {account} with member(s) {', '.join(system_names)}?"
            )
            if confirmation.confirmed:
                await confirmation.message.delete()
                await logger.log("Adding to database...")
            else:
                await confirmation.message.delete()
                logger.title = "Extend Cancelled"
                logger.color = discord.Color.red()
                await logger.log("Extend cancelled by user")
                return

        logger.title = "Extend Success"
        logger.color = discord.Color.green()
        await logger.send(
            "[Created member info + invite]\n*Waiting for instance to be invited to server...*"
        )
        log.info("New member instance extended and activated")

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
