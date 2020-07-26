import collections
import logging

import discord

log = logging.getLogger(__name__)

recently_proxied_messages = collections.deque(maxlen=1)


def new_proxied_message(oldmsg: discord.Message):
    """Add a proxy-causing message to the delete-log cleanup cache."""
    global recently_proxied_messages
    recently_proxied_messages.append(oldmsg)
