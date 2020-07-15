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
from polyphony.helpers.pluralkit import pk_get_member
from polyphony.settings import COMMAND_PREFIX

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
        self._token: str = token
        self._pk_member_id: str = pk_member_id
        self._discord_account_id: int = discord_account_id
        self.__member_name: str = member_name
        self.__display_name: str = display_name
        self.__pk_avatar_url: str = pk_avatar_url
        self.__pk_proxy_tags: dict = json.loads(pk_proxy_tags)

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        log.info(
            f"Instance started as {self.user} ({self._pk_member_id}). Initializing..."
        )
        self.member_name: str = self.__member_name
        if self.__display_name:
            self.display_name: str = self.__display_name
        else:
            self.display_name: str = self.__member_name
        self.pk_avatar_url: str = self.__pk_avatar_url
        self.pk_proxy_tags: dict = self.__pk_proxy_tags
        for guild in self.guilds:
            await guild.get_member(self.user.id).edit(nick=self._display_name)

        self_user = self.get_user(self._discord_account_id)
        if self_user:
            await self.change_presence(
                activity=discord.Activity(
                    name=f"{self_user.name}#{self_user.discriminator}",
                    type=discord.ActivityType.listening,
                )
            )
        else:
            # TODO: Member user has left the server
            log.warning(
                f"The main account for {self.user} ({self._pk_member_id}) has left all guilds with Polyphony"
            )
        with conn:
            log.debug(
                f"{self.user} ({self._pk_member_id}): Updating Self Account ID: {self.user.id}"
            )
            c.execute(
                "UPDATE members SET member_account_id = ? WHERE pk_member_id = ?",
                [self.user.id, self._pk_member_id],
            )
        log.info(f"{self.user} ({self._pk_member_id}): Initialization complete")

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

    async def sync(self, ctx=None) -> bool:
        """
        Sync with PluralKit

        :return (boolean) was successful
        """
        log.info(f"{self.user} ({self._pk_member_id}) is syncing")
        member = await pk_get_member(self._pk_member_id)
        if member is None:
            log.warning(f"Failed to sync{self.user} ({self._pk_member_id})")
            return False
        self.member_name = member["name"]
        self.display_name = member["display_name"]
        self.pk_avatar_url = member["avatar_url"]
        self.pk_proxy_tags = member["proxy_tags"][0]
        await self.update(ctx)
        log.info(f"{self.user} ({self._pk_member_id}): Sync complete")
        return True

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
            log.debug(f"{self.user} ({self._pk_member_id}): Updating Display Name")
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
                [json.dumps(value), self._token],
            )

    def get_token(self):
        return self._token

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

    async def on_message(self, message: discord.Message):
        start = time.time()
        if (
            message.content.startswith(self.pk_proxy_tags.get("prefix") or "")
            and message.content.endswith(self.pk_proxy_tags.get("suffix") or "")
            and message.author is not self.user
            and message.author.id == self._discord_account_id
        ):
            log.debug(
                f'{self.user} ({self._pk_member_id}): Processing new message => "{message.content}" (attachments: {len(message.attachments)})'
            )
            msg = message.content[
                len(self.pk_proxy_tags.get("prefix") or "")
                or None : -len(self.pk_proxy_tags.get("suffix") or "")
                or None
            ]

            # Do both at the same time to be as fast as possible
            from polyphony.bot import bot

            await asyncio.gather(
                message.channel.trigger_typing()
                if len(message.attachments) > 0
                else asyncio.sleep(0),
                bot.http.delete_message(message.channel.id, message.id),
                message.channel.send(
                    msg, files=[await file.to_file() for file in message.attachments],
                ),
            )
            end = time.time()
            log.debug(
                f"{self.user} ({self._pk_member_id}): Benchmark: {timedelta(seconds=end - start)} | Protocol Roundtrip: {timedelta(seconds=self.latency)}"
            )
        elif (
            self.user in message.mentions
            and message.author.id != self._discord_account_id
            and message.author.id != self.user.id
            and not message.content.startswith(COMMAND_PREFIX)
        ):
            log.debug(
                f"Forwarding ping from {self.user} to {self.get_user(self._discord_account_id)}"
            )
            from polyphony.bot import bot

            embed = discord.Embed(
                description=f"Originally to {self.user.mention}\n[Highlight Message]({message.jump_url})"
            )
            embed.set_author(
                name=f"From {message.author}", icon_url=message.author.avatar_url,
            )

            await bot.get_channel(message.channel.id).send(
                f"{self.get_user(self._discord_account_id).mention}", embed=embed,
            )

    async def on_guild_join(self, guild: discord.Guild):
        await guild.get_member(self.user.id).edit(nick=self._display_name)

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        if reaction.message.author == self.user and user == self.get_user(
            self._discord_account_id
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

                # Gets the message with the main bot in order to remove the reaction
                remove_reaction_message = await bot.get_channel(
                    reaction.message.channel.id
                ).fetch_message(reaction.message.id)
                try:
                    message = await self.wait_for(
                        "message",
                        check=lambda message: message.author
                        == self.get_user(self._discord_account_id),
                        timeout=30,
                    )
                    remove_reaction_message = await bot.get_channel(
                        message.channel.id
                    ).fetch_message(reaction.message.id)
                    await asyncio.gather(
                        # Delete with main bot:
                        bot.http.delete_message(
                            instructions.channel.id, instructions.id
                        ),
                        bot.http.delete_message(message.channel.id, message.id),
                        remove_reaction_message.remove_reaction(
                            reaction.emoji, self.get_user(self._discord_account_id)
                        ),
                        reaction.message.edit(content=message.content)
                        if message.content.lower() != "cancel"
                        else asyncio.sleep(0),
                        # Delete with instance bot user:
                        # instructions.delete(),
                        # message.delete(),
                        # reaction.remove(user),
                    )
                except asyncio.TimeoutError:
                    # Delete with main bot:
                    await asyncio.gather(
                        bot.http.delete_message(
                            instructions.channel.id, instructions.id
                        ),
                        remove_reaction_message.remove_reaction(
                            reaction.emoji, self.get_user(self._discord_account_id)
                        ),
                    )
                    # Delete with instance bot user:
                    # await asyncio.gather(
                    #     instructions.delete(), reaction.remove(user),
                    # )
