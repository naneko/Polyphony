import asyncio
import logging
import sqlite3

import discord
from discord.ext import commands

from .helpers.database import init_db
from .helpers.log_message import LogMessage
from .instance.helper import HelperInstance
from .settings import (
    TOKEN,
    DEBUG,
    COMMAND_PREFIX,
)

log = logging.getLogger(__name__)

# Main Polyhony Bot Instance
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)
helper = HelperInstance(intents=intents)

# Disable default help
bot.remove_command("help")

# Default Cog Extensions to be loaded
init_extensions = ["commands.admin", "commands.user", "commands.debug", "events"]

# TODO: Better Help System (look at Blimp's)
# TODO: ON_ERROR() handling
# TODO: Autoproxy (sync up typing status if possible)

log.info("Polyphony is starting...")

# Initialize Database
init_db()

# Load extensions
log.debug("Loading default extensions...")
if DEBUG is True:
    log.info("=== DEBUG MODE ENABLED ===")
    # init_extensions.append("commands.debug")

for ext in init_extensions:
    log.debug(f"Loading {ext}...")
    bot.load_extension(ext)
log.debug("Default extensions loaded.")


class HelperRunning:
    def __init__(self):
        self.running = False


helper_running = HelperRunning()


@bot.event
async def on_ready():
    """
    Execute on bot initialization with the Discord API.
    """
    log.info(f"Finishing initialization...")
    if not helper_running.running:
        log.debug("Starting helper...")
        asyncio.run_coroutine_threadsafe(helper.start(TOKEN), bot.loop)
        helper_running.running = True


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
                bot.reload_extension(extension)
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
