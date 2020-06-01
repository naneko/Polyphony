"""
User commands to configure Polyphony
"""
import logging
from typing import List, Literal

import discord
from discord.ext import commands

from helpers.checks import is_polyphony_user

log = logging.getLogger("polyphony." + __name__)


class User(commands.Cog):
    def __init__(self, bot: discord.ext.commands.bot):
        self.bot = bot

    @commands.command()
    @is_polyphony_user()
    async def sync(self, ctx: commands.context):
        """
        Sync system members with PluralKit

        :param ctx: Discord Context
        """
        # TODO: Implement
        await ctx.send("Sync command unimplemented")
        log.warning("Sync command unimplemented")

    @commands.command()
    @is_polyphony_user()
    async def nick(
        self, ctx: commands.context, system_member: discord.Member, *, nickname: str
    ):
        """
        p! nick: Set system member nickname

        :param ctx: Discord Context
        :param system_member: System Member Mention
        :param nickname: Nickname
        """
        # TODO: Implement
        await ctx.send("Nick command unimplemented")
        log.warning("Nick command unimplemented")

    @commands.command()
    @is_polyphony_user(allow_mods=True)
    async def ping(self, ctx: commands.context):
        """
        p! ping: Pings the core bot

        TODO: Also ping all system member instances for the given user

        :param ctx: Discord Context
        """
        await ctx.send(embed=discord.Embed(title=f"Pong ({self.bot.latency} ms)"))

    @commands.command()
    @is_polyphony_user(allow_mods=True)
    async def listroles(self, ctx: commands.context):
        """
        p! listroles: Lists available roles and their IDs

        :param ctx: Discord Context
        """
        # TODO: Implement
        await ctx.send("Listroles command unimplemented")
        log.warning("Listroles command unimplemented")

    @commands.command()
    @is_polyphony_user()
    async def role(
        self,
        ctx: commands.context,
        mode: Literal["add", "remove"],
        system_member: discord.Member,
        *args: List[int],
    ):
        """
        p! role add/remove [system member] [role IDs]: Adds a list of roles based on the ID from p! listroles

        :param ctx: Discord Context
        :param mode: (add/remove) mode
        :param system_member: A system member bot user
        """
        # TODO: Implement
        await ctx.send("Role command unimplemented")
        log.warning("Role command unimplemented")

    @commands.command()
    @is_polyphony_user()
    async def edit(self, ctx: commands.context, *, message: str):
        """
        p! edit [message]: Edits the last message
        
        :param ctx: Discord Context
        :param message: Message Content
        """
        # TODO: Implement
        await ctx.send("Edit command unimplemented")
        log.warning("Edit command unimplemented")

    @commands.command()
    @is_polyphony_user()
    async def editid(
        self, ctx: commands.context, message_id: discord.Message, *, message: str
    ):
        """
        p! editid [message id] [message]: Edits message with ID

        :param ctx: Discord Context
        :param message_id: ID of message to edit
        :param message: Message Content
        """
        # TODO: Implement
        await ctx.send("Editid command unimplemented")
        log.warning("Editid command unimplemented")

    @commands.command(name="del")
    @is_polyphony_user()
    async def delete(self, ctx: commands.context, message_id: discord.Message = None):
        """
        p! del (id): Deletes the last message unless a message ID parameter is provided. Can be run multiple times. n max limited by config.

        :param ctx: Discord Context
        :param message_id: ID of message to delete
        """
        # TODO: Implement
        await ctx.send("Delete command unimplemented")
        log.warning("Delete command unimplemented")


def setup(bot):
    log.debug("User module loaded")
    bot.add_cog(User(bot))


def teardown(bot):
    log.warning("User module unloaded")
