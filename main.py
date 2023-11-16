# Description: Main file for bot logic and handlers (client side)
import asyncio
import logging

from aiogram import Bot
from aiogram import Dispatcher
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart

import config

bot = Bot(config.BOT_TOKEN)
dp = Dispatcher()


# ========================================= Client side ========================================= #
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    bot_info = await bot.get_me()
    await message.answer(
        f"<b>Welcome to {bot_info.first_name}.</b>\n 🇬🇧 Please select language \n 🇺🇦 Будь ласка, виберіть мову \n "
        f"🇷🇺 Пожалуйста, выберите язык", reply_markup=language_keyboard(), parse_mode=ParseMode.HTML)


# =========================================  Language =========================================  #
def language_keyboard():
    keyboard = [[types.InlineKeyboardButton(text='🇬🇧 English', callback_data='set_language_en')],
                [types.InlineKeyboardButton(text='🇺🇦 Українська', callback_data='set_language_ua')],
                [types.InlineKeyboardButton(text='🇷🇺 Русский', callback_data='set_language_ru')], ]

    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return keyboard_markup


@dp.callback_query(lambda query: query.data.startswith('set_language'))
async def set_language_callback(query: types.CallbackQuery):
    language_code = query.data.split('_')[2]

    set_user_language(query.from_user.id, language_code)

    await query.answer(f"Language set to {language_code}")


def set_user_language(user_id, language_code):
    pass


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Welcome, please choose your language:")


# ========================================= Start ========================================= #
async def testing():
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
        await bot.close()


async def main():
    await testing()


if __name__ == '__main__':
    asyncio.run(main())
