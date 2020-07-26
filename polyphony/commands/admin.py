"""
Admin commands to configure polyphony
"""
import asyncio
import json
import logging
import sqlite3
from typing import List

import discord
from discord.ext import commands
from disputils import BotConfirmation

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
from polyphony.helpers.instances import instances, create_member_instance
from polyphony.helpers.log_message import LogMessage
from polyphony.helpers.message_cache import recently_proxied_messages
from polyphony.helpers.pluralkit import pk_get_member
from polyphony.settings import (
    DEFAULT_INSTANCE_PERMS,
    MODERATOR_ROLES,
    DELETE_LOGS_CHANNEL_ID,
    DELETE_LOGS_USER_ID,
    GUILD_ID,
)

log = logging.getLogger("polyphony." + __name__)

# TODO: Allow logging channel
# TODO: Error Handling
# TODO: "Get" command to get information about a PluralKit member via system id or member id
class Admin(commands.Cog):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.token_session = []

    @commands.group()
    @is_mod()
    async def list(self, ctx: commands.context):
        """
        list: Shows all active Polyphony members sorted by main account

        :param ctx: Discord Context
        :param arg1: None/"inactive"/Discord Account
        """
        if ctx.invoked_subcommand is not None:
            return
        log.debug("Listing active members...")
        c.execute("SELECT * FROM members WHERE member_enabled == 1")
        member_list = c.fetchall()
        embed = discord.Embed(title="Active Members")
        await self.send_member_list(ctx, embed, member_list)

    @list.command()
    @is_mod()
    async def all(self, ctx: commands.context):
        log.debug("Listing all members...")
        c.execute("SELECT * FROM members")
        member_list = c.fetchall()
        embed = discord.Embed(title="All Members")
        await self.send_member_list(ctx, embed, member_list)

    @list.command()
    @is_mod()
    async def system(self, ctx: commands.context, member: discord.Member):
        log.debug(f"Listing members for {member.display_name}...")
        c.execute(
            "SELECT * FROM members WHERE discord_account_id == ?", [member.id],
        )
        member_list = c.fetchall()
        embed = discord.Embed(title=f"Members of System")
        embed.set_author(name=f"{member} ({member.id})", icon_url=member.avatar_url)
        await self.send_member_list(ctx, embed, member_list)

    @list.command()
    @is_mod()
    async def suspended(self, ctx: commands.context):
        log.debug("Listing suspended members...")
        c.execute("SELECT * FROM members WHERE member_enabled == 0")
        member_list = c.fetchall()
        embed = discord.Embed(title="Suspended Members")
        await self.send_member_list(ctx, embed, member_list)

    @staticmethod
    async def send_member_list(
        ctx: commands.context, embed, member_list: List[sqlite3.Row]
    ):
        if member_list is None:
            embed.add_field(name="No members where found")

        for member in member_list:
            if len(embed.fields) >= 9:
                await ctx.send(embed=embed)
                embed = discord.Embed()
            member_user = ctx.guild.get_member(member["member_account_id"])
            owner_user = ctx.guild.get_member(member["discord_account_id"])
            tags = []
            for tag in json.loads(member["pk_proxy_tags"]):
                tags.append(
                    "`"
                    + (tag.get("prefix") or "")
                    + "text"
                    + (tag.get("suffix") or "")
                    + "`"
                )
            embed.add_field(
                name=dict(member).get("display_name", member["member_name"]),
                value=f"""**User:** {member_user.mention} (`{member_user.id}`)\n**Account Owner:** {owner_user.mention if hasattr(owner_user, 'mention') else "*Unable to get User*"} (`{member["discord_account_id"]}`)\n**PluralKit Member ID:** `{member['pk_member_id']}`\n**Tag(s):** {' or '.join(tags)}\n**Enabled:** `{bool(member['member_enabled'])}`""",
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
        :param pluralkit_member_id: PluralKit system or member id
        :param account: Main Account to be extended from
        """

        log.debug("Registering new member...")

        logger = LogMessage(ctx, title="Registering...")
        await logger.init()

        instance = None

        async with ctx.channel.typing():
            await logger.log("Fetching member from PluralKit...")
            member = await pk_get_member(pluralkit_member_id)

            # Member exists
            if member is not None:
                system_names = [f"{member['name']} (`{member['id']}`)"]
                await logger.log(
                    f"Fetched member -> {member['name']} (`{member['id']}`)"
                )
                tokens = get_unused_tokens()

                # Fail: No Slots Available
                if len(tokens) == 0:
                    logger.title = "Error Registering: No Slots Available"
                    logger.color = discord.Color.red()
                    await logger.log(
                        f"No tokens in queue. Run `{self.bot.command_prefix}tokens` for information on how to add more."
                    )
                    return

                # Confirm add
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

                # Get a token and update as used
                bot_token = tokens[0]
                update_token_as_used(bot_token["token"])

                # Insert new user into users database
                if get_user(account.id) is None:
                    await logger.log(
                        f"{account.mention} is a new user! Registering them with Polyphony"
                    )
                    insert_user(account.id)

                # Insert member unless already registered
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

                # Fail: Member Already Registered
                else:
                    logger.title = "Member Already Registered with Polyphony"
                    logger.color = discord.Color.light_grey()
                    await logger.log(
                        f"Member ID `{pluralkit_member_id}` was already registered with Polyphony"
                    )
                    return
                await logger.log("Creating member instance...")
                instance = create_member_instance(get_member(member["id"]))

            # Fail: Invalid ID
            else:
                logger.title = "Error Registering: Member ID invalid"
                logger.color = discord.Color.red()
                await logger.log(f"Member ID `{pluralkit_member_id}` was not found")
                return

        # Success State
        logger.title = f"Registration of {member['name']} Successful"
        logger.color = discord.Color.green()
        c.execute("SELECT * FROM tokens WHERE used = 0")
        slots = c.fetchall()
        await logger.log(f"There are now {len(slots)} slots available")
        await logger.log(f"\nUser is {instance.user.mention}")
        log.info("New member instance extended and activated")

    @commands.group()
    @is_mod()
    async def syncall(self, ctx: commands.context):
        if ctx.invoked_subcommand is not None:
            return
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
            sync_state = instance.sync()
            if await sync_state == 0:
                logger.content[
                    -1
                ] = f":white_check_mark: Synced {instance.user.mention}"
            elif sync_state == 1:
                logger.content[
                    -1
                ] = f":x: Failed to sync {instance.user.mention} because member ID `{instance.pk_member_id}` was not found on PluralKit's servers"
            else:
                logger.content[
                    -1
                ] = f":x: Failed to sync {instance.user.mention} becanse main user left server. Instance has been automatically suspended."
        logger.title = ":white_check_mark: Sync Complete"
        logger.color = discord.Color.green()
        await logger.update()
        log.info("Sync all complete")

    @syncall.command()
    @is_mod()
    async def system(self, ctx: commands.context, main_user: discord.User):
        """
        Sync system members with PluralKit

        :param main_user: User to sync for
        :param ctx: Discord Context
        """
        logger = LogMessage(
            ctx, title=f":hourglass: Syncing All Members for {main_user}..."
        )
        logger.color = discord.Color.orange()
        for instance in instances:
            if instance.main_user_account_id == main_user.id:
                await logger.log(f":hourglass: Syncing {instance.user.mention}...")
                try:
                    await instance.sync()
                    logger.content[
                        -1
                    ] = f":white_check_mark: Synced {instance.user.mention}"
                except TypeError:
                    logger.content[-1] = f":x: Failed to sync {instance.user.mention}"
        logger.title = ":white_check_mark: Sync Complete"
        logger.color = discord.Color.green()
        await logger.update()

    @syncall.command()
    @is_mod()
    async def member(self, ctx: commands.context, system_member: discord.User):
        """
        Sync system member with PluralKit

        :param system_member: User to sync
        :param ctx: Discord Context
        """
        logger = LogMessage(ctx, title=f":hourglass: Syncing {system_member}...")
        logger.color = discord.Color.orange()
        for instance in instances:
            if instance.user.id == system_member.id:
                await logger.log(f":hourglass: Syncing {instance.user.mention}...")
                try:
                    await instance.sync()
                    logger.content[
                        -1
                    ] = f":white_check_mark: Synced {instance.user.mention}"
                except TypeError:
                    logger.content[-1] = f":x: Failed to sync {instance.user.mention}"
        logger.title = ":white_check_mark: Sync Complete"
        logger.color = discord.Color.green()
        await logger.update()

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
        await ctx.message.delete()
        for i, instance in enumerate(instances):
            if instance.user.id == system_member.id:
                await instance.close()
                with conn:
                    c.execute(
                        "UPDATE members SET member_enabled = 0 WHERE token = ?",
                        [instance.get_token()],
                    )
                del instances[i]
                await ctx.send(
                    f"{system_member.mention} suspended by {ctx.author.mention}"
                )
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
        await ctx.message.delete()
        member = get_member_by_discord_id(system_member.id)
        if member is not None:
            if not member["member_enabled"]:
                c.execute(
                    "UPDATE members SET member_enabled = 1 WHERE member_account_id = ?",
                    [system_member.id],
                )
                instances.append(create_member_instance(member))
                await ctx.send(
                    f"{system_member.mention} started by {ctx.message.author.mention}"
                )
                log.info(f"{system_member} has been started by {ctx.message.author}")
            else:
                await ctx.send(f"{system_member.mention} is already running")

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
                await ctx.send(
                    f"{system_member.mention} disabled permanently by {ctx.message.author}"
                )
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
                logger = LogMessage(ctx, title=f"Adding token #{index+1}...")
                await logger.init()
                # Check token
                await logger.log(f"Checking token #{index+1}...")
                check_result, client_id = await check_token(token)
                if not check_result:
                    logger.title = f"Token #{index+1} Invalid"
                    logger.color = discord.Color.red()
                    await logger.log("Bot token is invalid")
                else:
                    await logger.log("Token valid")
                    if get_token(token) is None:
                        log.info("Adding new token to database")
                        insert_token(token, False)
                        logger.title = f"Bot token #{index+1} added"
                        logger.color = discord.Color.green()
                        c.execute("SELECT * FROM tokens WHERE used = 0")
                        slots = c.fetchall()
                        from polyphony.bot import bot

                        await logger.send(
                            f"[Invite to Server]({discord.utils.oauth_url(client_id, permissions=discord.Permissions(DEFAULT_INSTANCE_PERMS), guild=bot.get_guild(GUILD_ID))})\n\n**Client ID:** {client_id}\nThere are now {len(slots)} slot(s) available"
                        )
                    else:
                        logger.title = f"Token #{index+1} already in database"
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

    async def on_message(self, msg: discord.Message):
        if (
            msg.channel.id == DELETE_LOGS_CHANNEL_ID
            or msg.author.id == DELETE_LOGS_USER_ID
        ):

            log.debug(f"New message {msg.id} that might be a delete log found.")

            try:
                embed_text = msg.embeds[0].description
            except IndexError:
                return

            for oldmsg in recently_proxied_messages:
                if str(oldmsg.id) in embed_text:
                    log.debug(
                        f"Deleting delete log message {msg.id} (was about {oldmsg.id})"
                    )
                    await msg.delete()


def setup(bot: commands.bot):
    log.debug("Admin module loaded")
    bot.add_cog(Admin(bot))


def teardown(bot):
    log.warning("Admin module unloaded")
