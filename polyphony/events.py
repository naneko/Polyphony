import asyncio
import logging
import time
from datetime import timedelta

import discord
import emoji
from discord.ext import commands

from polyphony.helpers.instances import (
    instances,
    update_presence,
)
from polyphony.helpers.message_cache import (
    new_proxied_message,
    recently_proxied_messages,
)
from polyphony.settings import (
    COMMAND_PREFIX,
    DELETE_LOGS_CHANNEL_ID,
    DELETE_LOGS_USER_ID,
)

log = logging.getLogger("polyphony." + __name__)


class Events(commands.Cog):
    def __init__(self, bot: discord.ext.commands.bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        for instance in instances:
            if instance.main_user_account_id == msg.author.id:
                if instance.is_ready() is False:
                    continue

                if instance.main_user is None:
                    # Update Presence
                    # This is a fix for a problem where self.main_user was being set to None in on_ready()
                    instance.main_user = instance.get_user(
                        instance.main_user_account_id
                    )
                    if instance.main_user is not None:
                        log.debug(
                            f"{instance.user} ({instance.pk_member_id}): Presence was set to None."
                        )
                        await update_presence(instance)

                start = time.time()

                prefix_used = None
                suffix_used = None

                # Check prefix/suffix and get value
                for tag in instance.pk_proxy_tags:
                    if msg.content.startswith(
                        tag.get("prefix") or ""
                    ) and msg.content.endswith(tag.get("suffix") or ""):
                        prefix_used = tag.get("prefix") or ""
                        suffix_used = tag.get("suffix") or ""
                        break

                # Check message
                if (
                    prefix_used is not None
                    and suffix_used is not None
                    and msg.author is not instance.user
                    and msg.author.id == instance.main_user_account_id
                ):
                    log.debug(
                        f'{instance.user} ({instance.pk_member_id}): Processing new message in {msg.channel} => "{msg.content}" (attachments: {len(msg.attachments)})'
                    )

                    # Remove prefix/suffix
                    message = msg.content[
                        len(prefix_used or "") or None : -len(suffix_used or "") or None
                    ]

                    # Delete and send at same time to be as fast as possible

                    # Trigger typing if uploading attachment
                    await msg.channel.trigger_typing() if len(
                        msg.attachments
                    ) > 0 else None

                    await asyncio.gather(
                        # Delete Message. Without context, it's easier to call the low-level method in discord.http.
                        msg.delete(),
                        # Send new message
                        instance.get_channel(msg.channel.id).send(
                            message,
                            files=[await file.to_file() for file in msg.attachments],
                        ),
                    )

                    new_proxied_message(msg)

                    end = time.time()
                    log.debug(
                        f"{instance.user} ({instance.pk_member_id}): Benchmark: {timedelta(seconds=end - start)} | Protocol Roundtrip: {timedelta(seconds=instance.latency)}"
                    )

            # Check for ping
            elif (
                instance.user in msg.mentions
                and msg.author.id != instance.main_user_account_id
                and msg.author.id != instance.user.id
                and msg.author.id != self.bot.user.id
                and msg.author.bot is False
                and not msg.content.startswith(COMMAND_PREFIX)
            ):
                # Forward Ping
                log.debug(
                    f"Forwarding ping from {instance.user} to {instance.main_user}"
                )

                embed = discord.Embed(
                    description=f"Originally to {instance.user.mention}\n[Highlight Message]({msg.jump_url})"
                )
                embed.set_author(
                    name=f"From {msg.author}", icon_url=msg.author.avatar_url,
                )

                await self.bot.get_channel(msg.channel.id).send(
                    f"{instance.main_user.mention}", embed=embed,
                )

        # Delete logging message
        if DELETE_LOGS_USER_ID is not None and DELETE_LOGS_CHANNEL_ID is not None:
            if (
                msg.channel.id == DELETE_LOGS_CHANNEL_ID
                or msg.author.id == DELETE_LOGS_USER_ID
            ):
                try:
                    embed_text = msg.embeds[0].description
                except IndexError:
                    return

                for oldmsg in recently_proxied_messages:
                    member_ids = []
                    for instance in instances:
                        if instance.is_ready():
                            member_ids.append(instance.user.id)
                    if str(oldmsg.id) in embed_text and not any(
                        [str(member_id) in embed_text for member_id in member_ids]
                    ):
                        log.debug(
                            f"Deleting delete log message {msg.id} (was about {oldmsg.id})"
                        )
                        await msg.delete()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        for instance in instances:
            if instance.is_ready() is False:
                continue

            # Check for correct user
            if reaction.message.author == instance.user and user == instance.main_user:
                # Delete React
                if (
                    emoji.demojize(reaction.emoji) or ""
                ) == ":cross_mark:":  # Discord name: x
                    await reaction.message.delete()

                # Edit React
                if (
                    emoji.demojize(reaction.emoji) or ""
                ) == ":memo:":  # Discord name: pencil
                    embed = discord.Embed(
                        description=f"You are now editing a [message]({reaction.message.jump_url})\nYour next message will replace it's contents.",
                        color=discord.Color.orange(),
                    )
                    embed.set_footer(text='Type "cancel" to cancel edit')
                    instructions = await reaction.message.channel.send(
                        f"{user.mention}", embed=embed
                    )

                    edit_message = await instance.get_channel(
                        reaction.message.channel.id
                    ).fetch_message(reaction.message.id)

                    try:

                        # Wait 30 seconds for new message
                        message = await instance.wait_for(
                            "message",
                            check=lambda message: message.author == instance.main_user,
                            timeout=30,
                        )

                        # On new message, do all the things
                        await asyncio.gather(
                            # Delete instructions and edit message with main bot (again, low-level is easier without ctx)
                            instructions.delete(),
                            # bot.http.delete_message(instructions.channel.id, instructions.id),
                            message.delete(),
                            # bot.http.delete_message(message.channel.id, message.id),
                            reaction.remove(user),
                            # If message isn't "cancel" then edit the message
                            edit_message.edit(content=message.content)
                            if message.content.lower() != "cancel"
                            else asyncio.sleep(0),
                        )

                    # On timeout, delete instructions and reaction
                    except asyncio.TimeoutError:
                        # Delete instructions with main bot
                        await asyncio.gather(
                            instructions.delete(), reaction.remove(user)
                        )

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        for instance in instances:
            if instance.is_ready() is False:
                continue

            if (
                instance.main_user_account_id == after.id
                and before.status != after.status
            ):
                log.debug(
                    f"{instance.user} ({instance.pk_member_id}): Updating presence to {after.status}"
                )
                instance.main_user = instance.get_user(instance.main_user_account_id)
                await update_presence(instance, after.status)


def setup(bot):
    log.debug("Events module loaded")
    bot.add_cog(Events(bot))


def teardown(bot):
    log.warning("Events module unloaded")
