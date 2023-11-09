import asyncio
import logging

from aiogram import Bot
from aiogram import Dispatcher
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.utils import markdown

import config

dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Your welcome!\n U can choose some commands:\n /help - to get help\n /smile - to get smile")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("U can choose some commands:\n /help - to get help\n /smile - to get smile")


@dp.message(Command("smile"))
async def cmd_smile(message: types.Message):
    url = "https://i.pinimg.com/564x/21/d0/16/21d01679d38bcf1f940dc27fb7b850f0.jpg"
    await message.answer(

        text=f"{markdown.hide_link(url)} \n "
             f"{markdown.hbold(':-)')}\n",


        parse_mode=ParseMode.HTML,)


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=config.BOT_TOKEN)
    await dp.start_polling(bot)


# This handler will be called when user sends `/start` command
if __name__ == '__main__':
    asyncio.run(main())

