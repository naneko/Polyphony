import logging

import discord
from discord import app_commands
from discord.ext import commands

from polyphony.helpers.checks import is_owner
from polyphony.helpers.database import conn
from polyphony.settings import MODERATOR_ROLES

log = logging.getLogger(__name__)


class Enable(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command()
    @app_commands.checks.has_any_role(*MODERATOR_ROLES)
    @app_commands.check(is_owner)
    def enable(self, interaction: discord.Interaction, system_member: discord.Member):
        """
        Reintroduce a suspended instance into the wild.

        param interaction: Discord Interaction
        param system_member: Member to enable
        """
        member = conn.execute(
            "SELECT * FROM members WHERE id = ?",
            [system_member.id],
        ).fetchone()