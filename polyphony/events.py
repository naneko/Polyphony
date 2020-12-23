import asyncio
import json
import logging
import time
from datetime import timedelta

import discord
import emoji
from discord.ext import commands

from polyphony.helpers.database import conn
from polyphony.helpers.message_cache import (
    new_proxied_message,
    recently_proxied_messages,
)
from polyphony.settings import (
    COMMAND_PREFIX,
    DELETE_LOGS_CHANNEL_ID,
    DELETE_LOGS_USER_ID,
    TOKEN,
)

log = logging.getLogger("polyphony." + __name__)


class Events(commands.Cog):
    def __init__(self, bot: discord.ext.commands.bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        start = time.time()
        if msg.content.startswith(COMMAND_PREFIX):
            return
        members = conn.execute(
            "SELECT * FROM members WHERE main_account_id == ? AND member_enabled = 1",
            [msg.author.id],
        ).fetchall()

        for member in members:
            prefix_used = None
            suffix_used = None

            # Check prefix/suffix and get value
            for tag in json.loads(member["pk_proxy_tags"]):
                if msg.content.startswith(
                    tag.get("prefix") or ""
                ) and msg.content.endswith(tag.get("suffix") or ""):
                    prefix_used = tag.get("prefix") or ""
                    suffix_used = tag.get("suffix") or ""
                    break

            # Get autoproxy info
            db_user = conn.execute(
                "SELECT * FROM users WHERE id == ?", [msg.author.id]
            ).fetchone()
            autoproxy_mode = db_user["autoproxy_mode"]
            autoproxy = db_user["autoproxy"]

            # Cancel autoproxy if prefix is used
            # This is hacky because it was implemented later on. Probably could be more optimized.
            if autoproxy_mode is not None and autoproxy == member["id"]:
                for m in members:
                    for tag in json.loads(m["pk_proxy_tags"]):
                        if msg.content.startswith(
                            tag["prefix"] or ""
                        ) and msg.content.endswith(tag["suffix"] or ""):
                            log.debug(
                                f"{m['member_name']} ({m['pk_member_id']}): Autoproxy skipped"
                            )
                            autoproxy_mode = None

            # Check message
            if (
                prefix_used is not None
                and suffix_used is not None
                and msg.author.id is not member["main_account_id"]
            ) or (
                autoproxy_mode is not None
                and member["id"] == autoproxy
                and prefix_used is None
                and suffix_used is None
                and msg.author.id is not member["main_account_id"]
            ):
                log.debug(
                    f"""{member['member_name']} ({member['pk_member_id']}): Processing new message in {msg.channel} => "{msg.content}" (attachments: {len(msg.attachments)})"""
                )

                # Set latch autoproxy
                if autoproxy_mode == "latch" and (
                    prefix_used is not None or suffix_used is not None
                ):
                    log.debug(f"Setting autoproxy latch to {member['display_name']}")
                    conn.execute(
                        "UPDATE users SET autoproxy = ? WHERE id == ?",
                        [member["id"], msg.author.id],
                    )
                    conn.commit()

                # Remove prefix/suffix
                message = msg.content[
                    len(prefix_used or "") or None : -len(suffix_used or "") or None
                ]

                # Delete and send at same time to be as fast as possible

                # Trigger typing if uploading attachment
                await msg.channel.trigger_typing() if len(msg.attachments) > 0 else None

                # Momentarily switch bot tokens and send message
                self.bot.http.token = member["token"]
                await msg.channel.send(
                    message, files=[await file.to_file() for file in msg.attachments],
                )
                self.bot.http.token = TOKEN
                await msg.delete()

                new_proxied_message(msg)

                end = time.time()
                log.debug(
                    f"{member['member_name']} ({member['pk_member_id']}): Benchmark: {timedelta(seconds=end - start)} | Protocol Roundtrip: {timedelta(seconds=self.bot.latency)}"
                )

        # Check for ping
        members = conn.execute(
            "SELECT * FROM members WHERE member_enabled = 1"
        ).fetchall()
        for member in members:
            if (
                member["id"] in [m.id for m in msg.mentions]
                and msg.author.id != member["main_account_id"]
                and msg.author.id != member["id"]
                and msg.author.id != self.bot.user.id
                and msg.author.bot is False
                and not msg.content.startswith(COMMAND_PREFIX)
            ):
                # Forward Ping
                log.debug(
                    f"Forwarding ping from {member['id']} to {member['main_account_id']}"
                )

                embed = discord.Embed(
                    description=f"Originally to {self.bot.get_user(member['id']).mention}\n[Highlight Message]({msg.jump_url})"
                )
                embed.set_author(
                    name=f"From {msg.author}", icon_url=msg.author.avatar_url,
                )

                await self.bot.get_channel(msg.channel.id).send(
                    f"{self.bot.get_user(member['main_account_id']).mention}",
                    embed=embed,
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
                    member_ids = [m["id"] for m in members]
                    if str(oldmsg.id) in embed_text and not any(
                        [str(member_id) in embed_text for member_id in member_ids]
                    ):
                        log.debug(
                            f"Deleting delete log message {msg.id} (was about {oldmsg.id})"
                        )
                        await msg.delete()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
        member = conn.execute(
            "SELECT * FROM members WHERE main_account_id == ? AND id = ? AND member_enabled = 1",
            [user.id, reaction.message.author.id],
        ).fetchone()

        # Check for correct user
        if member is not None:
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

                try:

                    # Wait 30 seconds for new message
                    message = await self.bot.wait_for(
                        "message",
                        check=lambda message: message.author.id
                        == member["main_account_id"],
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
                    )
                    # If message isn't "cancel" then momentarily switch bot tokens and edit the message
                    if message.content.lower() != "cancel":
                        self.bot.http.token = member["token"]
                        await reaction.message.edit(content=message.content)
                        self.bot.http.token = TOKEN

                # On timeout, delete instructions and reaction
                except asyncio.TimeoutError:
                    # Delete instructions with main bot
                    await asyncio.gather(instructions.delete(), reaction.remove(user))


def setup(bot):
    log.debug("Events module loaded")
    bot.add_cog(Events(bot))


def teardown(bot):
    log.debug("Events module unloaded")
