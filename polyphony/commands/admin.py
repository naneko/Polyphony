"""
Admin commands to configure polyphony
"""
import asyncio
import logging
from typing import Union

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
    c,
    get_member_by_discord_id,
    conn,
)
from polyphony.helpers.helpers import LogMessage, instances
from polyphony.helpers.pluralkit import pk_get_member
from polyphony.settings import DEFAULT_INSTANCE_PERMS, MODERATOR_ROLES

log = logging.getLogger("polyphony." + __name__)

# TODO: Allow logging channel
# TODO: Error Handling
# TODO: "Get" command to get information about a PluralKit member via system id or member id
class Admin(commands.Cog):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.token_session = []

    @commands.command()
    @is_mod()
    async def list(
        self, ctx: commands.context, argument: Union[discord.Member, str] = None
    ):
        """
        list                    Shows all active Polyphony members sorted by main account
        list inactive           Shows systems and main accounts that haven’t been used in n number of days defined in the config or at all or where the main user has left the server
        list [main account]     Lists all polyphony system members for a given main account
        list all                Lists all Polyphony members registered

        :param ctx: Discord Context
        :param arg1: None/"inactive"/Discord Account
        """
        if argument is None:
            log.debug("Listing active members...")
            c.execute("SELECT * FROM members WHERE member_enabled == 1")
            member_list = c.fetchall()
            embed = discord.Embed(title="Active Members")
        elif isinstance(argument, discord.Member):
            log.debug(f"Listing members for {argument.display_name}...")
            c.execute(
                "SELECT * FROM members WHERE discord_account_id == ?", [argument.id],
            )
            member_list = c.fetchall()
            embed = discord.Embed(title=f"Members of System")
            embed.set_author(
                name=f"{argument} ({argument.id})", icon_url=argument.avatar_url
            )
        elif argument.lower() == "inactive":
            log.debug("Listing inactive members...")
            c.execute("SELECT * FROM members WHERE member_enabled == 0")
            member_list = c.fetchall()
            embed = discord.Embed(title="Inactive Members")
        elif argument.lower() == "all":
            log.debug("Listing all members...")
            c.execute("SELECT * FROM members")
            member_list = c.fetchall()
            embed = discord.Embed(title="All Members")
        else:
            log.debug("List members command was improperly formatted")
            ctx.send("[TODO] Add Error Message lol")  # TODO: Add error message
            return

        if member_list is None:
            embed.add_field(name="No members where found")

        for member in member_list:
            if len(embed.fields) >= 9:
                await ctx.send(embed=embed)
                embed = discord.Embed()
            member_user = ctx.guild.get_member_named(f"p.{member['member_name']}")
            owner_user = ctx.guild.get_member(member["discord_account_id"])
            embed.add_field(
                name=dict(member).get("display_name", member["member_name"]),
                value=f"""**User:** {member_user.mention} (`{member_user.id}`)\n**Account Owner:** {owner_user.mention if hasattr(owner_user, 'mention') else "*Unable to get User*"} (`{member["discord_account_id"]}`)\n**PluralKit Member ID:** `{member['pk_member_id']}`\n**Enabled:** `{bool(member['member_enabled'])}`""",
                inline=True,
            )

        await ctx.send(embed=embed)

    @commands.command()
    @is_mod()
    async def register(
        self, ctx: commands.context, pluralkit_member_id: str, account: discord.Member,
    ):
        """
        Creates a new Polyphony member instance

        :param ctx: Discord Context
        :param account: Main Account to be extended from
        :param pk_id: PluralKit system or member id
        """

        log.debug("Registering new member...")

        logger = LogMessage(ctx, title="Registering...")
        await logger.init()

        async with ctx.channel.typing():
            await logger.log("Fetching member from PluralKit...")
            member = await pk_get_member(pluralkit_member_id)
            if member is not None:
                system_names = [f"{member['name']} (`{member['id']}`)"]
                await logger.log(
                    f"Fetched member -> {member['name']} (`{member['id']}`)"
                )
                tokens = get_unused_tokens()
                if len(tokens) == 0:
                    logger.title = "Error Registering: No Slots Available"
                    logger.color = discord.Color.red()
                    await logger.log(
                        f"No tokens in queue. Run `{self.bot.command_prefix}tokens` for information on how to add more."
                    )
                    return
                bot_token = tokens[0]
                update_token_as_used(bot_token["token"])
                if get_user(account.id) is None:
                    await logger.log(
                        f"{account.mention} is a new user! Registering them with Polyphony"
                    )
                    insert_user(account.id)
                if get_member(pluralkit_member_id) is None:
                    insert_member(
                        bot_token["token"],
                        member["id"],
                        account.id,
                        0,
                        member["name"],
                        member["display_name"],
                        member["avatar_url"],
                        member["proxy_tags"][0],
                        member["keep_proxy"],
                        member_enabled=True,
                    )
                else:
                    logger.title = "Member Already Registered with Polyphony"
                    logger.color = discord.Color.light_grey()
                    await logger.log(
                        f"Member ID `{pluralkit_member_id}` was already registered with Polyphony"
                    )
                    return
                await logger.log("Creating member instance...")
                create_member_instance(get_member(member["id"]))
            else:
                logger.title = "Error Registering: Member ID invalid"
                logger.color = discord.Color.red()
                await logger.log(f"Member ID `{pluralkit_member_id}` was not found")
                return

        confirmation = BotConfirmation(ctx, discord.Color.blue())
        await confirmation.confirm(
            f"Create member for {account} with member {', '.join(system_names)}?"
        )
        if confirmation.confirmed:
            await confirmation.message.delete()
            await logger.log("Adding to database...")
        else:
            await confirmation.message.delete()
            logger.title = "Extend Cancelled"
            logger.color = discord.Color.red()
            await logger.log("Registration cancelled by user")
            return

        logger.title = "Registration Successful"
        logger.color = discord.Color.green()
        c.execute("SELECT * FROM tokens WHERE used = 0")
        slots = c.fetchall()
        await logger.log(f"There are now {len(slots)} slots available")
        await logger.log("\n*Generate an invite link using `invite [Client ID]`*")
        log.info("New member instance extended and activated")
        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(
            name=f"{dict(member).get('display_name', member['member_name'])} (p.{member['member_name']})",
            icon_url=member["avatar_url"],
        )
        await ctx.send(embed=embed)

    @commands.command()
    @is_mod()
    async def syncall(self, ctx: commands.context):
        log.info("Syncing all...")
        logger = LogMessage(ctx, title=":hourglass: Syncing All Members...")
        logger.color = discord.Color.orange()

        for instance in instances:
            if len(logger.content) > 30:
                logger.title = ":white_check_mark: Batch Complete"
                logger.color = discord.Color.green()
                await logger.update()
                logger = LogMessage(
                    ctx, title=":hourglass: Syncing Next Batch of Members..."
                )
                logger.color = discord.Color.orange()
            await logger.log(f":hourglass: Syncing {instance.user.mention}...")
            if await instance.sync() is True:
                logger.content[
                    -1
                ] = f":white_check_mark: Synced {instance.user.mention}"
            else:
                logger.content[-1] = f":x: Failed to sync {instance.user.mention}"
        logger.title = ":white_check_mark: Sync Complete"
        logger.color = discord.Color.green()
        await logger.update()
        log.info("Sync all complete")

    @commands.command()
    @is_mod()
    async def invite(self, ctx: commands.context, client_id: str):
        """
        Generates an invite link with pre-set permissions from a client ID.

        :param ctx: Discord Context
        :param client_id: Bot Client ID
        """
        log.debug("Generating invite link")
        embed = discord.Embed(
            title=f"Invite Link for {ctx.guild.name}",
            url=discord.utils.oauth_url(
                client_id,
                permissions=discord.Permissions(DEFAULT_INSTANCE_PERMS),
                guild=ctx.guild,
            ),
        )
        embed.set_footer(text=f"Client ID: {client_id}")
        await ctx.send(embed=embed)

    @commands.command()
    @is_mod()
    async def suspend(self, ctx: commands.context, system_member: discord.Member):
        """
        Pulls the member instance offline.

        :param ctx: Discord Context
        :param system_member: System Member
        """
        # TODO: Provide more verbose feedback from command
        for i, instance in enumerate(instances):
            if instance.user.id == system_member.id:
                await instance.close()
                with conn:
                    c.execute(
                        "UPDATE members SET member_enabled = 0 WHERE token = ?",
                        [instance.get_token()],
                    )
                del instances[i]
                await ctx.send(f"{system_member.mention} suspended")
                log.info(f"{system_member} has been suspended by {ctx.message.author}")

    @commands.command()
    @is_mod()
    async def start(self, ctx: commands.context, system_member: discord.Member):
        """
        Starts a suspended instance

        :param ctx: Discord Context
        :param system_member: System Member
        """
        # TODO: Provide more verbose feedback from command
        member = get_member_by_discord_id(system_member.id)
        if member:
            c.execute(
                "UPDATE members SET member_enabled = 1 WHERE member_account_id = ?",
                [system_member.id],
            )
            instances.append(create_member_instance(member))
            await ctx.send(f"{system_member.mention} started")
            log.info(f"{system_member} has been started by {ctx.message.author}")

    @commands.command()
    @is_mod()
    async def disable(self, ctx: commands.context, system_member: discord.Member):
        """
        Disables a system member permanently by deleting it from the database and kicking it from the server. Bot token cannot be reused.

        :param ctx: Discord Context
        :param system_member: System Member
        """
        # TODO: Provide more verbose feedback from command
        instance = get_member_by_discord_id(system_member.id)
        if instance:
            log.debug(f"Disabling {system_member}")
            confirmation = BotConfirmation(ctx, discord.Color.red())
            await confirmation.confirm(f"Disable member {system_member} permanently?")
            if confirmation.confirmed:
                await confirmation.message.delete()
                with conn:
                    c.execute(
                        "DELETE FROM members WHERE token = ?", [instance["token"]],
                    )
                await self.suspend(ctx, system_member)
                await ctx.send(f"{system_member.mention} disabled permanently")
                log.info(
                    f"{system_member} has been disabled permanently by {ctx.message.author}"
                )
                log.debug(f"Disabled {system_member}")
            else:
                await confirmation.message.delete()
                await ctx.send(f"{system_member.mention} was __not__ disabled")
                log.debug(f"Canceled disable of {system_member}")

    @commands.command()
    async def tokens(self, ctx: commands.context, *tokens: str):
        """
        Add tokens to queue

        :param ctx: Discord Context
        :param tokens: List of tokens
        """

        async def session(self, author: discord.Member):
            self.token_session.append(author)
            await asyncio.sleep(300)
            self.token_session.remove(author)

        if (
            ctx.channel.type is discord.ChannelType.private
            and ctx.message.author in self.token_session
        ):
            await ctx.send("Adding tokens...")
            log.debug(tokens)
            for index, token in enumerate(tokens):
                logger = LogMessage(ctx, title=f"Adding token {index}...")
                await logger.init()
                # Check token
                await logger.log(f"Checking token {index}...")
                if not await check_token(token):
                    logger.title = f"Token {index} Invalid"
                    logger.color = discord.Color.red()
                    await logger.log("Bot token is invalid")
                else:
                    await logger.log("Token valid")
                    if get_token(token) is None:
                        log.info("Adding new token to database")
                        insert_token(token, False)
                        logger.title = f"Bot token {index} added"
                        logger.color = discord.Color.green()
                        c.execute("SELECT * FROM tokens WHERE used = 0")
                        slots = c.fetchall()
                        await logger.send(
                            f"There are now {len(slots)} slot(s) available"
                        )
                    else:
                        logger.title = f"Token {index} already in database"
                        logger.color = discord.Color.orange()
                        await logger.log("Bot token already in database")
        elif ctx.channel.type is not discord.ChannelType.private:
            await ctx.message.delete()
            if any(role.name in MODERATOR_ROLES for role in ctx.message.author.roles):
                await ctx.message.author.send(
                    f"Token mode enabled for 5 minutes. Add tokens with `{self.bot.command_prefix}tokens [token] (more tokens...)` right here.\n\n*Don't paste a bot token in a server*"
                )
                await session(self, ctx.message.author)
        elif any(role.name in MODERATOR_ROLES for role in ctx.message.author.roles):
            ctx.message.delete()
            await ctx.channel.send(
                f"To add tokens, execute `{self.bot.command_prefix}tokens` as a moderator on a server **WITHOUT A BOT TOKEN**. Then in DMs, use `{self.bot.command_prefix}tokens [token] (more tokens...)`\n\n*Seriously don't paste a bot token in a server*"
            )

    async def on_member_leave(self, member):
        # TODO: Check if its a Polyphony member and suspend all system members if it is
        pass


def setup(bot: commands.bot):
    log.debug("Admin module loaded")
    bot.add_cog(Admin(bot))


def teardown(bot):
    log.warning("Admin module unloaded")
