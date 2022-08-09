import asyncio
import logging

from polyphony.bot import helper, helper_thread, bot
from polyphony.settings import TOKEN

log = logging.getLogger(__name__)

async def reset():
    log.warning("Resetting helper thread")
    await helper.logout()
    await helper.close()
    helper.clear()
    helper_thread.running = False
    helper_thread.thread.cancel()
    helper_thread.thread = asyncio.run_coroutine_threadsafe(helper.start(TOKEN), bot.loop)
    helper_thread.running = True
    log.info("Helper thread reset")