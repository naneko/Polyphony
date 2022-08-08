import logging

from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)


class SyncAll(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    group = app_commands.Group(name="syncall", description="...")

