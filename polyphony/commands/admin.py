"""
Admin commands to configure polyphony
"""
import asyncio
import json
import logging
import sqlite3
from typing import List, Union

import discord
from discord.ext import commands
from disputils import BotConfirmation

from polyphony.helpers.checks import is_mod, check_token
from polyphony.helpers.database import (
    insert_member,
    c,
    conn,
)
from polyphony.helpers.instances import (
    instances,
    create_member_instance,
    update_presence,
)
from polyphony.helpers.log_message import LogMessage
from polyphony.helpers.pluralkit import pk_get_member
from polyphony.settings import (
    DEFAULT_INSTANCE_PERMS,
    MODERATOR_ROLES,
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

    @commands.command()
    @commands.is_owner()
    async def upgrade(self, ctx: commands.context):
        from git import Repo

        with ctx.channel.typing():
            repo = Repo("..")
            o = repo.remotes.origin
            o.pull()

        await ctx.send(
            f"Polyphony pulled `{repo.heads[0].commit}` from master branch. Run `;;reload` or `;;reload all` to complete upgrade."
        )

    @commands.group()
    @commands.check_any(commands.is_owner(), is_mod())
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
    @commands.check_any(commands.is_owner(), is_mod())
    async def all(self, ctx: commands.context):
        log.debug("Listing all members...")
        c.execute("SELECT * FROM members")
        member_list = c.fetchall()
        embed = discord.Embed(title="All Members")
        await self.send_member_list(ctx, embed, member_list)

    @list.command(name="system")
    @commands.check_any(commands.is_owner(), is_mod())
    async def _system(self, ctx: commands.context, member: discord.Member):
        log.debug(f"Listing members for {member.display_name}...")
        c.execute(
            "SELECT * FROM members WHERE discord_account_id == ?", [member.id],
        )
        member_list = c.fetchall()
        embed = discord.Embed(title=f"Members of System")
        embed.set_author(name=f"{member} ({member.id})", icon_url=member.avatar_url)
        await self.send_member_list(ctx, embed, member_list)

    @list.command()
    @commands.check_any(commands.is_owner(), is_mod())
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
    @commands.check_any(commands.is_owner(), is_mod())
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
                system_name = f"{member['name']} (`{member['id']}`)"
                await logger.log(
                    f"Fetched member -> {member['name']} (`{member['id']}`)"
                )
                tokens = conn.execute("SELECT * FROM tokens WHERE used == 0").fetchall()

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
                    f"Create member for {account} with member {system_name}?"
                )
                if confirmation.confirmed:
                    await confirmation.message.delete()
                    await logger.log("Adding to database...")
                else:
                    await confirmation.message.delete()
                    logger.title = "Registration Cancelled"
                    logger.color = discord.Color.red()
                    await logger.log("Registration cancelled by user")
                    return

                # Get a token
                bot_token = tokens[0]

                # Insert new user into users database
                if (
                    conn.execute(
                        "SELECT * FROM users WHERE discord_account_id = ?", [account.id]
                    ).fetchone()
                    is None
                ):
                    await logger.log(
                        f"{account.mention} is a new user! Registering them with Polyphony"
                    )
                    conn.execute("INSERT INTO users VALUES(?)", [account.id])
                    conn.commit()

                # Insert member unless already registered
                if (
                    conn.execute(
                        "SELECT * FROM members WHERE pk_member_id == ?",
                        [pluralkit_member_id],
                    ).fetchone()
                    is None
                ):
                    insert_member(
                        bot_token["token"],
                        member["id"],
                        account.id,
                        0,
                        member["name"],
                        member["display_name"],
                        member["avatar_url"],
                        member["proxy_tags"],
                        member["keep_proxy"],
                        member_enabled=True,
                    )

                    # Mark token as used
                    conn.execute(
                        "UPDATE tokens SET used = 1 WHERE token = ?",
                        [bot_token["token"]],
                    )
                    conn.commit()

                # Fail: Member Already Registered
                else:
                    logger.title = "Member Already Registered with Polyphony"
                    logger.color = discord.Color.light_grey()
                    await logger.log(
                        f"Member ID `{pluralkit_member_id}` was already registered with Polyphony"
                    )
                    return
                await logger.log("Creating member instance...")
                instance = create_member_instance(
                    conn.execute(
                        "SELECT * FROM members WHERE pk_member_id == ?", [member["id"]]
                    ).fetchone()
                )
                await logger.log("Syncing member instance...")
                await instance.sync()
                await instance.wait_until_ready()
                await update_presence(
                    instance, name=self.bot.get_user(instance.user.id)
                )

            # Fail: Invalid ID
            else:
                logger.title = "Error Registering: Member ID invalid"
                logger.color = discord.Color.red()
                await logger.log(f"Member ID `{pluralkit_member_id}` was not found")
                return

        # Success State
        logger.title = f"Registration of {member['name']} Successful"
        logger.color = discord.Color.green()

        slots = conn.execute("SELECT * FROM tokens WHERE used = 0").fetchall()
        await logger.log(f"There are now {len(slots)} slots available")
        await logger.log(f"\nUser is {instance.user.mention}")
        log.info("New member instance registered and activated")

    @commands.group()
    @commands.check_any(commands.is_owner(), is_mod())
    async def syncall(self, ctx: commands.context):
        if ctx.invoked_subcommand is not None:
            return
        log.info("Syncing all...")
        logger = LogMessage(ctx, title=":hourglass: Syncing All Members...")
        logger.color = discord.Color.orange()

        for i, instance in enumerate(instances):
            try:
                if len(logger.content) > 30:
                    logger.title = ":white_check_mark: Batch Complete"
                    logger.color = discord.Color.green()
                    await logger.update()
                    logger = LogMessage(
                        ctx, title=":hourglass: Syncing Next Batch of Members..."
                    )
                    logger.color = discord.Color.orange()
                await logger.log(
                    f":hourglass: Syncing {instance.user.mention}... ({i}/{len(instances)})"
                )
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
            except AttributeError as e:
                log.error(e)
                await logger.log(
                    f":x: Failed to sync {instance.member_name} ({instance.pk_member_id}) due to an unknown error."
                )
        logger.title = ":white_check_mark: Sync Complete"
        logger.color = discord.Color.green()
        await logger.update()
        log.info("Sync all complete")

    @syncall.command()
    @commands.check_any(commands.is_owner(), is_mod())
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
            try:
                if instance.main_user_account_id == main_user.id:
                    await logger.log(f":hourglass: Syncing {instance.user.mention}...")
                    try:
                        await instance.sync()
                        logger.content[
                            -1
                        ] = f":white_check_mark: Synced {instance.user.mention}"
                    except TypeError:
                        logger.content[
                            -1
                        ] = f":x: Failed to sync {instance.user.mention}"
            except AttributeError as e:
                log.error(e)
                await logger.log(
                    f":x: Failed to sync {instance.member_name} ({instance.pk_member_id}) due to an unknown error."
                )
        logger.title = ":white_check_mark: Sync Complete"
        logger.color = discord.Color.green()
        await logger.update()

    @syncall.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def member(self, ctx: commands.context, system_member: discord.User):
        """
        Sync system member with PluralKit

        :param system_member: User to sync
        :param ctx: Discord Context
        """
        logger = LogMessage(ctx, title=f":hourglass: Syncing {system_member}...")
        logger.color = discord.Color.orange()
        for instance in instances:
            try:
                if instance.user.id == system_member.id:
                    await logger.log(f":hourglass: Syncing {instance.user.mention}...")
                    try:
                        await instance.sync()
                        logger.content[
                            -1
                        ] = f":white_check_mark: Synced {instance.user.mention}"
                    except TypeError:
                        logger.content[
                            -1
                        ] = f":x: Failed to sync {instance.user.mention}"
            except AttributeError as e:
                log.error(e)
                await logger.log(
                    f":x: Failed to sync {instance.member_name} ({instance.pk_member_id}) due to an unknown error."
                )
        logger.title = ":white_check_mark: Sync Complete"
        logger.color = discord.Color.green()
        await logger.update()

    @commands.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def invite(self, ctx: commands.context, member: Union[int, discord.Member]):
        """
        Generates an invite link with pre-set permissions from a client ID.

        :param member: Client to generate invite for
        :param ctx: Discord Context
        """
        log.debug("Generating invite link")
        if type(member) is discord.Member:
            member = member.id
        embed = discord.Embed(
            title=f"Invite Link for {ctx.guild.name}",
            url=discord.utils.oauth_url(
                member,
                permissions=discord.Permissions(DEFAULT_INSTANCE_PERMS),
                guild=ctx.guild,
            ),
        )
        embed.set_footer(text=f"Client ID: {member}")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.check_any(commands.is_owner(), is_mod())
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
                instances.pop(i)
                await ctx.send(
                    f"{system_member.mention} suspended by {ctx.author.mention}"
                )
                log.info(f"{system_member} has been suspended by {ctx.message.author}")

    @commands.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def start(self, ctx: commands.context, system_member: discord.Member):
        """
        Starts a suspended instance

        :param ctx: Discord Context
        :param system_member: System Member
        """
        # TODO: Provide more verbose feedback from command
        await ctx.message.delete()
        member = conn.execute(
            "SELECT * FROM members WHERE member_account_id = ?", [system_member.id]
        ).fetchone()
        if member is not None:
            if not member["member_enabled"]:
                with ctx.channel.typing():
                    c.execute(
                        "UPDATE members SET member_enabled = 1 WHERE member_account_id = ?",
                        [system_member.id],
                    )
                    instance = create_member_instance(member)
                    instances.append(instance)
                    await ctx.send(
                        f"{system_member.mention} started by {ctx.message.author.mention}"
                    )
                    log.info(
                        f"{system_member} has been started by {ctx.message.author}"
                    )
                    await instance.sync()
                    await instance.wait_until_ready()
                    await update_presence(
                        instance, name=self.bot.get_user(instance.main_user_account_id)
                    )
            else:
                await ctx.send(f"{system_member.mention} is already running")

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
            await ctx.send("Finished attempting to restart stagnant instances")
            log.info("Finished attempting to restart stagnant instances")
            return
        if system_member == "all":
            log.info("Restarting all instances")
            instance_queue = []
            with ctx.channel.typing():
                for i, instance in enumerate(instances):
                    instance_queue.append(self.restart_helper(instance))
            await asyncio.gather(*instance_queue)
            await ctx.send("Finished attempting to restart all instances")
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
                    await ctx.send(f"{system_member.mention} restarted")

                    log.info(f"{system_member} restarted")
                    break

    @commands.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def disable(self, ctx: commands.context, system_member: discord.Member):
        """
        Disables a system member permanently by deleting it from the database and kicking it from the server. Bot token cannot be reused.

        :param ctx: Discord Context
        :param system_member: System Member
        """
        # TODO: Provide more verbose feedback from command
        instance = conn.execute(
            "SELECT * FROM members WHERE member_account_id = ?", [system_member.id]
        ).fetchone()
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
                    f"{system_member.mention} disabled permanently by {ctx.message.author.mention}"
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
                    if (
                        conn.execute(
                            "SELECT * FROM tokens WHERE token = ?", [token]
                        ).fetchone()
                        is None
                    ):
                        log.info("Adding new token to database")
                        conn.execute("INSERT INTO tokens VALUES(?, ?)", [token, False])
                        conn.commit()
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


def setup(bot: commands.bot):
    log.debug("Admin module loaded")
    bot.add_cog(Admin(bot))


def teardown(bot):
    log.warning("Admin module unloaded")
