"""
Instances are individual bots that are created with the purpose.
"""
import asyncio
import logging
import pickle

import discord

from polyphony.helpers.database import conn, c

log = logging.getLogger(__name__)


class PolyphonyInstance(discord.Client):
    """Polyphony Member Instance."""

    # TODO: Allow status to be set
    # TODO: Sync presence (status/activity) with main discord account
    # TODO: When the instance is doing anything, do "async with channel.typing()"

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
        :param pk_proxy_tags: Expecting pickled value from database
        :param options:
        """
        super().__init__(**options)
        self._token: str = token
        self._pk_member_id: str = pk_member_id
        self._discord_account_id: int = discord_account_id
        self.__member_name: str = member_name
        self.__display_name: str = display_name
        self.__pk_avatar_url: str = pk_avatar_url
        self.__pk_proxy_tags: dict = pickle.loads(pk_proxy_tags)

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        log.info(
            f"Instance started as {self.user} ({self._pk_member_id}). Initializing..."
        )
        self.member_name: str = self.__member_name
        await asyncio.sleep(1)
        self.display_name: str = self.__display_name
        await asyncio.sleep(1)
        self.pk_avatar_url: str = self.__pk_avatar_url
        await asyncio.sleep(1)
        self.pk_proxy_tags: dict = self.__pk_proxy_tags
        for guild in self.guilds:
            await asyncio.sleep(1)
            await guild.get_member(self.user.id).edit(nick=self._display_name)
        await asyncio.sleep(1)
        self_user = self.get_user(self._discord_account_id)
        await self.change_presence(
            activity=discord.Activity(
                name=f"{self_user.name}#{self_user.discriminator}",
                type=discord.ActivityType.listening,
            )
        )
        log.debug(f"{self.user} ({self._pk_member_id}): Initialization complete")

    async def update(self):
        """
        Performs actions that require asyncio to push to Discord

        Actions:
            Update avatar
            Update nickname from display_name
        """
        for guild in self.guilds:
            await guild.get_member(self.user.id).edit(nick=self._display_name)
        import requests

        await self.user.edit(avatar=requests.get(self.pk_avatar_url).content)

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
        return self._pk_proxy_tags

    @member_name.setter
    def member_name(self, value: str):
        log.debug(
            f"{self.user} ({self._pk_member_id}): Username updating to p.{value}"
        )
        self._member_name = f"p.{value}"
        self.user.name = f"p.{value}"
        with conn:
            log.debug(f"{self.user} ({self._pk_member_id}): Updating Member Name")
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
        log.warning(
            f"{self.user} ({self._pk_member_id}): Display name updated to {value} in instance but this feature is not implemented"
        )
        with conn:
            log.debug(f"{self._pk_member_id}: Updating Display Name")
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
                f"{self.user} ({self._pk_member_id}): Updating avatar URL to {value}"
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
                f"{self.user} ({self._pk_member_id}): Updating proxy tags to {value}"
            )
            c.execute(
                "UPDATE members SET pk_proxy_tags = ? WHERE token = ?",
                [pickle.dumps(value), self._token],
            )
        log.warning(
            f"{self.user} ({self._pk_member_id}): Proxy tags updated to {value} in instance but this feature is not implemented"
        )
        # TODO: Update listener if needed

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if self._discord_account_id == after.id and before.status != after.status:
            log.debug(
                f"{self.user} ({self._pk_member_id}): Updating presence to {after.status}"
            )
            self_user = self.get_user(self._discord_account_id)
            await self.change_presence(
                status=after.status,
                activity=discord.Activity(
                    name=f"{self_user.name}#{self_user.discriminator}",
                    type=discord.ActivityType.listening,
                ),
            )

    async def on_guild_join(self, guild: discord.Guild):
        await guild.get_member(self.user.id).edit(nick=self._display_name)
