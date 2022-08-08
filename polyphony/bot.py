import asyncio
import logging
import sqlite3

import discord
from discord import app_commands
from discord.ext import commands

from .helpers.database import init_db
from .instance.helper import HelperInstance
from .settings import (
    TOKEN,
    DEBUG,
    COMMAND_PREFIX, GUILD_ID,
)

log = logging.getLogger(__name__)


class Polyphony(commands.Bot):
    def __init__(self):
        super().__init__(intents=discord.Intents.all(), command_prefix=COMMAND_PREFIX)

    async def setup_hook(self):
        # This copies the global commands over to your guild.
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
        helper_thread.thread = asyncio.run_coroutine_threadsafe(helper.start(TOKEN), bot.loop)
        helper_thread.running = True

    # Load extensions
    log.debug("Loading extensions...")
    for ext in init_extensions:
        log.debug(f"Loading {ext}...")
        await bot.load_extension(ext, package='polyphony')
    log.debug("Extensions loaded.")

    # Emote cache cleanup
    log.debug("Cleaning emote cache...")
    guild = bot.get_guild(GUILD_ID)
    if guild:
        for emote in guild.emojis:
            emote = await guild.fetch_emoji(emote.id)
            if emote.user.id == bot.user.id:
                await emote.delete()
    log.debug("Emote cache cleaning complete")


@bot.command()
@commands.is_owner()
async def reload(ctx: commands.context):
    """
    Reload default extensions (cogs)

    :param ctx: Discord Context
    """
    # TODO: Re-implement accounting for new system
    # TODO: Allow for full bot restart
    async with ctx.channel.typing():
        log.info(":hourglass: Reloading Extensions...")

        logger = LogMessage(ctx, title="Reloading extensions...")

        for extension in init_extensions:
            from discord.ext.commands import (
                ExtensionNotLoaded,
                ExtensionNotFound,
                ExtensionFailed,
            )

            try:
                await bot.reload_extension(extension)
                await logger.log(f":white_check_mark: Reloaded `{extension}`")
            except (
                    ExtensionNotLoaded,
                    ExtensionNotFound,
                    ExtensionFailed,
            ) as e:
                log.exception(e)
                await logger.log(f":x: Module `{extension}` failed to reload")
            log.debug(f"{extension} reloaded")

        try:
            log.info("Re-initializing database")
            v = init_db()
            await logger.log(f":white_check_mark: Database Initialized *(Version {v})*")
        except sqlite3.OperationalError:
            await logger.log(":x: Database failed to re-initialize (i.e. upgrade)")

        await logger.set(
            title=":white_check_mark: Reload Complete", color=discord.Color.green()
        )
        log.info("Reloading complete.")


bot.run(TOKEN)
