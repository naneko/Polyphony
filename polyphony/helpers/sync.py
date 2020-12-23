import asyncio
import logging
import sqlite3
from typing import List, NoReturn

import discord
from discord.ext import commands

from polyphony.helpers.database import conn
from polyphony.helpers.log_message import LogMessage
from polyphony.helpers.pluralkit import pk_get_member
from polyphony.instance.bot import PolyphonyInstance

log = logging.getLogger(__name__)


async def sync(ctx: commands.context, query: List[sqlite3.Row]) -> NoReturn:
    logger = LogMessage(ctx, title=":hourglass: Syncing All Members...")
    logger.color = discord.Color.orange()
    await logger.init()
    for i, member in enumerate(query):

        # Create instance
        instance = PolyphonyInstance(member["pk_member_id"])
        from polyphony.bot import bot

        asyncio.run_coroutine_threadsafe(instance.start(member["token"]), bot.loop)

        await instance.wait_until_ready()

        log.info(f"Syncing {instance.user}")

        await logger.log(
            f":hourglass: Syncing {instance.user.mention}... ({i+1}/{len(query)})"
        )

        # Pull from PluralKit
        pk_member = await pk_get_member(member["pk_member_id"])
        if pk_member is None:
            logger.content[
                -1
            ] = f":x: Failed to sync {instance.user.mention} from PluralKit"
            log.warning(f"Failed to sync {instance.user}")
            await instance.close()
            continue

        await instance.wait_until_ready()

        error_text = ""

        # Update Username
        if (
            instance.user.display_name != pk_member.get("name")
            and pk_member.get("name") is not None
        ):
            await logger.edit(
                -1,
                f":hourglass: Syncing {instance.user.mention} Username... ({i}/{len(query)})",
            )
            conn.execute(
                "UPDATE members SET display_name = ? WHERE pk_member_id = ?",
                [pk_member.get("name"), member["pk_member_id"]],
            )
            out = await instance.update_username(pk_member.get("name"))
            if out != 0:
                error_text += f"> {out}\n"

        # Update Avatar URL
        # TODO: Download both images and compare and skip if they are the same?
        await logger.edit(
            -1,
            f":hourglass: Syncing {instance.user.mention} Avatar... ({i}/{len(query)})",
        )
        conn.execute(
            "UPDATE members SET pk_avatar_url = ? WHERE pk_member_id = ?",
            [pk_member.get("avatar_url"), member["pk_member_id"]],
        )
        out = await instance.update_avatar(pk_member.get("avatar_url"))
        if out != 0:
            error_text += f"> {out}\n"

        # Update Nickname
        # Check if nickname is set
        await logger.edit(
            -1,
            f":hourglass: Syncing {instance.user.mention} Nickname... ({i}/{len(query)})",
        )
        if member["nickname"] != None:
            out = await instance.update_nickname(member["nickname"])
            if out < 0:
                error_text += f"> Nickname must be 32 characters or fewer in length\n"
            elif out > 0:
                error_text += f"> Nick didn't update on {out} guild(s)\n"
        # Otherwise use display_name if it exists
        else:
            conn.execute(
                "UPDATE members SET display_name = ? WHERE pk_member_id = ?",
                [pk_member.get("display_name"), member["pk_member_id"]],
            )
            out = await instance.update_nickname(
                pk_member.get("display_name") or pk_member.get("name")
            )
            if out < 0:
                error_text += f"> PluralKit display name must be 32 characters or fewer in length if you want to use it as a nickname\n"
            elif out > 0:
                error_text += f"> Nick didn't update on {out} guild(s)\n"

        if error_text == "":
            logger.content[-1] = f":white_check_mark: Synced {instance.user.mention}"
            await logger.update()
        else:
            logger.content[
                -1
            ] = f":warning: Synced {instance.user.mention} with errors:"
            await logger.log(error_text)

        log.info(f"Synced {instance.user}")

        await instance.close()

    logger.title = ":white_check_mark: Sync Complete"
    logger.color = discord.Color.green()
    await logger.update()
