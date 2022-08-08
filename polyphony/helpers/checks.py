"""
Checks to perform when running commands
"""
import asyncio
import logging

import discord
from discord.ext import commands

from polyphony.bot import bot
from polyphony.helpers.database import conn
from polyphony.settings import MODERATOR_ROLES

log = logging.getLogger(__name__)


def is_owner(interaction: discord.Interaction) -> bool:
    return interaction.user.id == bot.owner_id


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
        await test_client.wait_until_ready()
        client_id = test_client.user.id
        log.debug("Login successs")
    except discord.LoginFailure:
        log.debug("Bot token invalid")
        out = False
    finally:
        await test_client.close()
        log.debug("Logout of test instance complete.")

    return [out, client_id]
