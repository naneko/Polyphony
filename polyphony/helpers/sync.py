import asyncio
import json
import logging
import sqlite3
from typing import List, NoReturn

import discord
from discord.ext import commands

from polyphony.helpers.database import conn
from polyphony.helpers.log_message import LogMessage
from polyphony.helpers.pluralkit import pk_get_member
from polyphony.instance.bot import PolyphonyInstance
from polyphony.settings import SYNC_BATCH_SIZE

log = logging.getLogger(__name__)


# TODO: 3 strike system for auto-suspend
async def sync(
    ctx: commands.context,
    query: List[sqlite3.Row],
    message=":hourglass: Syncing Members",
) -> NoReturn:
    async def sync_helper(i: int, total: int, member, logger):
        # Create instance
        instance = PolyphonyInstance(member["pk_member_id"])
        from polyphony.bot import bot

        asyncio.run_coroutine_threadsafe(instance.start(member["token"]), bot.loop)

        try:
            await asyncio.wait_for(instance.wait_until_ready(), timeout=10)
        except asyncio.TimeoutError:
            log.debug(f"Failed to sync {member['id']} due to timeout")
            await instance.close()
            await logger.edit(
                i,
                f":x: Failed to sync <@{member['id']}> because Discord bot login timed out. The bot token was likely reset. Please contact a moderator for assistance."
            )
            return

        log.debug(f"Syncing {instance.user} ({i + 1}/{total})")

        # Pull from PluralKit
        pk_member = await pk_get_member(member["pk_member_id"])
        if pk_member is None:
            await logger.edit(
                i, f":x: Failed to sync {instance.user.mention} from PluralKit"
            )
            log.debug(f"Failed to sync {instance.user}")
            await instance.close()
            return

        await instance.wait_until_ready()

        error_text = ""

        # Update Proxy Tags
        conn.execute(
            "UPDATE members SET pk_proxy_tags = ? WHERE pk_member_id = ?",
            [json.dumps(pk_member.get("proxy_tags")), member["pk_member_id"]],
        )

        # Update Username
        if (
                instance.user.display_name != pk_member.get("name")
                and pk_member.get("name") is not None
        ):
            await logger.edit(
                i,
                f":hourglass: Syncing {instance.user.mention} Username...",
            )
            conn.execute(
                "UPDATE members SET display_name = ? WHERE pk_member_id = ?",
                [pk_member.get("name"), member["pk_member_id"]],
            )
            out = await instance.update_username(pk_member.get("name"))
            if out != 0:
                error_text += f"> {out}\n"

        # Update Avatar URL
        if pk_member.get("avatar_url") is not None:
            await logger.edit(
                i,
                f":hourglass: Syncing {instance.user.mention} Avatar...",
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
            i,
            f":hourglass: Syncing {instance.user.mention} Nickname...",
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

        # Update Roles
        await logger.edit(
            i,
            f":hourglass: Syncing {instance.user.mention} Roles...",
        )
        out = await instance.update_default_roles()
        if out:
            error_text += f"> {out}\n"

        if error_text == "":
            await logger.edit(i, f":white_check_mark: Synced {instance.user.mention}")
        else:
            error_text = error_text if error_text.endswith("\n") else f"{error_text}\n"
            logger.content[
                i
            ] = f":warning: Synced {instance.user.mention} with errors:\n{error_text}"

        conn.commit()

        log.debug(f"Synced {instance.user}")

        await instance.close()

    total = len(query)
    logger = LogMessage(ctx, f'{message} ({total})')
    logger.color = discord.Color.orange()
    await logger.init()
    logger.content = [""] * total
    sync_queue = [[]]
    i_batch = 0
    for i, member in enumerate(query):
        logger.content[i] = f":hourglass: Syncing <@{member['id']}>..."
        if i % SYNC_BATCH_SIZE == 0:
            sync_queue.append([])
            i_batch += 1
        sync_queue[i_batch].append(sync_helper(i, total, member, logger))

    await logger.update()

    for i, batch in enumerate(sync_queue):
        log.debug(f'Syncing batch {i}')
        await asyncio.gather(*batch)

    await logger.set(":white_check_mark: Sync Complete", discord.Color.green())