"""
Instances are individual bots that are created with the purpose.
"""
import asyncio
import json
import logging
import time
from datetime import timedelta

import discord
import discord.ext
import emoji

from polyphony.helpers.database import conn, c
from polyphony.helpers.log_to_channel import send_to_log_channel
from polyphony.helpers.message_cache import new_proxied_message
from polyphony.helpers.pluralkit import pk_get_member
from polyphony.settings import (
    COMMAND_PREFIX,
    DEFAULT_INSTANCE_PERMS,
    GUILD_ID,
    INSTANCE_ADD_ROLES,
    INSTANCE_REMOVE_ROLES,
)

log = logging.getLogger(__name__)


class PolyphonyInstance(discord.Client):
    """Polyphony Member Instance."""

    def __init__(
        self,
        token: str,
        pk_member_id: str,
        discord_account_id: int,
        member_name: str,
        display_name: str,
        pk_avatar_url: str,
        pk_proxy_tags: bytes,
        **options,
    ):
        """
        Creates Polyphony Member Instance

        :param token: Expecting valid token from database
        :param pk_member_id: Expecting member ID from database
        :param discord_account_id: Expecting account id from database
        :param member_name: Expecting member name from database
        :param display_name: Expecting display name from database
        :param pk_avatar_url: Expecting URL from database
        :param pk_proxy_tags: Expecting json string from database
        :param options:
        """
        super().__init__(**options)
        self.pk_member_id: str = pk_member_id
        self.main_user_account_id: int = discord_account_id
        self._token: str = token

        # Temporary for Initialization. Will be sent to API in on_ready().
        self.__member_name: str = member_name
        self.__display_name: str = display_name
        self.__pk_avatar_url: str = pk_avatar_url
        self.__pk_proxy_tags = json.loads(pk_proxy_tags)

        # Prevent message processing until ready
        self.initialized = False

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        log.info(
            f"[START] Instance started as {self.user} ({self.pk_member_id}). Initializing..."
        )

        state = await self.check_for_invalid_states()
        if state == 1:
            log.warning(
                f"Failed to start {self.user} (`{self.pk_member_id}`) because main user left. Instance has been suspended."
            )
            await self.close()
            return

        # Update Member Name
        self.member_name: str = self.__member_name
        if self.__display_name:
            self.display_name: str = self.__display_name
        else:
            self.display_name: str = self.__member_name

        # Update Username
        await self.user.edit(username=self.member_name)

        # Update Roles
        await self.update_default_roles()

        # Update Avatar
        self.pk_avatar_url: str = self.__pk_avatar_url

        # Update Proxy Tags
        self.pk_proxy_tags = self.__pk_proxy_tags

        # Update Nickname in Guilds
        await self.push_nickname_updates()

        # Update Presence
        await self.change_presence(
            activity=discord.Activity(
                name=f"{self.get_user(self.main_user_account_id)}",
                type=discord.ActivityType.listening,
            )
        )

        # Update Self ID in Database
        with conn:
            log.debug(
                f"{self.user} ({self.pk_member_id}): Updating Self Account ID: {self.user.id}"
            )
            c.execute(
                "UPDATE members SET member_account_id = ? WHERE pk_member_id = ?",
                [self.user.id, self.pk_member_id],
            )

        log.info(
            f"[COMPLETE] {self.user} ({self.pk_member_id}): Initialization complete"
        )

        self.initialized = True

    async def update(self, ctx=None):
        """
        Performs actions that require asyncio to push to Discord

        Actions:
            Update avatar
            Update nickname from display_name
        """
        log.debug(
            f"{self.user} ({self.pk_member_id}): Pushing nickname, username, and avatar"
        )

        # Update Username
        await self.user.edit(username=self.member_name)

        # Update Nickname
        await self.push_nickname_updates()

        # Update Avatar
        import requests

        try:
            await self.user.edit(avatar=requests.get(self.pk_avatar_url).content)
        except:
            if ctx is not None:
                embed = discord.Embed(
                    title="Error while updating profile picture",
                    description="You are updating your profile picture too fast. Please try again later.",
                    color=discord.Color.red(),
                )
                await ctx.channel.send(embed=embed)

    async def update_default_roles(self):
        log.debug(f"{self.user} ({self.pk_member_id}): Updating default roles")
        add_roles = []
        remove_roles = []
        for role in INSTANCE_ADD_ROLES:
            role = discord.utils.get(self.get_guild(GUILD_ID).roles, name=role)
            if role is not None:
                add_roles.append(role)
        for role in INSTANCE_REMOVE_ROLES:
            role = discord.utils.get(self.get_guild(GUILD_ID).roles, name=role)
            if role is not None:
                remove_roles.append(role)
        from polyphony.bot import bot

        if add_roles:
            await bot.get_guild(GUILD_ID).get_member(self.user.id).add_roles(*add_roles)
        if remove_roles:
            await bot.get_guild(GUILD_ID).get_member(self.user.id).remove_roles(
                *remove_roles
            )

    async def push_nickname_updates(self):
        log.debug(f"{self.user} ({self.pk_member_id}): Updating nickname in guilds")

        for guild in self.guilds:
            try:
                await guild.get_member(self.user.id).edit(nick=self.display_name)
                log.debug(
                    f"{self.user} ({self.pk_member_id}): Updated nickname to {self.display_name} on guild {guild.name}"
                )
            except AttributeError:
                log.debug(
                    f"{self.user} ({self.pk_member_id}): Failed to update nickname to {self.display_name} on guild {guild.name}"
                )
                pass

    async def sync(self, ctx=None) -> int:
        """
        Sync with PluralKit

        Return 0, success
        Return 1, not found on PluralKit (TODO: Change this to an invalid state that auto-stops the instance)
        Return 2, main user left

        :return (boolean) was successful
        """
        log.info(f"{self.user} ({self.pk_member_id}) is syncing")

        # Get PluralKit Member
        member = await pk_get_member(self.pk_member_id)

        # Detect Failure
        if member is None:
            log.warning(
                f"Failed to sync {self.user} (`{self.pk_member_id}`) because the member ID was not found on PluralKit's Servers"
            )
            return 1

        state = await self.check_for_invalid_states()
        if state == 1:
            log.warning(
                f"Failed to sync {self.user} (`{self.pk_member_id}`) because main user left. Instance has been suspended."
            )
            return 2

        # Update member name
        self.member_name = member.get("name") or self.member_name

        # Update display name (remove p. in member_name if using member_name)
        self.display_name: str = member.get("display_name") or self.member_name[2:]

        self.pk_avatar_url = member.get("avatar_url")
        self.pk_proxy_tags = member.get("proxy_tags")

        await self.update(ctx)
        log.info(f"{self.user} ({self.pk_member_id}): Sync complete")
        return 0

    async def check_for_invalid_states(self) -> int:
        log.debug(f"{self.user} ({self.pk_member_id}): Checking for invalid states...")
        await self.wait_until_ready()
        if await self.check_if_main_account_left():
            log.warning(
                f"{self.user} ({self.pk_member_id}): Main user left. Suspending self."
            )
            embed = discord.Embed(
                title="Main account left",
                description=f"Main account left for {self.user.mention}\n\n*Instance has been suspended.*",
                color=discord.Color.red(),
            )
            embed.set_footer(text=f"Main Account ID: {self.main_user_account_id}")
            await send_to_log_channel(embed=embed)
            from polyphony.helpers.instances import instances

            for i, instance in enumerate(instances):
                if instance.user.id == self.user.id:
                    await instance.close()
                    with conn:
                        c.execute(
                            "UPDATE members SET member_enabled = 0 WHERE token = ?",
                            [instance.get_token()],
                        )
                    instances.pop(i)
            return 1

        elif await self.check_if_not_in_guild():
            log.debug(f"{self.user} ({self.pk_member_id}) is not in the guild")
            from polyphony.bot import bot

            embed = discord.Embed(
                title="Member started but is not in server",
                description=f"[Invite to Server]({discord.utils.oauth_url(self.user.id, permissions=discord.Permissions(DEFAULT_INSTANCE_PERMS), guild=bot.get_guild(GUILD_ID))})",
                color=discord.Color.red(),
            )
            await send_to_log_channel(embed=embed)
            return 2
        return 0

    async def check_if_main_account_left(self) -> bool:
        log.debug(f"{self.user} ({self.pk_member_id}): Checking for account left...")
        from polyphony.bot import bot

        if self.main_user_account_id not in [
            member.id for member in bot.get_guild(GUILD_ID).members
        ]:
            log.debug(f"{self.user} ({self.pk_member_id}): Main account left")
            return True
        return False

    async def check_if_not_in_guild(self) -> bool:
        from polyphony.bot import bot

        log.debug(
            f"{self.user} ({self.pk_member_id}): Checking for self not in guild..."
        )
        if set(bot.guilds) & set(self.guilds) == set():
            log.debug(f"{self.user} ({self.pk_member_id}): Not in guild")
            return True
        log.debug(f"{self.user} ({self.pk_member_id}): Is in guild")
        return False

    @property
    def member_name(self) -> str:
        return self._member_name

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def pk_avatar_url(self) -> str:
        return self._pk_avatar_url

    @property
    def pk_proxy_tags(self) -> dict:
        if hasattr(self, "_pk_proxy_tags"):
            return self._pk_proxy_tags
        else:
            return {"prefix": "no_prefix", "suffix": "no_suffix"}

    @member_name.setter
    def member_name(self, value: str):
        log.debug(f"{self.user} ({self.pk_member_id}): Username updating to p.{value}")
        self._member_name = f"p.{value}"
        self.user.name = f"p.{value}"
        with conn:
            log.debug(f"{self.user} ({self.pk_member_id}): Updating Member Name")
            c.execute(
                "UPDATE members SET member_name = ? WHERE token = ?",
                [value, self._token],
            )

    @display_name.setter
    def display_name(self, value: str):
        """
        Requires calling the "update" method to push to Discord
        """
        self._display_name = value
        with conn:
            log.debug(f"{self.user} ({self.pk_member_id}): Updating Display Name")
            c.execute(
                "UPDATE members SET display_name = ? WHERE token = ?",
                [value, self._token],
            )
        # TODO: I think !p sync will have to actually set the nickname since that action needs context

    @pk_avatar_url.setter
    def pk_avatar_url(self, value: str):
        """
        Requires calling the "update" method to push to Discord
        """
        self._pk_avatar_url = value
        with conn:
            log.debug(
                f"{self.user} ({self.pk_member_id}): Updating avatar URL to {value}"
            )
            c.execute(
                "UPDATE members SET pk_avatar_url = ? WHERE token = ?",
                [value, self._token],
            )

    @pk_proxy_tags.setter
    def pk_proxy_tags(self, value: dict):
        self._pk_proxy_tags = value
        with conn:
            log.debug(
                f"{self.user} ({self.pk_member_id}): Updating proxy tags to {value}"
            )
            c.execute(
                "UPDATE members SET pk_proxy_tags = ? WHERE token = ?",
                [json.dumps(value), self._token],
            )

    def get_token(self):
        return self._token

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if self.main_user_account_id == after.id and before.status != after.status:
            log.debug(
                f"{self.user} ({self.pk_member_id}): Updating presence to {after.status}"
            )
            await self.change_presence(
                status=after.status,
                activity=discord.Activity(
                    name=f"{self.get_user(self.main_user_account_id)}",
                    type=discord.ActivityType.listening,
                ),
            )

    async def on_message(self, message: discord.Message):
        if self.initialized is False:
            return

        start = time.time()

        prefix_used = None
        suffix_used = None

        # Check prefix/suffix and get value
        for tag in self.pk_proxy_tags:
            if message.content.startswith(
                tag.get("prefix") or ""
            ) and message.content.endswith(tag.get("suffix") or ""):
                prefix_used = tag.get("prefix") or ""
                suffix_used = tag.get("suffix") or ""
                break

        # Check message
        if (
            prefix_used is not None
            and suffix_used is not None
            and message.author is not self.user
            and message.author.id == self.main_user_account_id
        ):
            log.debug(
                f'{self.user} ({self.pk_member_id}): Processing new message => "{message.content}" (attachments: {len(message.attachments)})'
            )

            # Remove prefix/suffix
            msg = message.content[
                len(prefix_used or "") or None : -len(suffix_used or "") or None
            ]

            # Delete and send at same time to be as fast as possible
            from polyphony.bot import bot

            await asyncio.gather(
                # Trigger typing if uploading attachment
                message.channel.trigger_typing()
                if len(message.attachments) > 0
                else asyncio.sleep(0),
                # Delete Message. Without context, it's easier to call the low-level method in discord.http.
                bot.http.delete_message(message.channel.id, message.id),
                # Send new message
                message.channel.send(
                    msg, files=[await file.to_file() for file in message.attachments],
                ),
            )

            new_proxied_message(message)

            end = time.time()
            log.debug(
                f"{self.user} ({self.pk_member_id}): Benchmark: {timedelta(seconds=end - start)} | Protocol Roundtrip: {timedelta(seconds=self.latency)}"
            )

        # Check for ping
        elif (
            self.user in message.mentions
            and message.author.id != self.main_user_account_id
            and message.author.id != self.user.id
            and not message.content.startswith(COMMAND_PREFIX)
        ):
            # Forward Ping
            log.debug(
                f"Forwarding ping from {self.user} to {self.get_user(self.main_user_account_id)}"
            )
            from polyphony.bot import bot

            embed = discord.Embed(
                description=f"Originally to {self.user.mention}\n[Highlight Message]({message.jump_url})"
            )
            embed.set_author(
                name=f"From {message.author}", icon_url=message.author.avatar_url,
            )

            await bot.get_channel(message.channel.id).send(
                f"{self.get_user(self.main_user_account_id).mention}", embed=embed,
            )

    async def on_guild_join(self, guild: discord.Guild):
        # Update Nickname on guild join
        await guild.get_member(self.user.id).edit(nick=self.display_name)

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        # Message deletes are handled by main bot to avoid permissions issues

        # Check for correct user
        if reaction.message.author == self.user and user == self.get_user(
            self.main_user_account_id
        ):

            # Delete React
            if (
                emoji.demojize(reaction.emoji) or ""
            ) == ":cross_mark:":  # Discord name: x
                from polyphony.bot import bot

                await bot.http.delete_message(
                    reaction.message.channel.id, reaction.message.id
                ),

            # Edit React
            if (
                emoji.demojize(reaction.emoji) or ""
            ) == ":memo:":  # Discord name: pencil
                from polyphony.bot import bot

                embed = discord.Embed(
                    description=f"You are now editing a [message]({reaction.message.jump_url})\nYour next message will replace it's contents.",
                    color=discord.Color.orange(),
                )
                embed.set_footer(text='Type "cancel" to cancel edit')
                instructions = await bot.get_channel(reaction.message.channel.id).send(
                    f"{user.mention}", embed=embed
                )

                try:

                    # Wait 30 seconds for new message
                    message = await self.wait_for(
                        "message",
                        check=lambda message: message.author
                        == self.get_user(self.main_user_account_id),
                        timeout=30,
                    )

                    # On new message, do all the things
                    await asyncio.gather(
                        # Delete instructions and edit message with main bot (again, low-level is easier without ctx)
                        bot.http.delete_message(
                            instructions.channel.id, instructions.id
                        ),
                        bot.http.delete_message(message.channel.id, message.id),
                        reaction.message.remove_reaction(
                            reaction.emoji, self.get_user(self.main_user_account_id)
                        ),
                        # If message isn't "cancel" then edit the message
                        reaction.message.edit(content=message.content)
                        if message.content.lower() != "cancel"
                        else asyncio.sleep(0),
                    )

                # On timeout, delete instructions and reaction
                except asyncio.TimeoutError:
                    # Delete instructions with main bot
                    await asyncio.gather(
                        bot.http.delete_message(
                            instructions.channel.id, instructions.id
                        ),
                        reaction.message.remove_reaction(
                            reaction.emoji, self.get_user(self.main_user_account_id)
                        ),
                    )
