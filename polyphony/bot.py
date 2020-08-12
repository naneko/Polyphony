import logging

import discord
from discord.ext import commands

from .helpers.checks import is_mod
from .helpers.database import init_db, conn
from .helpers.instances import create_member_instance, instances
from .helpers.message_cache import recently_proxied_messages
from .settings import (
    TOKEN,
    DEBUG,
    COMMAND_PREFIX,
    DELETE_LOGS_CHANNEL_ID,
    DELETE_LOGS_USER_ID,
)

log = logging.getLogger(__name__)

# Main Polyhony Bot Instance
bot = commands.Bot(command_prefix=COMMAND_PREFIX)

# Disable default help
bot.remove_command("help")

# Default Cog Extensions to be loaded
init_extensions = ["commands.admin", "commands.user"]

# TODO: Better Help Messages
# TODO: ON_ERROR() handling
# TODO: general polyphony channel logging module
# TODO: Send redirect note on DM
# TODO: Allow setting nickname override that isn't display_name
# TODO: Autoproxy (sync up typing status if possible)

log.info("Polyphony is starting...")

log.info("Starting member initialization...")

# Initialize Database
init_db()

# Start member instances
log.debug("Creating member instances...")
members = conn.execute("SELECT * FROM members WHERE member_enabled == 1").fetchall()
if len(members) == 0:
    log.info("No members found")
for member in members:
    create_member_instance(member)

log.info(f"Member instances created.")


@bot.event
async def on_ready():
    """
    Execute on bot initialization with the Discord API.
    """
    log.info(f"Polyphony ready. Started as {bot.user}.")


# Load extensions
log.debug("Loading default extensions...")
if DEBUG is True:
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
        if DEBUG is True:
            log.info("Reloading Extensions...")
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
            await ctx.send(
                embed=discord.Embed(
                    title="Reload Successful", color=discord.Color.green()
                )
            )
            log.info("Reloading complete.")
        else:
            await ctx.send(
                "Hot loading is not tested, and hence not enabled, for Polyphony outside of DEBUG mode."
            )


@bot.event
async def on_message(msg: discord.Message):
    await bot.process_commands(msg)
    if msg.channel.id == DELETE_LOGS_CHANNEL_ID or msg.author.id == DELETE_LOGS_USER_ID:

        try:
            embed_text = msg.embeds[0].description
        except IndexError:
            return

        for oldmsg in recently_proxied_messages:
            if str(oldmsg.id) in embed_text and not any(
                [str(instance.user.id) in embed_text for instance in instances]
            ):
                log.debug(
                    f"Deleting delete log message {msg.id} (was about {oldmsg.id})"
                )
                await msg.delete()


bot.run(TOKEN)
