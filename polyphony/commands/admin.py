"""
Admin commands to configure polyphony
"""
import asyncio
import logging
import sqlite3
from typing import Union

import discord
from discord.ext import commands
from disputils import BotConfirmation

from polyphony.helpers.checks import is_mod, check_token
from polyphony.helpers.database import (
    insert_member,
    c,
    conn,
)
from polyphony.helpers.decode_token import decode_token
from polyphony.helpers.log_message import LogMessage
from polyphony.helpers.member_list import send_member_list
from polyphony.helpers.pluralkit import pk_get_member
from polyphony.helpers.reset import reset
from polyphony.helpers.sync import sync
from polyphony.instance.bot import PolyphonyInstance
from polyphony.settings import (
    DEFAULT_INSTANCE_PERMS,
    MODERATOR_ROLES,
    GUILD_ID, )

log = logging.getLogger("polyphony." + __name__)

# TODO: Implement log_to_channel
# TODO: Error Handling
# TODO: "Get" command to get information about a PluralKit member via system id or member id

# TODO: Deregister all suspended users (purge)
# TODO: Enable all suspended users
# TODO: Rescue orphaned tokens
# TODO: Purge strikeout instances that have no meessages on the server to open up available tokens


class Admin(commands.Cog):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.token_session = []

    @commands.group()
    @commands.check_any(commands.is_owner(), is_mod())
    async def list(self, ctx: commands.context):
        """
        list: Shows all active Polyphony members sorted by main account

        :param ctx: Discord Context
        """
        if ctx.invoked_subcommand is not None:
            return
        log.debug("Listing active members...")
        c.execute("SELECT * FROM members WHERE member_enabled == 1")
        member_list = c.fetchall()
        embed = discord.Embed(title="Active Members")
        await send_member_list(ctx, embed, member_list)

    @list.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def all(self, ctx: commands.context):
        log.debug("Listing all members...")
        c.execute("SELECT * FROM members")
        member_list = c.fetchall()
        embed = discord.Embed(title="All Members")
        await send_member_list(ctx, embed, member_list)

    @list.command(name="system")
    @commands.check_any(commands.is_owner(), is_mod())
    async def _system(self, ctx: commands.context, member: discord.Member):
        log.debug(f"Listing members for {member.display_name}...")
        c.execute(
            "SELECT * FROM members WHERE main_account_id == ?",
            [member.id],
        )
        member_list = c.fetchall()
        embed = discord.Embed(title=f"Members of System")
        embed.set_author(name=f"{member} ({member.id})", icon_url=member.avatar_url)
        await send_member_list(ctx, embed, member_list)

    @list.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def suspended(self, ctx: commands.context):
        log.debug("Listing suspended members...")
        c.execute("SELECT * FROM members WHERE member_enabled == 0")
        member_list = c.fetchall()
        embed = discord.Embed(title="Suspended Members")
        await send_member_list(ctx, embed, member_list)

    @commands.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def register(
        self,
        ctx: commands.context,
        pluralkit_member_id: str,
        account: discord.Member,
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

        async with ctx.channel.typing():
            # Error: Account is not a user
            if account.bot is True:
                await logger.set(
                    title="Error Registering: Bad Account Pairing",
                    color=discord.Color.red(),
                )
                await logger.log(f"{account.mention} is a bot user")
                return

            # Get available tokens
            token = conn.execute("SELECT * FROM tokens WHERE used == 0").fetchone()

            # Error: No Slots Available
            if not token:
                await logger.set(
                    title=":x: Error Registering: No Slots Available",
                    color=discord.Color.red(),
                )
                await logger.log(
                    f":x: No tokens in queue. Run `{self.bot.command_prefix}tokens` for information on how to add more."
                )
                return

            # Error: Duplicate Registration
            check_duplicate = conn.execute(
                "SELECT * FROM members WHERE pk_member_id == ?",
                [pluralkit_member_id],
            ).fetchone()
            if check_duplicate:
                await logger.set(
                    title=":x: Error Registering: Member Already Registered",
                    color=discord.Color.red(),
                )
                await logger.log(
                    f":x: Member ID `{pluralkit_member_id}` is already registered with instance {self.bot.get_user(check_duplicate['id'])}"
                )
                return

            # Fetch member from PluralKit
            await logger.log(":hourglass: Fetching member from PluralKit...")
            member = await pk_get_member(pluralkit_member_id)

            # Error: Member not found
            if member is None:
                await logger.set(
                    title=":x: Error Registering: Member ID invalid",
                    color=discord.Color.red(),
                )
                await logger.log(f":x: Member ID `{pluralkit_member_id}` was not found")
                return

            # Error: Missing PluralKit Data
            if (
                member["name"] is None
                or member["avatar_url"] is None
                or member["proxy_tags"] is None
            ):
                await logger.set(
                    title=":x: Error Registering: Missing PluralKit Data",
                    color=discord.Color.red(),
                )
                if member["name"] is None:
                    await logger.log(":warning: Member is missing a name")
                if member["avatar_url"] is None:
                    await logger.log(":warning: Member is missing an avatar")
                if member["proxy_tags"] is None:
                    await logger.log(":warning: Member is missing proxy tags")
                await logger.log(
                    "\n:x: *Please check the privacy settings on PluralKit*"
                )
                return

            system_name = f"__**{member['name']}**__ (`{member['id']}`)"
            await logger.edit(
                -1,
                f":white_check_mark: Fetched member __**{member['name']}**__ (`{member['id']}`)",
            )

            # Confirm add
            confirmation = BotConfirmation(ctx, discord.Color.blue())
            await confirmation.confirm(
                f":grey_question: Create member for {account} with member {system_name}?"
            )
            if confirmation.confirmed:
                await confirmation.message.delete()
            else:
                await confirmation.message.delete()
                await logger.set(
                    title=":x: Registration Cancelled", color=discord.Color.red()
                )
                await logger.log(":x: Registration cancelled by user")
                return

            # Check if user is new to Polyphony
            if (
                conn.execute(
                    "SELECT * FROM users WHERE id = ?", [account.id]
                ).fetchone()
                is None
            ):
                await logger.log(
                    f":tada: {account.mention} is a new user! Registering them with Polyphony"
                )
                conn.execute("INSERT INTO users VALUES (?, NULL, NULL)", [account.id])
                conn.commit()

            # Insert member into database
            await logger.log(":hourglass: Adding to database...")
            try:
                insert_member(
                    token["token"],
                    member["id"],
                    account.id,
                    decode_token(token["token"]),
                    member["name"],
                    member["display_name"],
                    member["avatar_url"],
                    member["proxy_tags"],
                    member["keep_proxy"],
                    member_enabled=True,
                )
                await logger.edit(-1, ":white_check_mark: Added to database")

            # Error: Database Error
            except sqlite3.Error as e:
                log.error(e)
                await logger.set(
                    title=":x: Error Registering: Database Error",
                    color=discord.Color.red(),
                )
                await logger.edit(-1, ":x: An unknown database error occurred")
                return

            # Mark token as used
            conn.execute(
                "UPDATE tokens SET used = 1 WHERE token = ?",
                [token["token"]],
            )
            conn.commit()

            # Create Instance
            await logger.log(":hourglass: Syncing Instance...")
            instance = PolyphonyInstance(pluralkit_member_id)
            asyncio.run_coroutine_threadsafe(
                instance.start(token["token"]), self.bot.loop
            )
            await instance.wait_until_ready()

            sync_error_text = ""

            # Update Username
            await logger.edit(-1, f":hourglass: Syncing Username...")
            out = await instance.update_username(member["name"])
            if out != 0:
                sync_error_text += f"> {out}\n"

            # Update Avatar URL
            await logger.edit(-1, f":hourglass: Syncing Avatar...")
            out = await instance.update_avatar(member["avatar_url"])
            if out != 0:
                sync_error_text += f"> {out}\n"

            # Update Nickname
            await logger.edit(-1, f":hourglass: Syncing Nickname...")
            out = await instance.update_nickname(member["display_name"])
            if out < 0:
                sync_error_text += f"> PluralKit display name must be 32 or fewer in length if you want to use it as a nickname"
            elif out > 0:
                sync_error_text += f"> Nick didn't update on {out} guild(s)\n"

            # Update Roles
            await logger.edit(-1, f":hourglass: Updating Roles...")
            out = await instance.update_default_roles()
            if out:
                sync_error_text += f"> {out}\n"

            if sync_error_text == "":
                await logger.edit(-1, ":white_check_mark: Synced instance")
            else:
                await logger.edit(-1, ":warning: Synced instance with errors:")
                await logger.log(sync_error_text)

        # Success State
        logger.content = []
        await logger.set(
            title=f":white_check_mark: Registered __{member['name']}__",
            color=discord.Color.green(),
        )

        slots = conn.execute("SELECT * FROM tokens WHERE used = 0").fetchall()
        await logger.log(f":arrow_forward: **User is {instance.user.mention}**")
        if sync_error_text != "":
            await logger.log(":warning: Synced instance with errors:")
            await logger.log(sync_error_text)
        await logger.log(f"*There are now {len(slots)} slots available*")
        log.info(
            f"{instance.user} ({instance.pk_member_id}): New member instance registered ({len(slots)} slots left)"
        )
        await instance.close()

    @commands.group()
    @commands.check_any(commands.is_owner(), is_mod())
    async def syncall(self, ctx: commands.context):
        if ctx.invoked_subcommand is not None:
            return
        await sync(
            ctx,
            conn.execute("SELECT * FROM members WHERE member_enabled = 1").fetchall(),
        )

    @syncall.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def system(self, ctx: commands.context, main_user: discord.User):
        """
        Sync system members with PluralKit

        :param main_user: User to sync for
        :param ctx: Discord Context
        """
        await sync(
            ctx,
            conn.execute(
                "SELECT * FROM members WHERE main_account_id = ?", [main_user.id]
            ).fetchall(),
        )

    @syncall.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def member(self, ctx: commands.context, system_member: discord.User):
        """
        Sync system member with PluralKit

        :param system_member: User to sync
        :param ctx: Discord Context
        """
        await sync(
            ctx,
            conn.execute(
                "SELECT * FROM members WHERE id = ?", [system_member.id]
            ).fetchall(),
        )

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
        await ctx.message.delete()
        member = conn.execute(
            "SELECT * FROM members WHERE id = ?",
            [system_member.id],
        ).fetchone()
        if member is not None:
            if member["member_enabled"] == 0:
                await ctx.send(
                    embed=discord.Embed(
                        description=f":information_source: {system_member.mention} already suspended",
                        color=discord.Color.blue(),
                    ),
                    delete_after=10,
                )
            else:
                conn.execute(
                    "UPDATE members SET member_enabled = 0 WHERE id = ?",
                    [system_member.id],
                )
                conn.commit()
                await ctx.send(
                    embed=discord.Embed(
                        description=f":white_check_mark: {system_member.mention} suspended by {ctx.author.mention}",
                        color=discord.Color.green(),
                    )
                )
                log.info(f"{system_member} has been suspended by {ctx.message.author}")
        else:
            await ctx.send(
                embed=discord.Embed(
                    description=f":x: {system_member.mention} not found in database",
                    color=discord.Color.red(),
                ),
                delete_after=10,
            )

    @commands.command(aliases=["start"])
    @commands.check_any(commands.is_owner(), is_mod())
    async def enable(self, ctx: commands.context, system_member: discord.Member):
        """
        Reintroduce a suspended instance into the wild

        :param ctx: Discord Context
        :param system_member: System Member
        """
        await ctx.message.delete()
        member = conn.execute(
            "SELECT * FROM members WHERE id = ?",
            [system_member.id],
        ).fetchone()
        if member is not None:
            if member["member_enabled"] == 1:
                await ctx.send(
                    embed=discord.Embed(
                        description=f":information_source: {system_member.mention} already enabled",
                        color=discord.Color.blue(),
                    ),
                    delete_after=10,
                )
            else:
                conn.execute(
                    "UPDATE members SET member_enabled = 1 WHERE id = ?",
                    [system_member.id],
                )
                conn.commit()
                await ctx.send(
                    embed=discord.Embed(
                        description=f":white_check_mark: {system_member.mention} enabled by {ctx.author.mention}",
                        color=discord.Color.green(),
                    )
                )
                log.info(f"{system_member} has been enabled by {ctx.message.author}")
        else:
            await ctx.send(
                embed=discord.Embed(
                    description=f":x: {system_member.mention} not found in database",
                    color=discord.Color.red(),
                ),
                delete_after=10,
            )

    @commands.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def disable(self, ctx: commands.context, system_member: discord.Member):
        """
        Disables a system member permanently by deleting it from the database and kicking it from the server. Bot token cannot be reused.

        :param ctx: Discord Context
        :param system_member: System Member
        """
        await ctx.message.delete()
        member = conn.execute(
            "SELECT * FROM members WHERE id = ?",
            [system_member.id],
        ).fetchone()
        if member is not None:
            log.debug(f"Disabling {system_member}")
            confirmation = BotConfirmation(ctx, discord.Color.red())
            await confirmation.confirm(
                f"Disable member __{system_member}__ **permanently?**"
            )
            if confirmation.confirmed:
                await confirmation.message.delete()
                conn.execute(
                    "DELETE FROM members WHERE id = ?",
                    [system_member.id],
                )
                conn.commit()
                await ctx.send(
                    embed=discord.Embed(
                        description=f":ballot_box_with_check: {system_member.mention} **permanently disabled** by {ctx.author.mention}",
                        color=discord.Color.dark_green(),
                    )
                )
                log.info(
                    f"{system_member} has been permanently by {ctx.message.author}"
                )
            else:
                await confirmation.message.delete()
                await ctx.send(
                    embed=discord.Embed(
                        description=f":information_source: {system_member.mention} was __not__ disabled",
                        color=discord.Color.blue(),
                    ),
                    delete_after=10,
                )
                log.info(f"{system_member} not disabled")
        else:
            await ctx.send(
                embed=discord.Embed(
                    description=f":x: {system_member.mention} not found in database",
                    color=discord.Color.red(),
                ),
                delete_after=10,
            )

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
            for index, token in enumerate(tokens):
                logger = LogMessage(ctx, title=f"Adding token #{index+1}...")
                await logger.init()
                # Check token
                await logger.log(f"Checking token #{index+1}...")
                all_tokens = conn.execute("SELECT * FROM tokens").fetchall()
                chk = False
                token_client = decode_token(token)
                for chk_token in all_tokens:
                    if decode_token(str(chk_token["token"])) == token_client:
                        chk = True
                check_result, client_id = await check_token(token)
                if chk:
                    logger.title = f"Token #{index + 1} Client ID already in database"
                    logger.color = discord.Color.red()
                    await logger.log("Client ID already exists in database")
                elif not check_result:
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
                        log.info(
                            f"New token added by {ctx.author} (There are now {len(slots)} slots)"
                        )
                    else:
                        logger.title = f"Token #{index+1} already in database"
                        logger.color = discord.Color.orange()
                        await logger.log("Bot token already in database")
        elif ctx.channel.type is not discord.ChannelType.private:
            await ctx.message.delete()
            if any(
                role.name in MODERATOR_ROLES for role in ctx.message.author.roles
            ) or await ctx.bot.is_owner(ctx.author):
                try:
                    await ctx.message.author.send(
                        f"Token mode enabled for 5 minutes. Add tokens with `{self.bot.command_prefix}tokens [token] (more tokens...)` right here.\n\n*Don't paste a bot token in a server*"
                    )
                except discord.errors.Forbidden:
                    await ctx.send(
                        "Enable server DMs to use token command", delete_after=10.0
                    )
                await session(self, ctx.message.author)
            elif any(
                role.name in MODERATOR_ROLES for role in ctx.message.author.roles
            ) or ctx.bot.is_owner(ctx.author):
                await ctx.channel.send(
                    f"To add tokens, execute `{self.bot.command_prefix}tokens` as a moderator on a server **WITHOUT A BOT TOKEN**. Then in DMs, use `{self.bot.command_prefix}tokens [token] (more tokens...)`\n\n*Seriously don't paste a bot token in a server*",
                    delete_after=10.0,
                )

    @commands.command()
    async def tokenup(self, ctx: commands.context, member: discord.Member = None, token: str = None):
        """
        Add tokens to queue

        :param ctx: Discord Context
        :param token: Token
        :param member: System member
        """

        # TODO: Clean orphaned tokens

        async def session(self, author: discord.Member):
            self.token_session.append(author)
            await asyncio.sleep(300)
            self.token_session.remove(author)

        if (
                ctx.channel.type is discord.ChannelType.private
                and ctx.message.author in self.token_session
        ):
            await ctx.send("Updating token...")
            logger = LogMessage(ctx, title=f"Updating token...")
            await logger.init()
            # Check token
            await logger.log(f"Checking token...")

            # Step 1: check_token
            # Step 2: Check token decodes to match inputted ID

            check_result, client_id = await check_token(token)
            if not check_result:
                logger.title = f"Token Invalid"
                logger.color = discord.Color.red()
                await logger.log("Bot token is invalid")

            if decode_token(token) == member.id:
                await logger.log("Token valid")
                if (
                        conn.execute(
                            "SELECT * FROM tokens WHERE token = ?", [token]
                        ).fetchone()
                        is None
                ):
                    conn.execute("INSERT INTO tokens VALUES(?, ?)", [token, True])
                    conn.execute(
                        "UPDATE members SET token = ? WHERE id = ?",
                        [token, member.id],
                    )
                    conn.commit()
                    logger.title = f"Token updated"
                    logger.color = discord.Color.green()

                    await logger.send(
                        f"Token for {member.mention} has been updated"
                    )
                    log.info(
                        f"Token for {member.id} updated by {ctx.author}"
                    )
                else:
                    logger.title = f"Token is already in database"
                    logger.color = discord.Color.orange()
                    await logger.log("Bot token already in database")

            else:
                logger.title = f"Incorrect Token"
                logger.color = discord.Color.red()
                await logger.log(f"Token does not belong to {member.mention}")
        elif ctx.channel.type is not discord.ChannelType.private:
            await ctx.message.delete()
            if any(
                    role.name in MODERATOR_ROLES for role in ctx.message.author.roles
            ) or await ctx.bot.is_owner(ctx.author):
                try:
                    await ctx.message.author.send(
                        f"Token mode enabled for 5 minutes. Update tokens with `{self.bot.command_prefix}tokenup [system member] [token]` right here.\n\n*Don't paste a bot token in a server*"
                    )
                except discord.errors.Forbidden:
                    await ctx.send(
                        "Enable server DMs to use tokenup command", delete_after=10.0
                    )
                await session(self, ctx.message.author)
            elif any(
                    role.name in MODERATOR_ROLES for role in ctx.message.author.roles
            ) or ctx.bot.is_owner(ctx.author):
                await ctx.channel.send(
                    f"To add tokens, execute `{self.bot.command_prefix}tokenup` as a moderator on a server **WITHOUT A BOT TOKEN**. Then in DMs, use `{self.bot.command_prefix}tokenup [system member] [token]`\n\n*Seriously don't paste a bot token in a server*",
                    delete_after=10.0,
                )

    @commands.command()
    @commands.check_any(commands.is_owner(), is_mod())
    async def reset(self, ctx: commands.context):
        with ctx.typing():
            await reset()
        await ctx.send(
            embed=discord.Embed(
                title=":white_check_mark: Polyphony helper has been reset",
                color=discord.Color.green(),
            )
        )


def setup(bot: commands.bot):
    log.debug("Admin module loaded")
    bot.add_cog(Admin(bot))


def teardown(bot):
    log.warning("Admin module unloaded")
