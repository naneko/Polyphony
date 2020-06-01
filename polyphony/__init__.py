"""
Polyphony: A more robust version of PluralKit.

Created for The Valley discord server
"""
import logging
import sqlite3
import threading
from typing import List

import discord
from discord.ext import commands

from instance import PolyphonyInstance
from helpers.database import get_members, init_db
from settings import TOKEN, DEBUG

log = logging.getLogger(__name__)

# List of Instance Threads
instances: List[dict] = []

# Main Polyhony Bot Instance
bot = commands.Bot(command_prefix="p! ")

# Default Cog Extensions to be loaded
init_extensions = ["commands.admin", "commands.user"]


@bot.event
async def on_ready():
    """
    Execute on bot initialization with the Discord API.
    """

    # Initialize Database
    init_db()

    # Start member instances
    log.debug("Initializing member instances...")
    members = get_members()
    if len(members) == 0:
        log.debug("No members found")
    for member in members:
        create_member_instance(member)
    log.debug("Member initialization complete.")

    log.info(f"Polyphony started as {bot.user}")


def create_member_instance(member: sqlite3.Row):
    """
    Create member instance threads from dictionary that is returned from database
    :param member: directory that is returned from database functions
    """
    if not dict(member).get("member_enabled"):
        pass
    new_instance = PolyphonyInstance(dict(member))
    thread = threading.Thread(
        target=new_instance.run, args=[dict(member).get("token")], daemon=True
    )
    instances.append({"thread": thread, "instance": member})
    thread.start()


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
async def reload(ctx: commands.context):
    """
    Reload default extensions (cogs) for DEBUG mode

    :param ctx: Discord Context
    """
    if DEBUG:
        log.info("Reloading Extensions...")
        for ext in init_extensions:
            bot.reload_extension(ext)
            log.debug(f"{ext} reloaded")
        await ctx.send(
            embed=discord.Embed(title="Reload Successful", color=discord.Color.green())
        )
        log.info("Reloading complete.")
    else:
        ctx.send(
            "Hot loading is not tested, and hence not enabled, for Polyphony outside of DEBUG mode."
        )


bot.run(TOKEN)
