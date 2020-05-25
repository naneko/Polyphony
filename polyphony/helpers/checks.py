"""
Checks to perform when running commands
"""
import logging

from discord.ext import commands

from .database import get_users
from polyphony.settings import MODERATOR_ROLES

log = logging.getLogger(__name__)


def is_mod():
    """
    Is a moderator as defined in the settings
    :return: (bool) User is moderator
    """

    def predicate(ctx):
        return MODERATOR_ROLES in ctx.message.author.roles

    return commands.check(predicate)


def is_polyphony_user():
    """
    Is a Polyphony user in the users database
    :return: (bool) User is Polyphony user
    """

    def predicate(ctx):
        return ctx.message.author.id in get_users()

    return commands.check(predicate)
