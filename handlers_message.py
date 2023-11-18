from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command

from keyboards import language_keyboard
from main import bot, dp


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    bot_info = await bot.get_me()
    await message.answer(
        f"<b>Welcome to {bot_info.first_name}.</b>\n 🇬🇧 Please select language \n 🇺🇦 Будь ласка, виберіть мову \n "
        f"🇷🇺 Пожалуйста, выберите язык", reply_markup=language_keyboard(), parse_mode=ParseMode.HTML)


@dp.message(Command("language"))
async def cmd_language(message: types.Message):
    await message.answer("Please select language:", reply_markup=language_keyboard())


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Welcome, please choose your language:")
