import logging

import discord
from discord import app_commands
from discord.ext import commands

from polyphony.helpers.checks import is_owner
from polyphony.helpers.database import conn
from polyphony.helpers.views import Confirm
from polyphony.settings import MODERATOR_ROLES

log = logging.getLogger(__name__)


class Disable(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command()
    @app_commands.checks.has_any_role(*MODERATOR_ROLES)
    @app_commands.check(is_owner)
    async def disable(self, interaction: discord.Interaction, system_member: discord.Member):
        """
        Disables a system member permanently by deleting it from the database and kicking it from the server. Bot token cannot be reused.

        param interaction: Discord Interaction
        param system_member: Member to disable
        """
        member = conn.execute(
            "SELECT * FROM members WHERE id = ?",
            [system_member.id],
        ).fetchone()
        if member is None:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f":x: {system_member.mention} not found in database",
                    color=discord.Color.red(),
                ),
            )
            return

        log.debug(f"Disabling {system_member}")
        view = Confirm()
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f":grey_question: Disable member __{system_member}__ **permanently?**",
                color=discord.Color.yellow(),
            ),
            view=view,
        )
        await view.wait()

        if view.value is None:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    title=":x: Disable timed out",
                    description=f"User took too long to respond",
                    color=discord.Color.red(),
                ),
                view=None,
            )
            return
        elif view.value:
            conn.execute(
                "DELETE FROM members WHERE id = ?",
                [system_member.id],
            )
            conn.commit()
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f":ballot_box_with_check: {system_member.mention} **permanently disabled** by {interaction.user.mention}",
                    color=discord.Color.dark_green(),
                ),
                view=None,
            )
            log.info(
                f"{system_member} has been permanently by {interaction.user}"
            )
        else:
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f":information_source: {system_member.mention} was __not__ disabled",
                    color=discord.Color.blue(),
                ),
                view=None,
            )
            log.info(f"{system_member} not disabled")