import asyncio
import logging
import sqlite3

import discord
from discord import app_commands
from discord.app_commands import CommandAlreadyRegistered
from discord.ext import commands

# from .helpers.checks import is_owner
from .helpers.database import init_db
from .instance.helper import HelperInstance
from .settings import (
    TOKEN,
    DEBUG,
    COMMAND_PREFIX,
    GUILD_ID,
)

log = logging.getLogger(__name__)


class Polyphony(commands.Bot):
    def __init__(self):
        super().__init__(intents=discord.Intents.all(), command_prefix=COMMAND_PREFIX)

    async def setup_hook(self):
        # Load extensions
        log.debug("Loading extensions...")
        for ext in init_extensions:
            log.debug(f"Loading {ext}...")
            await bot.load_extension(ext, package="polyphony")
        log.debug("Extensions loaded.")

        # Copies global commands over to guild.
        guild_object = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild_object)
        await self.tree.sync(guild=guild_object)


# Main Polyhony Bot Instance
bot = Polyphony()
helper = HelperInstance(intents=discord.Intents.all())

# Default Cog Extensions to be loaded
init_extensions = ["commands", "events"]

# TODO: Better Help System (look at Blimp's)
# TODO: ON_ERROR() handling
# TODO: Autoproxy (sync up typing status if possible)

log.debug("Polyphony is starting...")

# Initialize Database
init_db()


# Initialize Helper Thread Class
class HelperThread:
    def __init__(self):
        self.running = False
        self.thread = None


helper_thread = HelperThread()


@bot.event
async def on_ready():
    """
    Execute on bot initialization with the Discord API.
    """
    log.debug(f"Finishing initialization...")
    if not helper_thread.running:
        log.debug("Starting helper...")
        helper_thread.thread = asyncio.run_coroutine_threadsafe(
            helper.start(TOKEN), bot.loop
        )
        helper_thread.running = True

    # Emote cache cleanup
    log.debug("Cleaning emote cache...")
    guild = bot.get_guild(GUILD_ID)
    if guild:
        for emote in guild.emojis:
            emote = await guild.fetch_emoji(emote.id)
            if emote.user.id == bot.user.id:
                await emote.delete()
    log.debug("Emote cache cleaning complete")


if DEBUG:

    @bot.tree.command()
    # @app_commands.check(is_owner)
    async def reload(interaction: discord.Interaction):
        """
        DEBUG: Reload default extensions

        param interaction: Discord Context
        """
        # TODO: Re-implement accounting for new system
        # TODO: Allow for full bot restart
        log.info("Reloading Extensions...")

        for extension in init_extensions:
            from discord.ext.commands import (
                ExtensionNotLoaded,
                ExtensionNotFound,
                ExtensionFailed,
            )

            try:
                await bot.reload_extension(extension)
                log.debug(f"Reloaded {extension}")
                # await logger.log(f":white_check_mark: Reloaded `{extension}`")
            except (
                ExtensionNotLoaded,
                ExtensionNotFound,
                ExtensionFailed,
                CommandAlreadyRegistered,
            ) as e:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title=":x: Failed to reload",
                        description=e,
                        color=discord.Color.green(),
                    ),
                    ephemeral=True,
                )
                log.error(f"{extension} failed to reload\nError: {e}")

        try:
            log.debug("Re-initializing database")
            v = init_db()
            log.debug(f":white_check_mark: Database Initialized *(Version {v})*")
            # await logger.log(f":white_check_mark: Database Initialized *(Version {v})*")
        except sqlite3.OperationalError as e:
            log.error(f"Database failed to re-initialize (i.e. upgrade)\nError {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=":x: Failed to initialize database",
                    description=e,
                    color=discord.Color.green(),
                ),
                ephemeral=True,
            )

        # await logger.set(
        #     title=":white_check_mark: Reload Complete", color=discord.Color.green()
        # )
        log.info("Reloading complete.")

        await interaction.response.send_message(
            embed=discord.Embed(
                title=":greencheck: Reload complete", color=discord.Color.green()
            ),
            ephemeral=True,
        )


bot.run(TOKEN)
