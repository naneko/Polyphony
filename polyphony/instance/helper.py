import asyncio
import logging
import re
from datetime import datetime, timedelta

import discord
import discord.ext
import requests

from polyphony.helpers.decode_token import decode_token
from polyphony.settings import (
    TOKEN, EMOTE_CACHE_MAX, GUILD_ID,
)

log = logging.getLogger(__name__)

# TODO: Process emotes for editing


class HelperInstance(discord.Client):
    def __init__(
        self,
        **options,
    ):
        super().__init__(**options)
        self.lock = asyncio.Lock()
        self.invisible = False
        self.emote_cache_rate_limit_timeout = datetime.now()
        log.debug(f"Helper initialized")

    async def on_ready(self):
        """Execute on bot initialization with the Discord API."""
        log.debug(f"Helper started as {self.user}")

    async def edit_as(self, message: discord.Message, content, token, files=None):
        await self.wait_until_ready()
        msg = await self.get_channel(message.channel.id).fetch_message(message.id)
        if msg is None:
            log.debug("Helper failed to edit")
            return False
        async with self.lock:
            self.http.token = token
            await msg.edit(content=content, files=files)
            self.http.token = TOKEN
        if not self.invisible:
            await self.change_presence(status=discord.Status.invisible)
        return True

    async def send_as(
        self, message: discord.Message, content, token, files=None, reference=None, emote_cache=None, mention_author=None
    ):
        await self.wait_until_ready()
        chan = self.get_channel(message.channel.id)
        if chan is None:
            log.debug("Helper failed to send")
            return False
        async with self.lock:
            self.http.token = token
            await chan.trigger_typing()

            # TODO: remove excessive emote_cache logging after feature is thoroughly production tested

            async def emote_cache_helper(ch_emote, emote_cache):
                log.debug(ch_emote)
                try:
                    emote_animated = len(re.findall(r'<a', ch_emote)) > 0
                    emote_name = re.findall(r':.+?:', ch_emote)[0][1:-1]
                    emote_id = re.findall(r':\d+>', ch_emote)[0][1:-1]
                    log.debug(f'Checking if {emote_id} (:{emote_name}:) is accessible without cache.')
                    for chk_emote in emote_cache.emojis:
                        if int(emote_id) == chk_emote.id:
                            log.debug(log.debug(f'{emote_id} (:{emote_name}:) is accessible. Skipping...'))
                            return False
                    log.debug(f'Getting emote image {emote_id} (:{emote_name}:)')
                    if emote_animated:
                        log.debug(f'{emote_id} (:{emote_name}:) is animated')
                        emote_image = requests.get(f'https://cdn.discordapp.com/emojis/{emote_id}.gif').content
                    else:
                        log.debug(f'{emote_id} (:{emote_name}:) is not animated')
                        emote_image = requests.get(f'https://cdn.discordapp.com/emojis/{emote_id}.webp').content
                    log.debug(f'Uploading emote {emote_id} (:{emote_name}:)')
                    cached_emote = await emote_cache.create_custom_emoji(name=emote_name,
                                                                         image=emote_image)
                    log.debug(f'{emote_id} (:{emote_name}:) uploaded')
                    return ch_emote, f'<{"a" if emote_animated else ""}:{cached_emote.name}:{cached_emote.id}>', cached_emote
                except discord.Forbidden:
                    log.debug('Polyphony does not have permission to upload emote cache emoji')
                    return False
                except discord.HTTPException as e:
                    log.debug(f'Failed to upload emote cache emoji\n{e}')
                    return False

            # Emote cache
            if self.emote_cache_rate_limit_timeout > datetime.now():
                log.debug('Emote cache rate limited')
                emote_cache = None
            if emote_cache:
                # TODO: Potentially allow user to turn emote cache on and off
                log.debug('Emote cache start')
                emotes = [*set(re.findall(r'<a?:.+?:\d+>', content))]  # Remove duplicates
                task_list = []
                new_emotes = []
                for emote in emotes[0:EMOTE_CACHE_MAX]:
                    task_list.append(emote_cache_helper(emote, emote_cache))

                log.debug('Processing emote cache...')
                try:
                    new_emotes = await asyncio.wait_for(asyncio.gather(*task_list), timeout=3)
                    for emote in new_emotes:
                        if emote:
                            content = content.replace(emote[0], emote[1])

                    log.debug(f'Message after emote cache => {content}')
                except asyncio.TimeoutError:
                    log.debug('DEBUG WARNING: Emote cached timed out. Disabling for 1 minute.')
                    self.emote_cache_rate_limit_timeout = datetime.now() + timedelta(minutes=1)

            await chan.send(content=content, files=files, reference=reference, mention_author=mention_author)

            # Delete emote cache after send
            if emote_cache:
                log.debug('Deleting cached emotes after message send')
                delete_list = []
                for emote in new_emotes:
                    if emote:
                        delete_list.append(emote[2].delete())
                await asyncio.gather(*delete_list)
                log.debug('Emote cache complete')

            self.http.token = TOKEN
        if not self.invisible:
            await self.change_presence(status=discord.Status.invisible)
        return True
