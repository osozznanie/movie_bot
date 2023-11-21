# Description: Main file for bot logic and handlers (client side)
import asyncio
import logging

import requests
import tmdbsimple as tmdb
from aiogram import Bot
from aiogram import Dispatcher
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, URLInputFile
from tmdbsimple import Discover, Genres
from texts import TEXTS

import api
import config

tmdb.API_KEY = api.TMDB_API_KEY
bot = Bot(config.BOT_TOKEN)
dp = Dispatcher(bot=bot)
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'


# ========================================= Keyboard ========================================= #

kb = [
    [
        types.KeyboardButton(text='/menu'),
        types.KeyboardButton(text='/language')
    ]
]


# ========================================= Client side ========================================= #
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    bot_info = await bot.get_me()

    await message.answer(
        f"<b>Welcome to {bot_info.first_name}.</b>\n 🇬🇧 Please select language \n 🇺🇦 Будь ласка, виберіть мову \n "
        f"🇷🇺 Пожалуйста, выберите язык", reply_markup=language_keyboard(), parse_mode=ParseMode.HTML)


# ========================================= Language =========================================  #
user_languages = {}


@dp.message(Command("language"))
async def cmd_language(message: types.Message):
    language_code = user_languages.get(message.from_user.id, 'en')
    await message.answer(TEXTS[language_code]['select_language'], reply_markup=language_keyboard())


@dp.callback_query(lambda query: query.data.startswith('set_language'))
async def set_language_callback(query: types.CallbackQuery):
    language_code = query.data.split('_')[2]

    select_menu = TEXTS[language_code]['select_menu']

    set_user_language(query.from_user.id, language_code)
    selected_language = TEXTS[language_code]['selected_language']

    await bot.send_message(query.from_user.id, select_menu, reply_markup=menu_keyboard(language_code),
                           parse_mode=ParseMode.HTML)
    await bot.answer_callback_query(query.id, f"Language set to {language_code}")

    await bot.edit_message_reply_markup(query.from_user.id, query.message.message_id)
    await bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.message_id,
                                text=selected_language, parse_mode=ParseMode.HTML)


@dp.callback_query(lambda query: query.data.startswith('menu_option'))
async def set_menu_callback(query: types.CallbackQuery):
    menu_code = query.data.split('_')[2]
    language_code = query.data.split('_')[3]

    select_option_text = TEXTS[language_code]['select_option']

    if menu_code == '1' or menu_code == '2':
        keyboard_markup = submenu_keyboard(language_code)
        await bot.edit_message_text(select_option_text,
                                    chat_id=query.from_user.id,
                                    message_id=query.message.message_id,
                                    reply_markup=keyboard_markup)
    elif menu_code == '3':
        await bot.send_message(query.from_user.id, "You selected the third menu option.")
    elif menu_code == '4':
        await bot.send_message(query.from_user.id, "You selected the fourth menu option.")


@dp.callback_query(lambda query: query.data.startswith('submenu_option'))
async def set_submenu_callback(call):
    submenu_code = call.data.split('_')[2]
    language_code = call.data.split('_')[3]
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    if submenu_code == '1':
        discover = Discover()
        response = discover.movie(language=tmdb_language_code)

        genres_api = Genres()
        genres_response = genres_api.movie_list(language=tmdb_language_code)
        genres = {genre['id']: genre['name'] for genre in genres_response['genres']}

        for movie in response['results'][:4]:
            title = movie['title']
            poster_url = 'https://image.tmdb.org/t/p/w500' + movie['poster_path']
            img = URLInputFile(poster_url)
            vote_average = movie['vote_average']
            genre_names = [genres[genre_id] for genre_id in movie['genre_ids'] if genre_id in genres]

            message_text = get_message_text_for_card_from_TMDB(language_code, title, vote_average, genre_names)

            await bot.send_photo(call.message.chat.id, photo=img, caption=message_text,
                                 parse_mode='HTML')
            await call.answer(show_alert=False)

    elif submenu_code == '2':
        message_text, keyboard_markup = get_rating_mod(language_code)
        await bot.edit_message_text(message_text,
                                    chat_id=call.from_user.id,
                                    message_id=call.message.message_id,
                                    reply_markup=keyboard_markup)
    elif submenu_code == '3':
        print('3')
    elif submenu_code == '4':
        print('4')


async def send_movies(callback_query: types.CallbackQuery, sort_order: str, vote_count: int):
    language_code = callback_query.data.split('_')[3]
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    discover = tmdb.Discover()
    response = discover.movie(sort_by=f'vote_average.{sort_order}', vote_count_gte=vote_count,
                              language=tmdb_language_code)

    genres_api = Genres()
    genres_response = genres_api.movie_list(language=tmdb_language_code)
    genres = {genre['id']: genre['name'] for genre in genres_response['genres']}

    for movie in response['results'][:3]:
        title = movie['title']
        poster_url = 'https://image.tmdb.org/t/p/w500' + movie['poster_path']
        img = URLInputFile(poster_url)

        vote_average = movie['vote_average']
        genre_names = [genres[genre_id] for genre_id in movie['genre_ids'] if genre_id in genres]

        message_text = get_message_text_for_card_from_TMDB(language_code, title, vote_average, genre_names)

        await bot.send_photo(callback_query.message.chat.id, photo=img, caption=message_text,
                             parse_mode='HTML')

    await bot.answer_callback_query(callback_query.id)


@dp.callback_query(lambda c: c.data and c.data.startswith('sort_option_low'))
async def process_callback_low(callback_query: types.CallbackQuery):

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder=get_text(callback_query.data.split('_')[3], 'select_kb_item')
    )

    await send_movies(callback_query, 'asc', 1000)
    await bot.send_message(callback_query.from_user.id, keyboard.input_field_placeholder, reply_markup=keyboard)
    await bot.delete_message(chat_id=callback_query.from_user.id,
                             message_id=callback_query.message.message_id)


@dp.callback_query(lambda c: c.data and c.data.startswith('sort_option_high'))
async def process_callback_high(callback_query: types.CallbackQuery):

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder=get_text(callback_query.data.split('_')[3], 'select_kb_item')
    )
    await send_movies(callback_query, 'desc', 1000)
    await bot.send_message(callback_query.from_user.id, keyboard.input_field_placeholder, reply_markup=keyboard)
    await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)


def get_rating_mod(language_code, text_key_low='starting_low', text_key_high='starting_high',
                   text_key_option='select_option'):
    texts = TEXTS[language_code]
    default_texts = TEXTS['en']

    option_low = texts.get(text_key_low, default_texts[text_key_low])
    option_high = texts.get(text_key_high, default_texts[text_key_high])
    select_option = texts.get(text_key_option, default_texts[text_key_option])

    keyboard = [
        [types.InlineKeyboardButton(text=option_low, callback_data=f'sort_option_low_{language_code}')],
        [types.InlineKeyboardButton(text=option_high, callback_data=f'sort_option_high_{language_code}')],
    ]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return select_option, keyboard_markup


def language_keyboard():
    keyboard = [[types.InlineKeyboardButton(text='🇬🇧 English', callback_data='set_language_en')],
                [types.InlineKeyboardButton(text='🇺🇦 Українська', callback_data='set_language_ua')],
                [types.InlineKeyboardButton(text='🇷🇺 Русский', callback_data='set_language_ru')], ]

    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return keyboard_markup


def menu_keyboard(language_code):
    option_texts = get_text(language_code, 'menu_keyboard')

    keyboard = [
        [
            types.InlineKeyboardButton(text=option_texts[0], callback_data=f'menu_option_1_{language_code}'),
            types.InlineKeyboardButton(text=option_texts[1], callback_data=f'menu_option_2_{language_code}'),
        ],
        [
            types.InlineKeyboardButton(text=option_texts[2], callback_data=f'menu_option_3_{language_code}'),
            types.InlineKeyboardButton(text=option_texts[3], callback_data=f'menu_option_4_{language_code}'),
        ]
    ]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return keyboard_markup


def get_message_text_for_card_from_TMDB(lang, title, vote_average, genre_names):
    title_text = get_text(lang, 'title')
    rating_text = get_text(lang, 'rating')
    genres_text = get_text(lang, 'genres')

    return f'{title_text}: {title}\n{rating_text}: {vote_average}\n{genres_text}: {", ".join(genre_names)}'


def get_text(lang, key):
    return TEXTS.get(lang, TEXTS['en']).get(key, '')


def submenu_keyboard(language_code):
    option_texts = get_text(language_code, 'submenu_keyboard')

    keyboard = [
        [
            types.InlineKeyboardButton(text=option_texts[0], callback_data=f'submenu_option_1_{language_code}'),
            types.InlineKeyboardButton(text=option_texts[1], callback_data=f'submenu_option_2_{language_code}')
        ],
        [
            types.InlineKeyboardButton(text=option_texts[2], callback_data=f'submenu_option_3_{language_code}'),
            types.InlineKeyboardButton(text=option_texts[3], callback_data=f'submenu_option_4_{language_code}')
        ],

    ]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return keyboard_markup


def set_user_language(user_id, language_code):
    user_languages[user_id] = language_code


@dp.callback_query(lambda c: c.data)
async def process_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f"You chose option {callback_query.data}")


# ========================================= Button =========================================  #


# =========================================  Help =========================================  #
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Welcome, please choose your language:")


# =========================================  Menu =========================================  #

@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    user_id = message.from_user.id
    language_code = user_languages.get(user_id, 'en')

    menu_message = TEXTS[language_code]['select_menu']

    await message.answer(menu_message, reply_markup=menu_keyboard(language_code))


# ========================================= Testing and Exception Handling =========================================
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


async def main():
    await testing()


if __name__ == '__main__':
    asyncio.run(main())
