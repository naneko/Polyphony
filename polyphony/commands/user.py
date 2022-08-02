"""
User commands to configure Polyphony
"""
import asyncio
import logging
from typing import Optional, Union

import discord
from discord.ext import commands

from polyphony.bot import helper
from polyphony.helpers.checks import is_polyphony_user, is_mod
from polyphony.helpers.database import c, conn
from polyphony.helpers.member_list import send_member_list
from polyphony.helpers.reset import reset
from polyphony.helpers.sync import sync
from polyphony.instance.bot import PolyphonyInstance
from polyphony.settings import (
    NEVER_SYNC_ROLES,
    ALWAYS_SYNC_ROLES,
    DISABLE_ROLESYNC_ROLES,
)

log = logging.getLogger("polyphony." + __name__)

# TODO: Add more delete_after cleaning


class User(commands.Cog):
    def __init__(self, bot: discord.ext.commands.bot):
        self.bot = bot

    @commands.group()
    @commands.check_any(is_mod(), is_polyphony_user(), commands.is_owner())
    async def help(self, ctx: commands.context):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(
                title="Polyphony Quick Start",
                name="Polyphony is an extension of PluralKit that allows more control for everyone.",
            )
            embed.add_field(
                name=":pencil: __Editing and deleting messages__",
                value="> **__Editing__**"
                "\n> **- Method 1:** React with :pencil: to the message and then type your edit"
                "\n> **- Method 2:** Type `;;edit <message>` to edit last message sent by a system member"
                "\n> **- Method 3:** Type `;;edit (message id) <message> ` to edit a message by it's id"
                "\n\n> **__Deleting__**"
                "\n> **- Method 1:** React with :x: on the message"
                "\n> **- Method 2:** Type `;;del` to delete the last message sent by a system member"
                "\n> **- Method 3:** Type `;;del` to delete a message by id"
                "\n\n> [How to get the ID]"
                "(https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-)"
                "\n> *Method 1 may not work on older messages*",
                inline=False,
            )
            embed.add_field(
                name=":inbox_tray: __Syncing from PluralKit__",
                value="> `;;sync` will sync changes for all your members\n"
                "> `;;sync member (member mention)` will sync changes for one specific member",
                inline=False,
            )
            embed.add_field(
                name=":information_source: __More Help__",
                value="> `;;help user` to get the full command list for Polyphony users"
                "\n> `;;help admin` to get the full command list for Moderators *(Moderators Only)*",
            )
            await ctx.channel.send(embed=embed)

    @help.command()
    async def user(self, ctx: commands.context):
        embed = discord.Embed(
            title="Polyphony User Help",
            description="Polyphony uses your prefix and suffix from PluralKit. Unlike PluralKit, "
            "system members can be pinged directly. That ping will automatically be"
            "forwarded to the main account.",
            inline=False,
        )
        embed.add_field(
            name=":pencil: `;;edit (message id) <message>`",
            value="> **Edits a message**"
            "\n> If you don't include an ID, it will edit the last message sent by a system member."
            "\n> [How to get a message ID]"
            "(https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-)",
            inline=False,
        )
        embed.add_field(
            name=":x: `;;del (message id)`",
            value="> **Deletes a message**"
            "\n> If you don't include an ID, it will delete the last message sent by a system member."
            "\n> [How to get a message ID]"
            "(https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-)",
            inline=False,
        )
        embed.add_field(
            name=":speech_balloon: `;;autoproxy <latch / Polyphony member user>`",
            value="> **Automatically proxies members without needing a tag**"
            "\n> `;;autoproxy <Polyphony member user>` will autoproxy a specific member unless you use the tags of a different member"
            "\n> `;;autoproxy latch` will remember the last tag you used and autoproxy that member until you use a different tag"
            "\n> *This is essentially the same as [PluralKit's autoproxy](https://pluralkit.me/guide/#proxying). You can also use `;;ap`.*",
        )
        embed.add_field(
            name=":inbox_tray: `;;sync`",
            value="> **Syncs information from PluralKit for all members**\n"
            "> `;;sync member (member mention)` will sync changes for one specific member",
            inline=False,
        )
        embed.add_field(
            name=":id: `;;nick <member> (nickname)`",
            value="> **Set the nickname of a system member.**\n"
            "> If you want to reset it to the name you have defined in PluralKit, just leave the `nickname` parameter empty",
            inline=False,
        )
        embed.add_field(
            name=":question: `;;whoarewe`",
            value="> Get a list of all the members you have registered with Polyphony",
            inline=False,
        )
        embed.add_field(
            name=":grey_question: `;;whois <Polyphony member user>`",
            value="> Get information about any Polyphony member user"
            "\n> *This command can be used by anyone*",
            inline=False,
        )
        embed.add_field(
            name=":bulb: `;;rolesync <Polyphony member user>`",
            value="> **This enables role sync mode.**\n"
            "> **Step 1** Use the command\n"
            "> **Step 2** Assign the roles you want for that system member to yourself\n"
            "> **Step 3** Type `done`"
            "> *This command will auto timeout after 5 minutes. If it times out, the changes will not be saved.*",
            inline=False,
        )
        embed.add_field(
            name=":mag: `;;slots`",
            value="> Show the number of free slots available for new members to be registered with Polyphony",
            inline=False,
        )
        embed.add_field(
            name=":stopwatch: `;;ping`",
            value="> Check if Polyphony, and hence Polyphony member users, is online and functioning",
            inline=False,
        )
        await ctx.channel.send(embed=embed)

    @help.command()
    @commands.check_any(is_mod(), commands.is_owner())
    async def admin(self, ctx: commands.context):
        embed = discord.Embed(
            title="Polyphony Admin Help",
            inline=False,
        )
        embed.add_field(
            name=":hamburger: `;;list`",
            value="> `;;list` lists all enabled members\n"
            "> `;;list all` lists all members registered with Polyphony\n"
            "> `;;list system <system owner>` lists all members in a system\n"
            "> `;;list suspended` lists all suspended members",
            inline=False,
        )
        embed.add_field(
            name=":scroll: `;;register <PluralKit member ID> <Main Account>`",
            value="> Ask members to give you the 5-letter PluralKit member IDs that are listed with pk;list (not system ID!)\n"
            "> The `Main Account` is **__NOT__** a bot account. It is the Discord user.\n"
            "> *You will be prompted with a confirmation dialog before the member is added. This will give you a chance to check for mistakes.*",
            inline=False,
        )
        embed.add_field(
            name=":inbox_tray: `;;syncall`",
            value="> **Syncs information from PluralKit for all members**\n"
            "> `;;syncall system <main account>` will sync the users for a specific system\n"
            "> `;;syncall member <system member>` will sync a specific system member"
            "> *Will also check for system members belonging to main accounts who have left the server and automatically suspend them*",
            inline=False,
        )
        embed.add_field(
            name=":mailbox_with_mail: `;;invite <client id/user id/user mention>`",
            value="> Creates an invite link for the instance bot ~~(or any other bot)~~",
            inline=False,
        )
        embed.add_field(
            name=":red_circle: `;;suspend <Polyphony member user>`",
            value="> Suspends a member instance, sending it offline.\n"
            "> *Can help save on resources.*",
            inline=False,
        )
        embed.add_field(
            name=":green_circle: `;;start <Polyphony member user>`",
            value="> Starts a member instance if it's suspended, bringing it online.",
            inline=False,
        )
        embed.add_field(
            name=":no_entry_sign: `;;disable <Polyphony member user>`",
            value="> **Permanently disables a member instance**\n"
            "> This will delete the instance from the Polyphony system. Because message history is not removed, bot users (tokens) cannot be reused after being disabled.\n"
            "> *If you do want to reuse a bot for some reason, reset the token in the Discord developer portal and add it with `;;tokens`*\n"
            "> *Due to the destructive nature of this command, a confirmation dialog will be shown before disabling to check for mistakes*",
            inline=False,
        )
        embed.add_field(
            name=":floppy_disk: `;;tokens`",
            value="> Add additional bot tokens to the queue to be used with `;;register`\n"
            "> **Make sure DMs are __ON__ for the server**\n"
            "> Run on the server WITHOUT any arguments. You will receive further instructions in a DM.\n"
            "> __Never paste tokens into the server__",
            inline=False,
        )
        embed.add_field(
            name=":arrows_counterclockwise: `;;tokenup`",
            value="> Update a bot token for a specific system member. Can be used if Discord resets a token.\n"
            "> **Make sure DMs are __ON__ for the server**\n"
                  "> Run on the server WITHOUT any arguments. You will receive further instructions in a DM.\n"
                  "> __Never paste tokens into the server__",
            inline=False,
        )
        embed.add_field(
            name=":grey_question: `;;whois <Polyphony member user>`",
            value="> Get information about any Polyphony member user"
            "\n> *This command can be used by anyone*",
            inline=False,
        )
        embed.add_field(
            name=":mag: `;;slots`",
            value="> Show the number of free slots available for new members to be registered with Polyphony",
            inline=False,
        )
        embed.add_field(
            name=":stopwatch: `;;ping`",
            value="> Check if Polyphony, and hence Polyphony member users, is online and functioning",
            inline=False,
        )
        await ctx.channel.send(embed=embed)

    @commands.command()
    @commands.check_any(is_mod(), is_polyphony_user(), commands.is_owner())
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
        elif len(slots) > 1:
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
        await sync(
            ctx,
            conn.execute(
                "SELECT * FROM members WHERE main_account_id = ?", [ctx.author.id]
            ).fetchall(),
        )

    @sync.command()
    @is_polyphony_user()
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
    @is_polyphony_user()
    async def whoarewe(self, ctx: commands.context):
        """
        List members of system belonging to user who executes command

        :param ctx: Discord Context
        """
        log.debug(f"Listing members for {ctx.author.display_name}...")
        c.execute(
            "SELECT * FROM members WHERE main_account_id == ?",
            [ctx.author.id],
        )
        member_list = c.fetchall()
        embed = discord.Embed(title=f"Members of System")
        embed.set_author(name=f"{ctx.author}", icon_url=ctx.author.avatar_url)
        await send_member_list(ctx, embed, member_list, whoarewe=True)

    @commands.command()
    async def whois(self, ctx: commands.context, system_member: discord.Member):
        c.execute("SELECT * FROM members WHERE id == ?", [system_member.id])
        member = c.fetchone()
        try:
            embed = discord.Embed(
                description=f"{system_member.mention} is part of the {self.bot.get_user(member['main_account_id']).mention} system",
            )
        except AttributeError:
            embed = discord.Embed(
                description=f":x: It appears the user for {system_member.mention} has left the server.",
            )
        embed.add_field(name="User ID", value=member["id"])
        embed.add_field(
            name="System Owner ID",
            value=member["main_account_id"],
        )
        embed.set_thumbnail(url=self.bot.get_user(member["id"]).avatar_url)
        await ctx.channel.send(embed=embed)

    @commands.command()
    @is_polyphony_user()
    async def nick(
        self, ctx: commands.context, ctx_member: discord.Member, *, nickname: str = ""
    ):
        member = conn.execute(
            "SELECT * FROM members WHERE main_account_id == ? AND id == ?",
            [ctx.author.id, ctx_member.id],
        ).fetchone()
        if member is not None:
            with ctx.channel.typing():
                embed = discord.Embed(
                    description=f":hourglass: {'Updating' if nickname != '' else 'Clearing'} nickname for {ctx_member.mention}...",
                    color=discord.Color.orange(),
                )
                embed.set_author(
                    name=ctx_member.display_name, icon_url=ctx_member.avatar_url
                )
                status_msg = await ctx.channel.send(embed=embed)

                # Create instance
                instance = PolyphonyInstance(member["pk_member_id"])
                asyncio.run_coroutine_threadsafe(
                    instance.start(member["token"]), self.bot.loop
                )
                await instance.wait_until_ready()

                out = await instance.update_nickname(nickname)

                await instance.close()

                if out < 0:
                    embed = discord.Embed(
                        title=f":x: **Could not update nickname**\n",
                        description=f":warning: Nickname `{(nickname[:42] + '...') if len(nickname or '') > 42 else nickname}` is too long",
                        color=discord.Color.red(),
                    )
                    embed.set_author(
                        name=ctx_member.display_name, icon_url=ctx_member.avatar_url
                    )
                    embed.set_footer(text="Nicknames must be 32 characters or less")
                else:
                    embed = discord.Embed(
                        description=f":white_check_mark: Nickname {'updated' if nickname != '' else 'cleared'} for {ctx_member.mention}",
                        color=discord.Color.green(),
                    )
                    embed.set_author(
                        name=ctx_member.display_name, icon_url=ctx_member.avatar_url
                    )
                    if out > 0:
                        embed.set_footer(
                            text="With errors: did not update in all guilds"
                        )

                await status_msg.edit(embed=embed)

    @commands.command()
    @commands.check_any(is_mod(), is_polyphony_user(), commands.is_owner())
    async def ping(self, ctx: commands.context):
        """
        ping: Pings the core bot

        :param ctx: Discord Context
        """
        await ctx.message.delete()
        await ctx.send(
            embed=discord.Embed(title=f"Pong").set_footer(
                text=f"{self.bot.latency:.3g}s"
            ),
            delete_after=10,
        )

    @commands.command(aliases=["ap"])
    @is_polyphony_user()
    async def autoproxy(self, ctx: commands.context, arg: Union[discord.Member, str]):
        await ctx.message.delete()
        embed = None
        if (
            type(arg) is discord.Member
            and conn.execute(
                "SELECT * FROM members WHERE main_account_id == ? AND id == ?",
                [ctx.author.id, arg.id],
            ).fetchone()
            is not None
        ):
            conn.execute(
                "UPDATE users SET autoproxy_mode = 'member', autoproxy = ? WHERE id == ?",
                [arg.id, ctx.author.id],
            )
            conn.commit()
            embed = discord.Embed(description=f"Autoproxy set to {arg.mention}")
            embed.set_footer(text="Use ;;ap off to turn autoproxy off")
        elif arg == "latch":
            conn.execute(
                "UPDATE users SET autoproxy_mode = 'latch', autoproxy = NULL WHERE id == ?",
                [ctx.author.id],
            )
            conn.commit()
            embed = discord.Embed(description=f"Autoproxy set to **latch mode**")
            embed.set_footer(text="Use ;;ap off to turn autoproxy off")
        elif arg == "off":
            conn.execute(
                "UPDATE users SET autoproxy_mode = NULL WHERE id == ?",
                [ctx.author.id],
            )
            conn.commit()
            embed = discord.Embed(description=f"Autoproxy is now **off**")
        if embed is None and type(arg) is discord.Member:
            embed = discord.Embed(
                description=f"{arg.mention} is not a member of your system",
                color=discord.Color.red(),
            )
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed, delete_after=10)

    @commands.command()
    @is_polyphony_user()
    # TODO make more efficient
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
            "SELECT * FROM members WHERE main_account_id == ? AND id == ?",
            [ctx.author.id, system_member.id],
        )
        if c.fetchone():

            # Get User's Roles
            user_roles = []
            for role in ctx.author.roles[1:]:
                if role.name not in ALWAYS_SYNC_ROLES and not role.managed:
                    user_roles.append(role)
            # Get Member's Roles
            member_roles = []
            for role in system_member.roles[1:]:
                if role.name not in NEVER_SYNC_ROLES:
                    member_roles.append(role)

            embed = discord.Embed(
                title=":hourglass: Syncing roles...",
                description=f"Assign yourself the roles you want for {system_member.mention} and then type `done`",
                color=discord.Color.orange(),
            )
            saved_roles_str = " ".join([role.mention for role in ctx.author.roles[1:]])
            embed.add_field(
                name=f":file_folder: __{ctx.author.display_name}__'s Roles *(saved)*",
                value=saved_roles_str
                if len(saved_roles_str) < 1024
                else ":hushed: Too many to show" or "None",
            )
            embed_member_original_roles = " ".join(
                [role.mention for role in system_member.roles[1:]]
            )
            embed.add_field(
                name=f"__{system_member.display_name}__'s Original Roles",
                value=embed_member_original_roles
                if len(embed_member_original_roles)
                else ":hushed: Too many to show" or "None",
            )
            embed.set_footer(
                text="Will timeout in 5 minutes. Changes may take a moment to update."
            )
            embed.set_author(
                name=system_member.display_name,
                icon_url=system_member.avatar_url,
            )
            instructions = await ctx.channel.send(ctx.author.mention, embed=embed)
            loading_embed = discord.Embed(
                title=":hourglass: *Hold on while I update your roles...*",
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
                    title=":hourglass: *Hold on while I sync and update...*",
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
                        title=":white_check_mark: Role Sync Complete",
                        description=f"Finished syncing roles from {ctx.author.mention} to {system_member.mention}\n{ctx.author.mention}'s original roles have been restored",
                        color=discord.Color.green(),
                    )
                    embed.add_field(
                        name=f"__{system_member.display_name}__'s Old Roles",
                        value=embed_member_original_roles
                        if len(embed_member_original_roles) < 1024
                        else ":hushed: Too many to show" or "None",
                    )
                    new_roles_str = " ".join(
                        [role.mention for role in system_member.roles[1:]]
                    )
                    embed.add_field(
                        name=f"__{system_member.display_name}__'s New Roles",
                        value=new_roles_str
                        if len(new_roles_str) < 1024
                        else ":hushed: Too many to show" or "None",
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
                    else ":hushed: Too many to show" or "None",
                )
                unsynced_roles_str = " ".join([role.mention for role in unsynced_roles])
                embed.add_field(
                    name=f"`{system_member.display_name}`'s Unsaved Roles Due to Timeout",
                    value=unsynced_roles_str
                    if len(unsynced_roles_str) < 1024
                    else ":hushed: Too many to show" or "None",
                )
                embed.set_footer(
                    text='Role sync times out after 5 minutes. Type "done" next time to save changes.'
                )
                embed.set_author(
                    name=system_member.display_name,
                    icon_url=system_member.avatar_url,
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
            member = conn.execute(
                "SELECT * FROM members WHERE main_account_id == ? AND id == ? AND member_enabled = 1",
                [ctx.author.id, message.author.id],
            ).fetchone()
            if member:
                log.debug(
                    f"Editing message {message.id} by {message.author} for {ctx.author}"
                )
                while await helper.edit_as(
                    message,
                    content,
                    member["token"],
                ) is False:
                    await reset()
        else:
            log.debug(f"Editing last Polyphony message for {ctx.author}")
            member_ids = [
                member["id"]
                for member in conn.execute(
                    "SELECT * FROM members WHERE main_account_id == ?",
                    [ctx.author.id],
                ).fetchall()
            ]
            async for message in ctx.channel.history():
                if message.author.id in member_ids:
                    while await helper.edit_as(
                        message,
                        content,
                        conn.execute(
                            "SELECT * FROM members WHERE id == ?",
                            [message.author.id],
                        ).fetchone()["token"],
                    ) is False:
                        await reset()
                    break

    @commands.command(name="del")
    @is_polyphony_user()
    async def delete(
        self,
        ctx: commands.context,
        message: Optional[discord.Message] = None,
    ):
        """
        del (id): Deletes the last message unless a message ID parameter is provided. Can be run multiple times. n max limited by config.

        :param ctx: Discord Context
        :param message: ID of message to delete
        """
        await ctx.message.delete()
        if message is not None:
            member = conn.execute(
                "SELECT * FROM members WHERE main_account_id == ? AND id == ? AND member_enabled = 1",
                [ctx.author.id, message.author.id],
            ).fetchone()
            if member:
                log.debug(
                    f"Deleting message {message.id} by {message.author} for {ctx.author}"
                )
                message = await self.bot.get_channel(message.channel.id).fetch_message(
                    message.id
                )
                await message.delete()
        else:
            log.debug(f"Deleting last Polyphony message for {ctx.author}")
            member_ids = [
                member["id"]
                for member in conn.execute(
                    "SELECT * FROM members WHERE main_account_id == ?",
                    [ctx.author.id],
                ).fetchall()
            ]
            async for message in ctx.channel.history():
                if message.author.id in member_ids:
                    await message.delete()
                    break


def setup(bot):
    log.debug("User module loaded")
    bot.add_cog(User(bot))


def teardown(bot):
    log.debug("User module unloaded")
