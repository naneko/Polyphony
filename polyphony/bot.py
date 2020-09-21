import asyncio
import logging
import sqlite3

import discord
from discord.ext import commands

from .helpers.database import init_db, conn
from .helpers.instances import (
    create_member_instance,
    instances,
    update_presence,
    reload_instance_module,
)
from .settings import (
    TOKEN,
    DEBUG,
    COMMAND_PREFIX,
)

log = logging.getLogger(__name__)

# Main Polyhony Bot Instance
bot = commands.Bot(command_prefix=COMMAND_PREFIX)

# Disable default help
bot.remove_command("help")

# Default Cog Extensions to be loaded
init_extensions = ["commands.admin", "commands.user", "commands.debug", "events"]

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


# Init State
class InitState:
    initialized = False


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

    # Create all member instances
    if InitState.initialized is False:
        InitState.initialized = True
        await initialize_members()


async def initialize_members():
    # Start member instances
    log.debug("Initializing member instances...")
    members = conn.execute("SELECT * FROM members WHERE member_enabled == 1").fetchall()
    new_instance_waits = []
    new_instance_presence = []
    if len(members) == 0:
        log.info("No members found")
    for i, member in enumerate(members):
        new_instance = create_member_instance(member)
        new_instance_waits.append(new_instance.wait_until_ready())
        new_instance_presence.append(
            update_presence(
                new_instance, name=bot.get_user(new_instance.main_user_account_id),
            )
        )
        if (i + 1) % 10 == 0 or i + 1 >= len(members):
            log.debug(f"Waiting for batch (Continue on {i + 1}/{len(members)})")
            await asyncio.gather(*new_instance_waits)
            await asyncio.gather(*new_instance_presence)
            new_instance_waits = []
            new_instance_presence = []
            log.debug(f"Next batch...")
            log.info(f"{i + 1}/{len(members)} MEMBERS READY")
    log.info("Checking for invalid states")
    state_check = []
    for instance in instances:
        state_check.append(instance.check_for_invalid_states())
        await asyncio.gather(*state_check)
    log.info(f"[ALL MEMBER INSTANCES READY]")


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

        if reload_all == "all":
            await msg.edit(
                embed=discord.Embed(
                    title="Reloading instances with updated module...",
                    description="Shutting down instances...",
                    color=discord.Color.orange(),
                )
            )
            log.info("Reloading instances")
            to_close = []
            for instance in instances:
                to_close.append(instance.close())
                instances.remove(instance)
            await asyncio.gather(*to_close)
            await msg.edit(
                embed=discord.Embed(
                    title="Reloading instances with updated module...",
                    description="Reloading instance module...",
                    color=discord.Color.orange(),
                )
            )
            reload_instance_module()
            await msg.edit(
                embed=discord.Embed(
                    title="Reloading instances with updated module...",
                    description="Restarting member instances...",
                    color=discord.Color.orange(),
                )
            )
            await initialize_members()
            for instance in instances:
                await msg.edit(
                    embed=discord.Embed(
                        title="Reloading instances with updated module...",
                        description=f"Restarting member instances...\nWaiting on {instance.member_name}...",
                        color=discord.Color.orange(),
                    )
                )
                await instance.wait_until_ready()
                await update_presence(instance, name=bot.get_user(instance.user.id))
            log.info("Instances reloaded")

        await msg.delete()
        await ctx.send(
            embed=discord.Embed(title="Reload Successful", color=discord.Color.green())
        )
        log.info("Reloading complete.")


bot.run(TOKEN)
