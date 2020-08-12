import asyncio
import logging
import sqlite3
from typing import List

from polyphony.instance.bot import PolyphonyInstance

log = logging.getLogger(__name__)

# List of Instance Threads
instances: List[PolyphonyInstance] = []


def create_member_instance(member: sqlite3.Row) -> PolyphonyInstance:
    """
    Create member instance threads from dictionary that is returned from database
    :param member: directory that is returned from database functions
    """
    if not member["member_enabled"]:
        pass
    log.debug(
        f"Creating member instance {member['member_name']} ({member['pk_member_id']})"
    )
    new_instance = PolyphonyInstance(
        member["token"],
        member["pk_member_id"],
        member["discord_account_id"],
        member["member_name"],
        member["display_name"],
        member["pk_avatar_url"],
        member["pk_proxy_tags"],
        member["nickname"],
    )
    loop = asyncio.get_event_loop()
    loop.create_task(new_instance.start(member["token"]))
    instances.append(new_instance)
    return new_instance
