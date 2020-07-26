"""
User commands to configure Polyphony
"""
import asyncio
import json
import logging
from datetime import timedelta
from typing import Optional

import discord
from discord.ext import commands

from polyphony.helpers.checks import is_polyphony_user, is_mod
from polyphony.helpers.database import c
from polyphony.helpers.instances import instances
from polyphony.helpers.log_message import LogMessage
from polyphony.settings import (
    NEVER_SYNC_ROLES,
    ALWAYS_SYNC_ROLES,
    DISABLE_ROLESYNC_ROLES,
)

log = logging.getLogger("polyphony." + __name__)


class User(commands.Cog):

    # TODO: Slots command: will show how many tokens are available. (maybe also show with register command)

    def __init__(self, bot: discord.ext.commands.bot):
        self.bot = bot

    @commands.group()
    @is_polyphony_user(allow_mods=True)
    async def help(self, ctx: commands.context):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Polyphony Quick Start",
                name="Polyphony is an extension of PluralKit that allows more control for everyone.",
            )
            embed.add_field(
                name=":pencil: __Editing and deleting messages__",
                value="**__Editing__**"
                "\n**- Method 1:** React with :pencil: to the message and then type your edit"
                "\n**- Method 2:** Type `;;edit <message>` to edit last message sent by a system member"
                "\n**- Method 3:** Type `;;edit (message id) <message> ` to edit a message by it's id"
                "\n\n**__Deleting__**"
                "\n**- Method 1:** React with :x: on the message"
                "\n**- Method 2:** Type `;;del` to delete the last message sent by a system member"
                "\n**- Method 3:** Type `;;del` to delete a message by id"
                "\n\n[How to get the ID]"
                "(https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-)"
                "\n*Method 1 may not work on older messages*",
                inline=False,
            )
            embed.add_field(
                name=":inbox_tray: __Syncing from PluralKit__",
                value="`;;sync` will sync changes for all your members\n"
                "`;;sync member (member mention)` will sync changes for one specific member",
                inline=False,
            )
            embed.add_field(
                name=":information_source: __More Help__",
                value="`;;help user` to get the full command list for Polyphony users"
                "\n`;;help admin` to get the full command list for Moderators *(Moderators Only)*",
            )
            await ctx.channel.send(embed=embed)

    @help.command()
    async def user(self, ctx: commands.context):
        embed = discord.Embed(
            title="Polyphony User Help",
            description="Polyphony uses your prefix and suffix from PluralKit. Unlike PluralKit,"
            "system members can be pinged directly. That ping will automatically be"
            "forwarded to the main account.",
            inline=False,
        )
        embed.add_field(
            name=":pencil: `;;edit (message id) <message>`",
            value="**Edits a message**"
            "\nIf you don't include an ID, it will edit the last message sent by a system member."
            "\n[How to get a message ID]"
            "(https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-)",
            inline=False,
        )
        embed.add_field(
            name=":x: `;;del (message id)`",
            value="**Deletes a message**"
            "\nIf you don't include an ID, it will delete the last message sent by a system member."
            "\n[How to get a message ID]"
            "(https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-)",
            inline=False,
        )
        embed.add_field(
            name=":inbox_tray: `;;sync`",
            value="**Syncs information from PluralKit for all members**\n"
            "`;;sync member (member mention)` will sync changes for one specific member\n"
            "*Tip: Setting a display name in PluralKit will set a nickname that is different from the bot username*",
            inline=False,
        )
        embed.add_field(
            name=":question: `;;whoarewe`",
            value="Get a list of all the members you have registered with Polyphony",
            inline=False,
        )
        embed.add_field(
            name=":grey_question: `;;whois <Polyphony member user>`",
            value="Get information about any Polyphony member user"
            "\n*This command can be used by anyone*",
            inline=False,
        )
        embed.add_field(
            name=":bulb: `;;rolesync <Polyphony member user>`",
            value="**This enables role sync mode.** This will temporarily remove all roles from the main user and "
            "replace them with the system member's roles. Any roles you assign to yourself (the main user) will be "
            "synced with the system member. Type `done` and your main user's original roles will be restored.\n"
            "*This command will auto timeout after 5 minutes. If it times out, the changes will not be saved.*",
            inline=False,
        )
        embed.add_field(
            name=":mag: `;;slots`",
            value="Show the number of free slots available for new members to be registered with Polyphony",
            inline=False,
        )
        embed.add_field(
            name=":stopwatch: `;;ping`",
            value="Check if Polyphony, and hence Polyphony member users, is online and functioning",
            inline=False,
        )
        await ctx.channel.send(embed=embed)

    @help.command()
    @is_mod()
    async def admin(self, ctx: commands.context):
        await ctx.channel.send(
            "Ask Kiera for now. She is going to add this help menu soon."
        )

    @commands.command()
    @is_polyphony_user()
    # @commands.cooldown(1, 10)
    async def slots(self, ctx: commands.context):
        """
        Show number of slots available

        :param ctx: Discord Context
        """
        await ctx.message.delete()
        c.execute("SELECT * FROM tokens WHERE used = 0")
        slots = c.fetchall()
        if 2 > len(slots) >= 1:
            embed = discord.Embed(
                title=f"There is 1 slot available.", color=discord.Color.green()
            )
        elif len(slots) > 2:
            embed = discord.Embed(
                title=f"There are {len(slots)} slots available",
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title=f"Sorry, there are currently no slots available",
                description="Contact a moderator",
            )
        await ctx.channel.send(embed=embed)

    @commands.group()
    @is_polyphony_user()
    async def sync(self, ctx: commands.context):
        """
        Sync system members with PluralKit

        :param ctx: Discord Context
        """
        if ctx.invoked_subcommand is not None:
            return
        logger = LogMessage(ctx, title=":hourglass: Syncing All Members...")
        logger.color = discord.Color.orange()
        for instance in instances:
            if instance.main_user_account_id == ctx.author.id:
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

    @sync.command()
    @is_polyphony_user()
    async def member(self, ctx: commands.context, system_member: discord.User):
        """
        Sync system member with PluralKit

        :param system_member: User to sync
        :param ctx: Discord Context
        """
        logger = LogMessage(ctx, title=f":hourglass: Syncing {system_member}...")
        logger.color = discord.Color.orange()
        for instance in instances:
            if (
                instance.user.id == system_member.id
                and instance.main_user_account_id == ctx.author.id
            ):
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
    @is_polyphony_user()
    async def whoarewe(self, ctx: commands.context):
        """
        List members of system belonging to user who executes command

        :param ctx: Discord Context
        """
        log.debug(f"Listing members for {ctx.author.display_name}...")
        c.execute(
            "SELECT * FROM members WHERE discord_account_id == ?", [ctx.author.id],
        )
        member_list = c.fetchall()
        embed = discord.Embed(title=f"Members of System")
        embed.set_author(name=f"{ctx.author}", icon_url=ctx.author.avatar_url)

        if member_list is None:
            embed.add_field(
                name="No members where found", value="Ask a mod to add some!"
            )

        for member in member_list:
            member_user = ctx.guild.get_member_named(f"p.{member['member_name']}")
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
                value=f"""**User:** {member_user.mention}\n**PluralKit Member ID:** `{member['pk_member_id']}`\n**Tags:** {' or '.join(tags)}\n**Enabled:** `{'Yes' if member['member_enabled'] else 'No'}`""",
                inline=True,
            )

        await ctx.send(embed=embed)

    @commands.command()
    async def whois(self, ctx: commands.context, system_member: discord.Member):
        c.execute(
            "SELECT * FROM members WHERE member_account_id == ?", [system_member.id]
        )
        member = c.fetchone()
        embed = discord.Embed(
            description=f"{system_member.mention} is part of the {self.bot.get_user(member['discord_account_id']).mention} system",
        )
        embed.add_field(
            name="User ID", value=self.bot.get_user(member["member_account_id"]).id
        )
        embed.add_field(
            name="System Owner ID",
            value=self.bot.get_user(member["discord_account_id"]).id,
        )
        embed.set_thumbnail(
            url=self.bot.get_user(member["member_Account_id"]).avatar_url
        )
        await ctx.channel.send(embed=embed)

    @commands.command()
    @is_polyphony_user(allow_mods=True)
    async def ping(self, ctx: commands.context):
        """
        ping: Pings the core bot

        :param ctx: Discord Context
        """
        await ctx.send(
            embed=discord.Embed(title=f"Pong ({timedelta(seconds=self.bot.latency)})")
        )

    @commands.command()
    @is_polyphony_user()
    async def rolesync(self, ctx: commands.context, system_member: discord.Member):
        """
        Sync current roles to system member until typing `done`

        :param system_member: System member to sync roles with
        :param ctx: Discord Context
        """
        if any(
            [role.name in DISABLE_ROLESYNC_ROLES for role in ctx.message.author.roles]
        ):
            # Don't execute if has role that disables rolesync
            return
        c.execute(
            "SELECT * FROM members WHERE discord_account_id == ? AND member_account_id == ?",
            [ctx.author.id, system_member.id],
        )
        if c.fetchone():

            # Get User's Roles
            user_roles = []
            for role in ctx.author.roles[1:]:
                if role.name not in ALWAYS_SYNC_ROLES:
                    user_roles.append(role)
            # Get Member's Roles
            member_roles = []
            for role in system_member.roles[1:]:
                if role.name not in NEVER_SYNC_ROLES:
                    member_roles.append(role)

            embed = discord.Embed(
                title="Syncing roles...",
                description=f"Assign yourself the roles you want for {system_member.mention} and then type `done`",
                color=discord.Color.orange(),
            )
            saved_roles_str = " ".join([role.mention for role in ctx.author.roles[1:]])
            embed.add_field(
                name=f"`{ctx.author.display_name}`'s Roles *(saved)*",
                value=saved_roles_str
                if len(saved_roles_str) < 1024
                else "Too many to show" or "None",
            )
            embed_member_original_roles = " ".join(
                [role.mention for role in system_member.roles[1:]]
            )
            embed.add_field(
                name=f"`{system_member.display_name}`'s Original Roles",
                value=embed_member_original_roles
                if len(embed_member_original_roles)
                else "Too many to show" or "None",
            )
            embed.set_footer(
                text="Will timeout in 5 minutes. Changes may take a moment to update."
            )
            embed.set_author(
                name=system_member.display_name, icon_url=system_member.avatar_url,
            )
            instructions = await ctx.channel.send(ctx.author.mention, embed=embed)
            loading_embed = discord.Embed(
                title="*Hold on while I update your roles...*",
                color=discord.Color.orange(),
            )
            loading = await ctx.channel.send(embed=loading_embed)

            # Remove user's roles and give member's roles
            async with ctx.channel.typing():
                await ctx.author.remove_roles(*user_roles)
                await ctx.author.add_roles(*member_roles)
            loading_embed = discord.Embed(
                title="Type `done` to sync your roles.", color=discord.Color.green()
            )
            await loading.edit(embed=loading_embed)

            # Wait for "done"
            try:
                await self.bot.wait_for(
                    "message",
                    check=lambda message: message.author == ctx.author
                    and message.content.lower() == "done",
                    timeout=60 * 5,  # 5 mins
                )
                loading_embed = discord.Embed(
                    title="*Hold on while I sync and update...*",
                    color=discord.Color.orange(),
                )
                await loading.edit(embed=loading_embed)

                # On done, add new roles to member, remove new roles from user, and old roles to user
                async with ctx.channel.typing():
                    new_roles = [role for role in ctx.author.roles[1:]]

                    roles_to_remove = []
                    for role in new_roles:
                        if role.name not in ALWAYS_SYNC_ROLES:
                            roles_to_remove.append(role)

                    # Remove all roles from member and main user
                    await asyncio.gather(
                        system_member.remove_roles(*member_roles),
                        ctx.author.remove_roles(*roles_to_remove),
                    )

                    # Add new roles to member and restore user roles
                    await asyncio.gather(
                        system_member.add_roles(*new_roles),
                        ctx.author.add_roles(*user_roles),
                    )
                    embed = discord.Embed(
                        title="Role Sync Complete",
                        description=f"Finished syncing roles from {ctx.author.mention} to {system_member.mention}\n\n*{ctx.author.mention}'s original roles have been restored*",
                        color=discord.Color.green(),
                    )
                    embed.add_field(
                        name=f"`{system_member.display_name}`'s Old Roles",
                        value=embed_member_original_roles
                        if len(embed_member_original_roles) < 1024
                        else "Too many to show" or "None",
                    )
                    new_roles_str = " ".join(
                        [role.mention for role in system_member.roles[1:]]
                    )
                    embed.add_field(
                        name=f"`{system_member.display_name}`'s New Roles",
                        value=new_roles_str
                        if len(new_roles_str) < 1024
                        else "Too many to show" or "None",
                    )
                    embed.set_author(
                        name=system_member.display_name,
                        icon_url=system_member.avatar_url,
                    )
                    await instructions.edit(content="", embed=embed)
                    await loading.delete()
            except asyncio.TimeoutError:
                unsynced_roles = system_member.roles[1:]
                roles_to_remove = []
                for role in system_member.roles[1:]:
                    if role.name not in ALWAYS_SYNC_ROLES:
                        roles_to_remove.append(role)
                loading_embed = discord.Embed(
                    title="*Timed out. Hold on while I restore your roles...*",
                    color=discord.Color.orange(),
                )
                await loading.edit(embed=loading_embed)
                async with ctx.channel.typing():
                    await system_member.add_roles(*member_roles)
                    await ctx.author.remove_roles(*roles_to_remove)
                    await ctx.author.add_roles(*user_roles)
                embed = discord.Embed(
                    title="Role Sync Timed Out",
                    description=f"Restored original roles for {system_member.mention}",
                    color=discord.Color.dark_orange(),
                )
                embed.add_field(
                    name=f"`{system_member.display_name}`'s Restored Roles",
                    value=embed_member_original_roles
                    if len(embed_member_original_roles) < 1024
                    else "Too many to show" or "None",
                )
                unsynced_roles_str = " ".join([role.mention for role in unsynced_roles])
                embed.add_field(
                    name=f"`{system_member.display_name}`'s Unsaved Roles Due to Timeout",
                    value=unsynced_roles_str
                    if len(unsynced_roles_str) < 1024
                    else "Too many to show" or "None",
                )
                embed.set_footer(
                    text='Role sync times out after 5 minutes. Type "done" next time to save changes.'
                )
                embed.set_author(
                    name=system_member.display_name, icon_url=system_member.avatar_url,
                )
                await instructions.edit(content="", embed=embed)
                await loading.delete()

    @commands.command()
    @is_polyphony_user()
    async def edit(
        self,
        ctx: commands.context,
        message: Optional[discord.Message] = None,
        *,
        content: str,
    ):
        """
        edit (message id) [message]: Edits the last message or message with ID
        
        :param ctx: Discord Context
        :param message: (optional) ID of message
        :param content: Message Content
        """
        await ctx.message.delete()
        if message is not None:
            log.debug(
                f"Editing message {message.id} by {message.author} for {ctx.author}"
            )
            c.execute(
                "SELECT * FROM members WHERE discord_account_id == ? AND member_account_id == ?",
                [ctx.author.id, message.author.id],
            )
            if c.fetchone():
                for instance in instances:
                    if instance.user.id == message.author.id:
                        message = await instance.get_channel(
                            message.channel.id
                        ).fetch_message(message.id)
                        await message.edit(content=content)
                        break
        else:
            log.debug(f"Editing last Polyphony message for {ctx.author}")
            c.execute(
                "SELECT * FROM members WHERE discord_account_id == ?", [ctx.author.id],
            )
            member_ids = [member["member_account_id"] for member in c.fetchall()]
            async for message in ctx.channel.history():
                if message.author.id in member_ids:
                    for instance in instances:
                        if instance.user.id == message.author.id:
                            message = await instance.get_channel(
                                message.channel.id
                            ).fetch_message(message.id)
                            await message.edit(content=content)
                            break
                    break

    @commands.command(name="del")
    @is_polyphony_user()
    async def delete(
        self, ctx: commands.context, message: Optional[discord.Message] = None,
    ):
        """
        del (id): Deletes the last message unless a message ID parameter is provided. Can be run multiple times. n max limited by config.

        :param ctx: Discord Context
        :param message: ID of message to delete
        """
        await ctx.message.delete()
        if message is not None:
            log.debug(
                f"Deleting message {message.id} by {message.author} for {ctx.author}"
            )
            c.execute(
                "SELECT * FROM members WHERE discord_account_id == ? AND member_account_id == ?",
                [ctx.author.id, message.author.id],
            )
            if c.fetchone():
                for instance in instances:
                    if instance.user.id == message.author.id:
                        message = await instance.get_channel(
                            message.channel.id
                        ).fetch_message(message.id)
                        await message.delete()
                        break
        else:
            log.debug(f"Deleting last Polyphony message for {ctx.author}")
            c.execute(
                "SELECT * FROM members WHERE discord_account_id == ?", [ctx.author.id],
            )
            member_ids = [member["member_account_id"] for member in c.fetchall()]
            async for message in ctx.channel.history():
                if message.author.id in member_ids:
                    for instance in instances:
                        if instance.user.id == message.author.id:
                            message = await instance.get_channel(
                                message.channel.id
                            ).fetch_message(message.id)
                            await message.delete()
                            break
                    break


def setup(bot):
    log.debug("User module loaded")
    bot.add_cog(User(bot))


def teardown(bot):
    log.warning("User module unloaded")
