import logging
import sqlite3

import discord
from discord.ext import commands

from .helpers.database import init_db
from .settings import (
    TOKEN,
    DEBUG,
    COMMAND_PREFIX,
)

log = logging.getLogger(__name__)

# Main Polyhony Bot Instance
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# Disable default help
bot.remove_command("help")

# Default Cog Extensions to be loaded
init_extensions = ["commands.admin", "commands.user", "commands.debug", "events"]

# TODO: Better Help System (look at Blimp's)
# TODO: ON_ERROR() handling
# TODO: Autoproxy (sync up typing status if possible)

log.info("Polyphony is starting...")

log.info("Starting member initialization...")

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


@bot.event
async def on_ready():
    """
    Execute on bot initialization with the Discord API.
    """
    log.info(f"[POLYPHONY MAIN BOT READY] Started as {bot.user}")


@bot.command()
@commands.is_owner()
async def reload(ctx: commands.context, reload_all=None):
    """
    Reload default extensions (cogs)

    :param ctx: Discord Context
    """
    # TODO: Restart Instances
    async with ctx.channel.typing():
        log.info("Reloading Extensions...")

        msg = await ctx.send(
            embed=discord.Embed(
                title="Reloading extensions...", color=discord.Color.orange()
            )
        )

        for extension in init_extensions:
            from discord.ext.commands import (
                ExtensionNotLoaded,
                ExtensionNotFound,
                ExtensionFailed,
            )

            try:
                bot.reload_extension(extension)
            except (ExtensionNotLoaded, ExtensionNotFound, ExtensionFailed,) as e:
                log.exception(e)
                await ctx.send(
                    embed=discord.Embed(
                        title=f"Module {extension} failed to reload",
                        color=discord.Color.red(),
                    )
                )
            log.debug(f"{extension} reloaded")

        try:
            log.info("Re-initializing database")
            init_db()
        except sqlite3.OperationalError:
            await ctx.send(
                embed=discord.Embed(
                    title=f"Database failed to re-initialize (i.e. upgrade)",
                    color=discord.Color.red(),
                )
            )

        await msg.delete()
        await ctx.send(
            embed=discord.Embed(title="Reload Successful", color=discord.Color.green())
        )
        log.info("Reloading complete.")


bot.run(TOKEN)
