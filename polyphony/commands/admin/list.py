import logging

import discord
from discord import app_commands
from discord.ext import commands

from polyphony.helpers.database import c
from polyphony.helpers.checks import is_owner
from polyphony.helpers.member_list import send_member_list
from polyphony.settings import MODERATOR_ROLES

log = logging.getLogger(__name__)


class List(commands.GroupCog, name="list"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command()
    @app_commands.checks.has_any_role(*MODERATOR_ROLES)
    @app_commands.check(is_owner)
    async def all(self, interaction: discord.Interaction) -> None:
        """
        ADMIN: List all members

        param interaction: Discord Interaction
        """
        log.debug("Listing all members...")
        c.execute("SELECT * FROM members")
        member_list = c.fetchall()
        embed = discord.Embed(title="All Members")
        await send_member_list(interaction, embed, member_list)

    @app_commands.command()
    @app_commands.checks.has_any_role(*MODERATOR_ROLES)
    @app_commands.check(is_owner)
    async def active(self, interaction: discord.Interaction) -> None:
        """
        ADMIN: Shows all active members

        param interaction: Discord Interaction
        """
        log.debug("Listing active members...")
        c.execute("SELECT * FROM members WHERE member_enabled == 1")
        member_list = c.fetchall()
        embed = discord.Embed(title="Active Members")
        await send_member_list(interaction, embed, member_list)

    @app_commands.command(name="system")
    @app_commands.checks.has_any_role(*MODERATOR_ROLES)
    @app_commands.check(is_owner)
    async def _system(
        self, interaction: discord.Interaction, member: discord.Member
    ) -> None:
        """
        ADMIN: List members of a system

        param interaction: Discord Interaction
        """
        log.debug(f"Listing members for {member.display_name}...")
        c.execute(
            "SELECT * FROM members WHERE main_account_id == ?",
            [member.id],
        )
        member_list = c.fetchall()
        embed = discord.Embed(title=f"Members of System")
        embed.set_author(name=f"{member} ({member.id})", icon_url=member.avatar_url)
        await send_member_list(interaction, embed, member_list)

    @app_commands.command()
    @app_commands.checks.has_any_role(*MODERATOR_ROLES)
    @app_commands.check(is_owner)
    async def suspended(self, interaction: discord.Interaction) -> None:
        """
        ADMIN: List suspended members

        param interaction: Discord Interaction
        """
        log.debug("Listing suspended members...")
        c.execute("SELECT * FROM members WHERE member_enabled == 0")
        member_list = c.fetchall()
        embed = discord.Embed(title="Suspended Members")
        await send_member_list(interaction, embed, member_list)
