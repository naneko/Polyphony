"""
Checks to perform when running commands
"""
import asyncio
import logging

import discord
from discord.ext import commands

from polyphony.helpers.database import conn
from polyphony.settings import MODERATOR_ROLES

log = logging.getLogger(__name__)


def is_mod():
    """
    Decorator
    Is a moderator as defined in the settings
    """

    async def predicate(ctx: commands.context):
        if any(role.name in MODERATOR_ROLES for role in ctx.message.author.roles):
            return True
        else:
            return False

    return commands.check(predicate)


def is_polyphony_user():
    """
    Decorator
    Is a Polyphony user in the users database
    """
    # TODO: Add error message that self deletes
    async def predicate(ctx: commands.context):
        user = conn.execute(
            "SELECT * FROM users WHERE id = ?", [ctx.author.id]
        ).fetchone()
        if user is not None:
            return True
        else:
            return False

    return commands.check(predicate)


async def check_token(token: str) -> [bool, int]:
    """
    Checks discord token is valid

    :param token: Discord Token
    :return: boolean
    """
    out = True
    client_id = None
    test_client = discord.Client()

    log.debug("Checking bot token...")

    try:
        log.debug("Attempting login...")
        loop = asyncio.get_event_loop()
        loop.create_task(test_client.start(token))
        await asyncio.wait_for(test_client.wait_until_ready(), timeout=3)
        client_id = test_client.user.id
        log.debug("Login success")
    except asyncio.exceptions.TimeoutError:  # Intentionally broad exception catch
        log.debug("Bot token invalid")
        out = False
    finally:
        await test_client.close()
        log.debug("Logout of test instance complete.")

    return [out, client_id]
