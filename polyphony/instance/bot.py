"""
Instances are individual bots that are created with the purpose.
"""
import io
import urllib

import discord
import logging

log = logging.getLogger(__name__)


class PolyphonyInstance(discord.Client):
    """Polyphony Member Instance."""

    # TODO: Allow status to be set
    # TODO: Sync presence (status/activity) with main discord account
    # TODO: When the instance is doing anything, do "async with channel.typing()"

    def __init__(
        self,
        pk_member_id: str,
        discord_account_id: int,
        member_name: str,
        display_name: str,
        pk_avatar_url: str,
        pk_proxy_tags: dict,
        **options,
    ):
        super().__init__(**options)
        self._pk_member_id: str = pk_member_id
        self._discord_account_id: int = discord_account_id
        self.member_name: str = member_name
        self.display_name: str = display_name
        self.pk_avatar_url: str = pk_avatar_url
        self.pk_proxy_tags: dict = pk_proxy_tags

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        log.info(f"Instance started as {self.user}")

    @property
    def member_name(self) -> str:
        return self.member_name

    @property
    def display_name(self) -> str:
        return self.display_name

    @property
    def pk_avatar_url(self) -> str:
        return self.pk_avatar_url

    @property
    def pk_proxy_tags(self) -> dict:
        return self.pk_proxy_tags

    @member_name.setter
    def member_name(self, value: str):
        log.debug(f"{self.user} | Username updating to {value}")
        self._member_name = value
        self.user.edit(username=self._member_name)

    @display_name.setter
    def display_name(self, value: str):
        self._display_name = value
        log.warning(
            f"{self.user} | Display name updated to {value} in instance but this feature is not implemented"
        )
        # TODO: I think !p sync will have to actually set the nickname since that action needs context
        # self.user.display_name = value

    @pk_avatar_url.setter
    def pk_avatar_url(self, value: str):
        try:
            avatar = urllib.request.urlopen(value)
            self.user.edit(avatar=io.BytesIO(avatar.read()))
            self._pk_avatar_url = value
            log.debug(f"{self.user} | Avatar updated to {value}")
        except:
            log.warning(f"{self.user} | Unable to update avatar")

    @pk_proxy_tags.setter
    def pk_proxy_tags(self, value: dict):
        self._pk_proxy_tags = value
        log.warning(
            f"{self.user} | Proxy tags updated to {value} in instance but this feature is not implemented"
        )
        # TODO: Update listener if needed
