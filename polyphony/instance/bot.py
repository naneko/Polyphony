"""
Instances are individual bots that are created with the purpose.
"""
import json
import logging

import discord
import discord.ext

from polyphony.helpers.database import conn, c
from polyphony.helpers.log_to_channel import send_to_log_channel
from polyphony.helpers.pluralkit import pk_get_member
from polyphony.settings import (
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
        nickname: str,
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
        self.member_name: str = member_name
        self.display_name: str = display_name
        self.pk_avatar_url: str = pk_avatar_url
        self.pk_proxy_tags = json.loads(pk_proxy_tags)
        self.nickname: str = nickname

        # Main User Account
        self.main_user = None

        log.debug(f"[INITIALIZED] {self.member_name} ({self.pk_member_id})")

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        log.debug(f"[STARTUP]     {self.user} ({self.pk_member_id})")
        # TODO: Fix
        # state = await self.check_for_invalid_states()
        # if state == 1:
        #     log.warning(
        #         f"Failed to start {self.user} ({self.pk_member_id}) because main user left. Instance has been suspended."
        #     )
        #     await self.close()
        #     return

        # Update Self ID in Database
        with conn:
            log.debug(
                f"{self.user} ({self.pk_member_id}): Updating Self Account ID: {self.user.id}"
            )
            c.execute(
                "UPDATE members SET member_account_id = ? WHERE pk_member_id = ?",
                [self.user.id, self.pk_member_id],
            )

        self.main_user = self.get_user(self.main_user_account_id)

        log.info(f"[READY]        {self.user} ({self.pk_member_id})")

    async def on_disconnect(self):
        log.info(f"[DISCONNECTED] {self.user} ({self.pk_member_id})")

    async def on_resumed(self):
        log.info(f"[RESUMED]      {self.user} ({self.pk_member_id})")

    async def on_error(self, event_method, *args, **kwargs):
        log.error(f"{self.user} ({self.pk_member_id}): {event_method}")

    async def on_guild_join(self, guild: discord.Guild):
        # Update Nickname on guild join
        await guild.get_member(self.user.id).edit(
            nick=self.nickname or self.display_name
        )

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
        try:
            await self.user.edit(username=self.member_name)
        except discord.HTTPException:
            log.debug(
                f"{self.user} ({self.pk_member_id}): Username Update Failed. Probably being updated too frequently."
            )
            if ctx is not None:
                embed = discord.Embed(
                    title="Error while updating username",
                    description="You are updating your username too fast. Please try again later.",
                    color=discord.Color.red(),
                )
                await ctx.channel.send(embed=embed)

        # Update Nickname
        await self.push_nickname_updates()

        # Update Avatar
        import requests

        try:
            log.debug(f"{self.user} ({self.pk_member_id}): Getting Avatar")
            avatar = requests.get(self.pk_avatar_url).content
            log.debug(f"{self.user} ({self.pk_member_id}): Updating Avatar")
            await self.user.edit(avatar=avatar)
        except discord.HTTPException:
            log.debug(
                f"{self.user} ({self.pk_member_id}): Avatar Update Failed. Probably being updated too frequently."
            )
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
                await guild.get_member(self.user.id).edit(
                    nick=self.nickname or self.display_name
                )
                log.debug(
                    f"{self.user} ({self.pk_member_id}): Updated nickname to {self.nickname or self.display_name} on guild {guild.name}"
                )
            except AttributeError:
                log.debug(
                    f"{self.user} ({self.pk_member_id}): Failed to update nickname to {self.nickname or self.display_name} on guild {guild.name}"
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

        await self.wait_until_ready()

        # Get PluralKit Member
        member = await pk_get_member(self.pk_member_id)

        await self.update_default_roles()

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

        self.pk_avatar_url = member.get("avatar_url") or self.pk_avatar_url
        self.pk_proxy_tags = member.get("proxy_tags") or self.pk_proxy_tags

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

            # TODO: Change instance array to be dict instead to allow direct access instead of iterative access
            for i, instance in enumerate(instances):
                if instance.user.id == self.user.id:
                    await instance.change_presence(
                        status=discord.Status.offline, activity=None
                    )
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

        if bot.get_guild(GUILD_ID).get_member(self.main_user_account_id) is None:
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

    @property
    def nickname(self) -> str:
        return self._nickname

    @member_name.setter
    def member_name(self, value: str):
        log.debug(f"{self.user} ({self.pk_member_id}): Username updating to p.{value}")
        self._member_name = f"p.{value}"
        if self.is_ready():
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

    @nickname.setter
    def nickname(self, value: str):
        self._nickname = value
        log.debug(f"{self.user} ({self.pk_member_id}): Updating nickname to {value}")
        conn.execute(
            "UPDATE members SET nickname = ? WHERE token = ?", [value, self._token]
        )
        conn.commit()

    def get_token(self):
        return self._token
