import asyncio
import json
import logging
import re
import time
from datetime import timedelta

import discord
import emoji
import requests
from discord.ext import commands
from discord.ext.commands import EmojiConverter

from polyphony.bot import helper, bot
from polyphony.helpers.database import conn
from polyphony.helpers.message_cache import (
    new_proxied_message,
    recently_proxied_messages,
)
from polyphony.helpers.reset import reset
from polyphony.settings import (
    COMMAND_PREFIX,
    DELETE_LOGS_CHANNEL_ID,
    DELETE_LOGS_USER_ID, GUILD_ID,
)

log = logging.getLogger("polyphony." + __name__)


class Events(commands.Cog):
    def __init__(self, bot: discord.ext.commands.bot):
        self.bot = bot
        self.edit_session = []

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        start = time.time()  # For benchmark debug message

        # Cancel if using bot command prefix (allows bot commands to run)
        if msg.content.startswith(COMMAND_PREFIX):
            return

        # Skip for edit react
        if msg.author.id in self.edit_session:
            return

        # Get the system
        system = conn.execute(
            "SELECT * FROM members WHERE main_account_id == ? AND member_enabled = 1",
            [msg.author.id],
        ).fetchall()

        ping_suppress = False  # Set to suppress ping. Used to prevent double ping forwarding with a proxied ping.

        # Set datastructures
        member_data = {
            "prefix": None,
            "suffix": None,
        }
        member = None

        # Compile tags with member objects
        tags = []
        for m in system:
            for t in json.loads(m["pk_proxy_tags"]):
                tags.append([t, m])

        # Check tags and set member
        for tag in tags:
            if msg.content.startswith(
                tag[0].get("prefix") or ""
            ) and msg.content.endswith(tag[0].get("suffix") or ""):
                member_data["prefix"] = tag[0].get("prefix") or ""
                member_data["suffix"] = tag[0].get("suffix") or ""
                member = tag[1]
                break

        # Get autoproxy status
        ap_data = {"mode": None, "user": None}
        db_user = conn.execute(
            "SELECT * FROM users WHERE id == ?", [msg.author.id]
        ).fetchone()
        if db_user is not None:
            ap_data["mode"] = db_user["autoproxy_mode"]
            ap_data["user"] = db_user["autoproxy"]

        # Check for autoproxy
        if member is None and ap_data["mode"] is not None:
            member = conn.execute(
                "SELECT * FROM members WHERE id == ? AND member_enabled = 1",
                [ap_data["user"]],
            ).fetchone()

        # Send message if member is set
        if member is not None:
            log.debug(
                f"""{member['member_name']} ({member["pk_member_id"]}): Processing new message in {msg.channel} => "{msg.content}" (attachments: {len(msg.attachments)})"""
            )

            # Set autoproxy latch
            if ap_data["mode"] == "latch" and (
                member_data["prefix"] is not None or member_data["suffix"] is not None
            ):
                log.debug(f"Setting autoproxy latch to {member['display_name']}")

                # Update database to remember current latch
                conn.execute(
                    "UPDATE users SET autoproxy = ? WHERE id == ?",
                    [member["id"], msg.author.id],
                )
                conn.commit()

            # Remove prefix/suffix
            message = msg.content[
                len(member_data["prefix"] or "")
                or None : -len(member_data["suffix"] or "")
                or None
            ]

            if msg.mentions:
                mention_author = True
            else:
                mention_author = False

            # Send proxied message
            attempts = 0
            while await helper.send_as(
                msg,
                message,
                member["token"],
                files=[await file.to_file() for file in msg.attachments],
                reference=msg.reference,
                emote_cache=bot.get_guild(GUILD_ID),  # TODO: Maybe put outside of event
                mention_author=mention_author
            ) is False:
                log.debug(f"Helper failed to send (attempt {attempts} of 3)")
                attempts += 1
                await reset()
            if attempts >= 3:
                log.error(
                    f"""{member['member_name']} ({member["pk_member_id"]}): Message in {msg.channel} failed to send => "{msg.content}" (attachments: {len(msg.attachments)})"""
                )
                return
            await msg.delete()

            # Server log channel message deletion handler (cleans up logging channel)
            new_proxied_message(msg)

            end = time.time()  # For benchmarking purposes
            log.debug(
                f"{member['member_name']} ({member['pk_member_id']}): Benchmark: {timedelta(seconds=end - start)} | Protocol Roundtrip: {timedelta(seconds=self.bot.latency)}"
            )

            ping_suppress = True  # Message was proxied so suppress it

        # Check for ping
        all_members = conn.execute(
            "SELECT * FROM members WHERE member_enabled = 1"
        ).fetchall()
        # Get the database entry for the current member (if any)
        msg_member = conn.execute(
            "SELECT * FROM members WHERE id = ?", [msg.author.id]
        ).fetchone()
        # Get the system of the current member (if any)
        if msg_member is not None:
            system = conn.execute(
                "SELECT * FROM members WHERE main_account_id = ?",
                [msg_member["main_account_id"]],
            ).fetchall()

        # If a message was proxied, the ping is suppressed to avoid a double-ping from the instance and the original message
        if not ping_suppress:
            for member in all_members:
                # Check for a valid ping
                if (
                    member["id"] in [m.id for m in msg.mentions]
                    and msg.author.id != member["main_account_id"]
                    and msg.author.id != member["id"]
                    and msg.author.id != self.bot.user.id
                    and not msg.content.startswith(COMMAND_PREFIX)
                ):
                    embed = discord.Embed(
                        description=f"Originally to {self.bot.get_user(member['id']).mention}\n[Highlight Message]({msg.jump_url})"
                    )
                    embed.set_author(
                        name=f"From {msg.author}",
                        icon_url=msg.author.avatar_url,
                    )

                    # Check if ping is from another Polyphony instance
                    if msg.author.bot is True and msg.author.id in [
                        m["id"] for m in all_members
                    ]:
                        # Check member isn't part of author's own system
                        if member["id"] not in [m["id"] for m in system]:
                            # Forward Ping from Instance
                            log.debug(
                                f"Forwarding ping from {member['id']} to {member['main_account_id']} (from proxy)"
                            )
                            await self.bot.get_channel(msg.channel.id).send(
                                f"{self.bot.get_user(member['main_account_id']).mention}",
                                embed=embed,
                            )
                    else:
                        # Forward Ping from non-polyphony instance
                        log.debug(
                            f"Forwarding ping from {member['id']} to {member['main_account_id']}"
                        )

                        await self.bot.get_channel(msg.channel.id).send(
                            f"{self.bot.get_user(member['main_account_id']).mention}",
                            embed=embed,
                        )
                    break

        # Delete logging channel message
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
                    member_ids = [m["id"] for m in system]
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
            if type(reaction.emoji) is str:
                if (
                    emoji.demojize(reaction.emoji) or ""
                ) == ":cross_mark:":  # Discord name: x
                    await reaction.message.delete()

                # Edit React
                if (
                    emoji.demojize(reaction.emoji) or ""
                ) == ":memo:":  # Discord name: pencil
                    self.edit_session.append(user.id)
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
                        # If message isn't "cancel" then momentarily switch bot tokens and edit the message
                        if message.content.lower() != "cancel":
                            while await helper.edit_as(
                                reaction.message, message.content, member["token"]
                            ) is False:
                                await reset()
                        # Delete instructions and edit message with main bot (again, low-level is easier without ctx)
                        await instructions.delete()
                        # bot.http.delete_message(instructions.channel.id, instructions.id),
                        await message.delete()
                        # bot.http.delete_message(message.channel.id, message.id),
                        await reaction.remove(user)

                    # On timeout, delete instructions and reaction
                    except asyncio.TimeoutError:
                        # Delete instructions with main bot
                        await asyncio.gather(
                            instructions.delete(), reaction.remove(user)
                        )

                    self.edit_session.remove(user.id)


def setup(bot):
    log.debug("Events module loaded")
    bot.add_cog(Events(bot))


def teardown(bot):
    log.debug("Events module unloaded")
