import asyncio
import importlib
import logging
import sqlite3
from typing import List

import discord

import polyphony.instance.bot

log = logging.getLogger(__name__)

# List of Instance Threads
instances: List[polyphony.instance.bot.PolyphonyInstance] = []


def reload_instance_module():
    importlib.reload(polyphony.instance.bot)
    logging.debug("Instance module reloaded")


def create_member_instance(
    member: sqlite3.Row,
) -> polyphony.instance.bot.PolyphonyInstance:
    """
    Create member instance threads from dictionary that is returned from database
    :param member: directory that is returned from database functions
    """
    if not member["member_enabled"]:
        pass
    log.debug(
        f"Creating member instance {member['member_name']} ({member['pk_member_id']})"
    )
    new_instance = polyphony.instance.bot.PolyphonyInstance(
        member["token"],
        member["pk_member_id"],
        member["discord_account_id"],
        member["member_name"],
        member["display_name"],
        member["pk_avatar_url"],
        member["pk_proxy_tags"],
        member["nickname"],
    )
    from polyphony.bot import bot

    # bot.loop.create_task(new_instance.start(member["token"]))
    asyncio.run_coroutine_threadsafe(new_instance.start(member["token"]), bot.loop)
    instances.append(new_instance)
    return new_instance


async def update_presence(instance, status=discord.Status.online, name=None):
    await instance.wait_until_ready()
    log.debug(
        f'{instance.user} ({instance.pk_member_id}): Setting presence to "Listening to {instance.main_user or name or "..."}"'
    )
    await instance.change_presence(
        status=status,
        activity=discord.Activity(
            name=f"{instance.main_user or name or '...'}",
            type=discord.ActivityType.listening,
        ),
    )
    return True
