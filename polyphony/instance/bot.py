"""
Instances are individual bots that are created with the purpose.
"""
import asyncio
import logging
from io import BytesIO

import discord
import discord.ext
# import imagehash
# from PIL import Image, UnidentifiedImageError

from polyphony.helpers.database import conn
from polyphony.settings import (
    GUILD_ID,
    INSTANCE_ADD_ROLES,
    INSTANCE_REMOVE_ROLES,
)

log = logging.getLogger(__name__)


class PolyphonyInstance(discord.Client):
    """Polyphony Member Instance."""

    def __init__(
        self,
        pk_member_id: str,
        **options,
    ):
        """
        Creates Polyphony Member Instance

        :param pk_member_id: Expecting member ID from database
        :param options:
        """
        super().__init__(**options)

        self.pk_member_id: str = pk_member_id
        log.debug(f"[INITIALIZED] ({self.pk_member_id})")

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        log.debug(f"[STARTUP] {self.user} ({self.pk_member_id})")

        await self.change_presence(status=discord.Status.invisible)

        log.debug(f"[READY] {self.user} ({self.pk_member_id})")

    async def on_disconnect(self):
        log.debug(f"[DISCONNECTED] {self.user} ({self.pk_member_id})")

    async def update_username(self, name):
        await self.wait_until_ready()
        log.debug(f"{self.user} ({self.pk_member_id}): Updating username")
        if len(name or "") > 32:
            return "Username must be 32 characters or less"
        try:
            await self.user.edit(username=f"p.{name}")
            return 0
        except discord.HTTPException as e:
            log.info(
                f"{self.user} ({self.pk_member_id}): Username Update Failed.\n {e.text}"
            )
            if "too fast" in e.text.lower():
                return "Username is being updated too frequently"
            elif "too many" in e.text.lower():
                await self.update_username(f"{name}_")
                return (
                    f"Too many people had the username `{name}`: appended underscore(s)"
                )
            else:
                return "An unknown error occurred while updating username"

    async def update_avatar(self, url, no_timeout=False):
        await self.wait_until_ready()
        import requests

        try:
            # log.debug(f"{self.user} ({self.pk_member_id}): Getting Old and New Avatars")
            avatar = requests.get(url).content

            if no_timeout:
                await asyncio.wait_for(self.user.edit(avatar=avatar), 300)
                pass
            else:
                await asyncio.wait_for(self.user.edit(avatar=avatar), 10)
            return 0

            # old_avatar = requests.get(self.user.avatar_url).content

            # cutoff = 5

            # try:
            #     log.debug(f"{self.user} ({self.pk_member_id}): Comparing Avatar")
            #     hash_avatar = imagehash.average_hash(Image.open(BytesIO(avatar)))
            #     hash_old_avatar = imagehash.average_hash(
            #         Image.open(BytesIO(old_avatar))
            #     )
            #     log.debug(
            #         f"{self.user} ({self.pk_member_id}): Avatar Difference: {hash_avatar - hash_old_avatar}"
            #     )
            # except UnidentifiedImageError:
            #     hash_avatar = 0
            #     hash_old_avatar = 0
            #     log.debug(
            #         f"{self.user} ({self.pk_member_id}): Avatar comparison failed. Resorting to just updating"
            #     )

            # if not hash_avatar - hash_old_avatar < cutoff:
            #     log.debug(f"{self.user} ({self.pk_member_id}): Updating Avatar")
            #     if no_timeout:
            #         await asyncio.wait_for(self.user.edit(avatar=avatar), 300)
            #         pass
            #     else:
            #         await asyncio.wait_for(self.user.edit(avatar=avatar), 10)
            #     return 0
            # else:
            #     log.debug(
            #         f"{self.user} ({self.pk_member_id}): Skipping updating avatar because avatars are similar"
            #     )
            #     return 0
        except discord.HTTPException as e:
            log.info(
                f"{self.user} ({self.pk_member_id}): Avatar Update Failed. \n {e.text}"
            )
            if "too fast" in e.text.lower():
                return "Avatar is being updated too frequently"
            else:
                return "An unknown error occurred while updating avatar"
        except asyncio.TimeoutError:
            return "Avatar not updated because Discord took too long"
        except discord.errors.InvalidArgument:
            return "Avatar image type is invalid"

    async def update_default_roles(self):
        await self.wait_until_ready()
        log.debug(f"{self.user} ({self.pk_member_id}): Updating default roles")
        add_roles = []
        remove_roles = []
        try:
            for role in INSTANCE_ADD_ROLES:
                role = discord.utils.get(self.get_guild(GUILD_ID).roles, name=role)
                if role is not None:
                    add_roles.append(role)
            for role in INSTANCE_REMOVE_ROLES:
                role = discord.utils.get(self.get_guild(GUILD_ID).roles, name=role)
                if role is not None:
                    remove_roles.append(role)
        except AttributeError as e:
            log.info(f"{self.user} ({self.pk_member_id}): Error updating roles: {e}")
            return "Failed to update default roles. Is the bot on the server?"
        from polyphony.bot import bot

        if add_roles:
            await bot.get_guild(GUILD_ID).get_member(self.user.id).add_roles(*add_roles)
        if remove_roles:
            await bot.get_guild(GUILD_ID).get_member(self.user.id).remove_roles(
                *remove_roles
            )
        return

    async def update_nickname(self, name):
        await self.wait_until_ready()
        log.debug(f"{self.user} ({self.pk_member_id}): Updating nickname in guilds")
        return_value = 0

        if len(name or "") > 32:
            return -1

        if name is None or name == "":
            name = self.user.display_name[2:]

        conn.execute(
            "UPDATE members SET nickname = ? WHERE id == ?",
            [name, self.user.id],
        )
        conn.commit()

        for guild in self.guilds:
            try:
                await guild.get_member(self.user.id).edit(nick=name)
                log.debug(
                    f"{self.user} ({self.pk_member_id}): Updated nickname to {name} on guild {guild.name}"
                )
            except AttributeError:
                log.debug(
                    f"{self.user} ({self.pk_member_id}): Failed to update nickname to {name} on guild {guild.name}"
                )
                return_value += 1
                pass

        return return_value
