"""
Admin commands to configure polyphony
"""
import logging

from discord.ext import commands

log = logging.getLogger("polyphony." + __name__)


class Admin(commands.Cog):
    def __init__(self, bot: commands.bot):
        self.bot = bot

    # TODO: Add unimplemented method definitions


def setup(bot: commands.bot):
    log.debug("Admin module loaded")
    bot.add_cog(Admin(bot))


def teardown(bot):
    log.warning("Admin module unloaded")
