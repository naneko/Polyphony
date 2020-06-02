"""
Checks to perform when running commands
"""
import logging

from discord.ext import commands

from polyphony.helpers.database import get_users
from polyphony.settings import MODERATOR_ROLES

log = logging.getLogger(__name__)


def is_mod():
    """
    Is a moderator as defined in the settings
    """

    async def predicate(ctx: commands.context):
        if MODERATOR_ROLES in ctx.message.author.roles:
            return True
        else:
            await ctx.send(
                f"Sorry {ctx.message.author.mention}. You are not a Polyphony moderator.",
                delete_after=5,
            )
            return False

    return commands.check(predicate)


def is_polyphony_user(allow_mods: bool = False):
    """
    Is a Polyphony user in the users database
    """
    # TODO: Add error message that self deletes
    async def predicate(ctx: commands.context):
        is_user = ctx.message.author.id in get_users()
        if allow_mods:
            is_user = is_user or MODERATOR_ROLES in ctx.message.author.roles
        if is_user:
            return True
        else:
            await ctx.send(
                f"Sorry {ctx.message.author.mention}. You are not a Polyphony user. Contact a moderator if you believe this is a mistake.",
                delete_after=5,
            )
            return False

    return commands.check(predicate)
