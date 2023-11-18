import asyncio
import logging

from aiogram import Bot
from aiogram import Dispatcher

import config

bot = Bot(config.BOT_TOKEN)
dp = Dispatcher(bot=bot)

from config import TMDB_API_KEY
from handlers_message import *
from handlers_callback_query import *
from keyboards import *


async def main():
    global bot
    try:
        logging.basicConfig(level=logging.INFO)

        bot = Bot(token=config.BOT_TOKEN)
        polling_task = asyncio.create_task(dp.start_polling(bot))
        await polling_task
    except Exception as e:
        logging.exception("An error occurred:")
    finally:
        logging.info("Bot stopped.")


if __name__ == '__main__':
    asyncio.run(main())
