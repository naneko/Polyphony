import logging

import discord
from discord.ext import commands

from .helpers.checks import is_mod
from .helpers.database import init_db, get_enabled_members
from .helpers.helpers import create_member_instance
from .settings import TOKEN, DEBUG

log = logging.getLogger(__name__)

# Main Polyhony Bot Instance
bot = commands.Bot(command_prefix=";;")

# Default Cog Extensions to be loaded
init_extensions = ["commands.admin", "commands.user"]

# TODO: Help Messages
# TODO: ON_ERROR() handling to log to channel
# TODO: general polyphony channel logging module
# TODO: Send note on DM
# TODO: Allow setting nickname override that isn't display_name
# TODO: Autoproxy (sync up typing status if possible)


@bot.event
async def on_ready():
    """
    Execute on bot initialization with the Discord API.
    """

    # Initialize Database
    init_db()

    # Start member instances
    log.debug("Initializing member instances...")
    members = get_enabled_members()
    if len(members) == 0:
        log.debug("No members found")
    for member in members:
        create_member_instance(member)
    log.debug(f"Member initialization complete.")

    log.info(f"Polyphony started as {bot.user}")


# Load extensions
log.debug("Loading default extensions...")
if DEBUG:
    log.info("=== DEBUG MODE ENABLED ===")
    init_extensions.append("commands.debug")
for ext in init_extensions:
    log.debug(f"Loading {ext}...")
    bot.load_extension(ext)
log.debug("Default extensions loaded.")


@bot.command()
@is_mod()
async def reload(ctx: commands.context):
    """
    Reload default extensions (cogs) for DEBUG mode

    :param ctx: Discord Context
    """
    # TODO: Restart Instances
    async with ctx.channel.typing():
        if DEBUG:
            log.info("Reloading Extensions...")
            for extension in init_extensions:
                from discord.ext.commands import (
                    ExtensionNotLoaded,
                    ExtensionNotFound,
                    ExtensionFailed,
                )

                try:
                    bot.reload_extension(extension)
                except (
                    ExtensionNotLoaded,
                    ExtensionNotFound,
                    ExtensionFailed,
                ) as e:
                    log.exception(e)
                    await ctx.send(
                        embed=discord.Embed(
                            title=f"Module {extension} failed to reload",
                            color=discord.Color.red(),
                        )
                    )
                log.debug(f"{extension} reloaded")
            await ctx.send(
                embed=discord.Embed(
                    title="Reload Successful", color=discord.Color.green()
                )
            )
            log.info("Reloading complete.")
        else:
            ctx.send(
                "Hot loading is not tested, and hence not enabled, for Polyphony outside of DEBUG mode."
            )


bot.run(TOKEN)
