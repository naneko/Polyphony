"""
Checks to perform when running commands
"""
import logging

import discord
from discord.ext import commands

from polyphony.helpers.database import get_user
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
            await ctx.send(
                f"Sorry {ctx.message.author.mention}. You are not a Polyphony moderator.",
                delete_after=10,
            )
            return False

    return commands.check(predicate)


def is_polyphony_user(allow_mods: bool = False):
    """
    Decorator
    Is a Polyphony user in the users database
    """
    # TODO: Add error message that self deletes
    async def predicate(ctx: commands.context):
        user = get_user(ctx.author.id)
        is_mod = False
        if allow_mods:
            is_mod = any(
                role.name in MODERATOR_ROLES for role in ctx.message.author.roles
            )
        if is_mod or user is not None:
            return True
        else:
            await ctx.send(
                f"Sorry {ctx.message.author.mention}. You are not a Polyphony user. Contact a moderator if you believe this is a mistake.",
                delete_after=10,
            )
            return False

    return commands.check(predicate)


async def check_token(token: str) -> bool:
    """
    Checks discord token is valid

    :param token: Discord Token
    :return: boolean
    """
    out = True
    test_client = discord.Client()

    log.debug("Checking bot token...")

    try:
        log.debug("Attempting login...")
        await test_client.login(token)
        log.debug("Login successs")
    except discord.LoginFailure:
        log.debug("Bot token invalid")
        out = False
    finally:
        await test_client.logout()
        log.debug("Logout of test instance complete.")

    return out
