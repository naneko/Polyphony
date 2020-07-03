"""
Instances are individual bots that are created with the purpose.
"""
import asyncio
import logging
import pickle
import time
from datetime import timedelta

import discord

from polyphony.helpers.database import conn, c
from polyphony.helpers.pluralkit import pk_get_member

log = logging.getLogger(__name__)


class PolyphonyInstance(discord.Client):
    """Polyphony Member Instance."""

    # TODO: Sync presence (status/activity) with main discord account
    # TODO: When the instance is doing anything, do "async with channel.typing()"
    # TODO: Edit/Delete Reactions

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
        self.display_name: str = self.__display_name
        self.pk_avatar_url: str = self.__pk_avatar_url
        self.pk_proxy_tags: dict = self.__pk_proxy_tags
        await self.user.edit(username=self._member_name)
        for guild in self.guilds:
            await guild.get_member(self.user.id).edit(nick=self._display_name)
        self_user = self.get_user(self._discord_account_id)
        await self.change_presence(
            activity=discord.Activity(
                name=f"{self_user.name}#{self_user.discriminator}",
                type=discord.ActivityType.listening,
            )
        )
        with conn:
            log.debug(f"{self._pk_member_id}: Updating Display Name")
            c.execute(
                "UPDATE members SET member_account_id = ? WHERE token = ?",
                [self.user.id, self._token],
            )
        log.debug(f"{self.user} ({self._pk_member_id}): Initialization complete")

    async def update(self, ctx=None):
        """
        Performs actions that require asyncio to push to Discord

        Actions:
            Update avatar
            Update nickname from display_name
        """
        log.debug(
            f"{self.user} ({self._pk_member_id}): Pushing nickname, username, and avatar"
        )
        await self.user.edit(username=self.member_name)
        for guild in self.guilds:
            await guild.get_member(self.user.id).edit(nick=self.display_name)
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

    async def sync(self, ctx=None):
        """
        Sync with PluralKit
        """
        log.info(f"{self.user} ({self._pk_member_id}) is syncing")
        member = await pk_get_member(self._pk_member_id)
        self.member_name = member["name"]
        self.display_name = member["display_name"]
        self.pk_avatar_url = member["avatar_url"]
        self.pk_proxy_tags = member["proxy_tags"][0]
        await self.update(ctx)
        log.info(f"{self.user} ({self._pk_member_id}): Sync complete")

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
        log.debug(f"{self.user} ({self._pk_member_id}): Username updating to p.{value}")
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

    async def on_message(self, message):
        start = time.time()
        if (
            message.content.startswith(self.pk_proxy_tags.get("prefix") or "")
            and message.content.endswith(self.pk_proxy_tags.get("suffix") or "")
            and message.author is not self.user
            and message.author.id == self._discord_account_id
        ):
            log.debug(
                f'{self.user} ({self._pk_member_id}): Processing new message => "{message.content}"'
            )
            msg = message.content[
                len(self.pk_proxy_tags.get("prefix") or "")
                or None : -len(self.pk_proxy_tags.get("suffix") or "")
                or None
            ]
            await asyncio.gather(
                message.delete(), message.channel.send(msg)
            )  # Do both at the same time to be as fast as possible
            end = time.time()
            log.debug(
                f"{self.user} ({self._pk_member_id}): Benchmark: {timedelta(seconds=end - start)} | Protocol Roundtrip: {timedelta(seconds=self.latency)}"
            )

    async def on_guild_join(self, guild: discord.Guild):
        await guild.get_member(self.user.id).edit(nick=self._display_name)
