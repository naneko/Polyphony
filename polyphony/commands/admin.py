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
)
from polyphony.helpers.helpers import LogMessage
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
        self, ctx: commands.context, arg1: Union[discord.Member, str] = None
    ):
        """
        list: Shows all active Polyphony members sorted by main account
        list inactive: Shows systems and main accounts that haven’t been used in n number of days defined in the config or at all or where the main user has left the server
        list [main account]: Lists all polyphony system members for a given main account
        list all: Lists all Polyphony members registered

        :param ctx: Discord Context
        :param arg1: None/"inactive"/Discord Account
        """
        embed = discord.Embed()
        inline = True
        member_list = []

        if arg1 is None:
            log.debug("Listing active members...")
            c.execute("SELECT * FROM members WHERE member_enabled == 1")
            member_list = c.fetchall()
            embed = discord.Embed(title="Active Members")
        elif isinstance(arg1, discord.Member):
            log.debug(f"Listing members for {arg1.display_name}...")
            c.execute("SELECT * FROM members WHERE discord_account_id == ?", [arg1.id])
            member_list = c.fetchall()
            embed = discord.Embed(title=f"Members of System")
            embed.set_author(name=f"{arg1} ({arg1.id})", icon_url=arg1.avatar_url)
        elif arg1.lower() == "inactive":
            log.debug("Listing inactive members...")
            c.execute("SELECT * FROM members WHERE member_enabled == 0")
            member_list = c.fetchall()
            embed = discord.Embed(title="Inactive Members")
        elif arg1.lower() == "all":
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
            member_user = ctx.guild.get_member_named(f"p.{member['member_name']}")
            owner_user = ctx.guild.get_member(member["discord_account_id"])
            embed.add_field(
                name=member["display_name"],
                value=f"""User: {member_user.mention} (`{member_user.id}`)\nAccount Owner: {owner_user.mention} (`{owner_user.id}`)\nPluralKit Member ID: `{member['pk_member_id']}`\nEnabled: `{bool(member['member_enabled'])}`""",
                inline=inline,
            )
            inline = not inline

        await ctx.send(embed=embed)

    @commands.command()
    @is_mod()
    async def register(
        self, ctx: commands.context, pk_id: str, account: discord.Member
    ):
        """
        register [member id] [main account] (bot token): Creates a new Polyphony member instance

        :param ctx: Discord Context
        :param account: Main Account to be extended from
        :param pk_id: PluralKit system or member id
        """

        log.debug("Registering new member...")

        logger = LogMessage(ctx, title="Registering...")
        await logger.init()

        async with ctx.channel.typing():
            await logger.log("Fetching member from PluralKit...")
            member = await pk_get_member(pk_id)
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
                if get_member(pk_id) is None:
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
                        f"Member ID `{pk_id}` was already registered with Polyphony"
                    )
                    return
                await logger.log("Creating member instance...")
                create_member_instance(get_member(member["id"]))
            else:
                logger.title = "Error Registering: Member ID invalid"
                logger.color = discord.Color.red()
                await logger.log(f"Member ID `{pk_id}` was not found")
                return

        confirmation = BotConfirmation(ctx, discord.Color.blue())
        await confirmation.confirm(
            f"Create member for {account} with member(s) {', '.join(system_names)}?"
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
        await logger.log("\n*Generate an invite link using `invite [Client ID]`*")
        log.info("New member instance extended and activated")
        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(
            name=f"{member['display_name']} (p.{member['member_name']})",
            icon_url=member["avatar_url"],
        )
        await ctx.send(embed=embed)

    @commands.command()
    @is_mod()
    async def invite(self, ctx: commands.context, client_id: str):
        """
        invite [client id]: Generates an invite link with pre-set permissions from client ID.

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
        suspend [system member]: Sets member_enabled to false. Pulls the member instance offline.

        :param ctx: Discord Context
        :param system_member: System Member
        """
        # TODO: Implement
        await ctx.send("Suspend command unimplemented")
        log.warning("Suspend command unimplemented")

    @commands.command()
    @is_mod()
    async def disable(self, ctx: commands.context, system_member: discord.Member):
        """
        disable [system member]: Disables a system member by deleting it from the database and kicking it from the server. Bot token cannot be reused.

        :param ctx: Discord Context
        :param system_member: System Member
        """
        # TODO: Implement
        await ctx.send("Disable command unimplemented")
        log.warning("Disable command unimplemented")

    @commands.command()
    async def tokens(self, ctx: commands.context, *tokens: str):
        """
        tokens [token] (more tokens...): Add tokens to queue

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
                        await logger.send(None)
                    else:
                        logger.title = f"Token {index} already in database"
                        logger.color = discord.Color.orange()
                        await logger.log("Bot token already in database")
        elif ctx.channel.type is not discord.ChannelType.private:
            ctx.message.delete()
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
