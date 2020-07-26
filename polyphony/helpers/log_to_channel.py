import logging

import discord

from polyphony.settings import ADMIN_LOGS_CHANNEL_ID

log = logging.getLogger(__name__)


async def send_to_log_channel(msg: str = None, embed: discord.Embed = None):
    from polyphony.bot import bot

    channel = bot.get_channel(ADMIN_LOGS_CHANNEL_ID)

    if embed is None:
        embed = discord.Embed()

    embed.set_author(name="Polyphony Logger")

    if channel is not None:
        await channel.send(msg, embed=embed)
