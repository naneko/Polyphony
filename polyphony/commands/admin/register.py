import asyncio
import logging
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from polyphony.helpers.checks import is_owner
from polyphony.helpers.database import conn, insert_member
from polyphony.helpers.decode_token import decode_token
from polyphony.helpers.pluralkit import pk_get_member
from polyphony.helpers.views import Confirm
from polyphony.instance.bot import PolyphonyInstance
from polyphony.settings import MODERATOR_ROLES

log = logging.getLogger(__name__)


class Register(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command()
    @app_commands.checks.has_any_role(*MODERATOR_ROLES)
    @app_commands.check(is_owner)
    async def register(
            self,
            interaction: discord.Interaction,
            pluralkit_member_id: str,
            account: discord.Member,
    ):
        """
        Creates a new Polyphony member instance

        :param interaction: Discord Interaction
        :param pluralkit_member_id: PluralKit system or member id
        :param account: Main Account to be extended from
        """

        log_prefix = f'({pluralkit_member_id} to {account.id}) '

        log.debug(log_prefix + "Registering new member...")

        async with interaction.channel.typing():
            # Error: Account is not a user
            if account.bot is True:
                await interaction.response.send_message(embed=discord.Embed(
                    title=':x: Error Registering: Bad Account Pairing',
                    description=f'{account.mention} is a bot user',
                    color=discord.Color.red()
                ))
                return

            # Get available tokens
            token = conn.execute("SELECT * FROM tokens WHERE used == 0").fetchone()

            # Error: No Slots Available
            if not token:
                await interaction.response.send_message(embed=discord.Embed(
                    title=':x: Error Registering: No Slots Available',
                    description=f"No tokens in queue. Run `/tokens` for information on how to add more.",
                    color=discord.Color.red()
                ))
                return

            # Error: Duplicate Registration
            check_duplicate = conn.execute(
                "SELECT * FROM members WHERE pk_member_id == ?",
                [pluralkit_member_id],
            ).fetchone()
            if check_duplicate:
                await interaction.response.send_message(embed=discord.Embed(
                    title=':x: Error Registering: Member Already Registered',
                    description=f"Member ID `{pluralkit_member_id}` is already registered with instance {self.bot.get_user(check_duplicate['id'])}",
                    color=discord.Color.red()
                ))
                return

            # Fetch member from PluralKit
            member = await pk_get_member(pluralkit_member_id)

            # Error: Member not found
            if member is None:
                await interaction.response.send_message(embed=discord.Embed(
                    title=':x: Error Registering: Member ID invalid',
                    description=f"Member ID `{pluralkit_member_id}` was not found",
                    color=discord.Color.red()
                ))
                return

            # Error: Missing PluralKit Data
            if (
                    member["name"] is None
                    or member["avatar_url"] is None
                    or member["proxy_tags"] is None
            ):
                embed = discord.Embed(
                    title=':x: Error Registering: Missing PluralKit Data',
                    color=discord.Color.red()
                ).set_footer(text='Please check the privacy settings on PluralKit')
                if member["name"] is None:
                    embed.description = ":warning: Member is missing a name"
                if member["avatar_url"] is None:
                    embed.description = ":warning: Member is missing an avatar"
                if member["proxy_tags"] is None:
                    embed.description = ":warning: Member is missing proxy tags"
                await interaction.response.send_message(embed=embed)
                return

            # Confirm add
            view = Confirm()
            await interaction.response.send_message(embed=discord.Embed(
                title=f":grey_question: Create member for {account} with member __**{member['name']}**__ (`{member['id']}`)?",
                color=discord.Color.blue()
            ), view=view)
            await view.wait()
            if view.value is None:
                interaction.response.edit_message(embed=discord.Embed(
                    title=':x: Registration timed out',
                    description=f"User took too long to respond",
                    color=discord.Color.red()
                ), view=None)
                return
            elif view.value:
                interaction.response.edit_message(embed=discord.Embed(
                    title=':hourglass: Registering...',
                    description=f"Registering __**{member['name']}**__ (`{member['id']}`) for {account.mention}",
                    color=discord.Color.red()
                ), view=None)
            else:
                interaction.response.edit_message(embed=discord.Embed(
                    title=':x: Cancelled',
                    description=f"Registration of __**{member['name']}**__ (`{member['id']}`) for {account.mention} cancelled by user",
                    color=discord.Color.red()
                ), view=None)
                return

            # Check if user is new to Polyphony
            if (
                    conn.execute(
                        "SELECT * FROM users WHERE id = ?", [account.id]
                    ).fetchone()
                    is None
            ):
                conn.execute("INSERT INTO users VALUES (?, NULL, NULL)", [account.id])
                conn.commit()

            # Insert member into database
            try:
                insert_member(
                    token["token"],
                    member["id"],
                    account.id,
                    decode_token(token["token"]),
                    member["name"],
                    member["display_name"],
                    member["avatar_url"],
                    member["proxy_tags"],
                    member["keep_proxy"],
                    member_enabled=True,
                )

            # Error: Database Error
            except sqlite3.Error as e:
                log.error(e)
                await interaction.response.send_message(embed=discord.Embed(
                    title=':x: Error Registering: Database Error',
                    description=":x: An unknown database error occurred",
                    color=discord.Color.red()
                ))
                return

            # Mark token as used
            conn.execute(
                "UPDATE tokens SET used = 1 WHERE token = ?",
                [token["token"]],
            )
            conn.commit()

            # Create Instance
            instance = PolyphonyInstance(pluralkit_member_id)
            asyncio.run_coroutine_threadsafe(
                instance.start(token["token"]), self.bot.loop
            )
            await instance.wait_until_ready()

            sync_error_text = ""

            # Update Username
            out = await instance.update_username(member["name"])
            if out != 0:
                sync_error_text += f"> {out}\n"

            # Update Avatar URL
            out = await instance.update_avatar(member["avatar_url"])
            if out != 0:
                sync_error_text += f"> {out}\n"

            # Update Nickname
            out = await instance.update_nickname(member["display_name"])
            if out < 0:
                sync_error_text += f"> PluralKit display name must be 32 or fewer in length if you want to use it as a nickname"
            elif out > 0:
                sync_error_text += f"> Nick didn't update on {out} guild(s)\n"

            # Update Roles
            out = await instance.update_default_roles()
            if out:
                sync_error_text += f"> {out}\n"

        # Success State
        slots = conn.execute("SELECT * FROM tokens WHERE used = 0").fetchall()
        embeds = [discord.Embed(
            title=f'white_check_mark: Registered __{member["name"]}__',
            description=f":arrow_forward: **User is {instance.user.mention}**\n"
                        f"*There are now {len(slots)} slots available*\n",
            color=discord.Color.green()
        )]
        if sync_error_text != "":
            embeds.append(discord.Embed(
                title=':warning: Synced instance with errors',
                description=sync_error_text,
                color=discord.Color.gold()
            ))

        await interaction.response.edit_message(embeds=embeds)
        log.info(
            f"{instance.user} ({instance.pk_member_id}): New member instance registered ({len(slots)} slots left)"
        )
        await instance.close()