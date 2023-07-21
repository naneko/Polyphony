import logging

from discord.ext import commands

log = logging.getLogger(__name__)


class Reset(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot