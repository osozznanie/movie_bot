# Description: Main file for bot logic and handlers (client side)
import asyncio
import logging
import random

import requests
import tmdbsimple as tmdb
from aiogram import Bot
from aiogram import Dispatcher
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, URLInputFile
from tmdbsimple import Discover, Genres, Movies
from texts import TEXTS

import api
import config

tmdb.API_KEY = api.TMDB_API_KEY
bot = Bot(config.BOT_TOKEN)
dp = Dispatcher(bot=bot)
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'
shown_movies = set()

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
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    select_option_text = get_text(language_code, 'select_option')

    if menu_code == '1' or menu_code == '2':
        keyboard_markup = submenu_keyboard(tmdb_language_code)
        await bot.edit_message_text(select_option_text,
                                    chat_id=query.from_user.id,
                                    message_id=query.message.message_id,
                                    reply_markup=keyboard_markup)
    elif menu_code == '3':
        movies = tmdb.Movies()
        popular_movies = movies.popular()
        random_movie = random.choice(popular_movies['results'])

        movie = tmdb.Movies(random_movie['id'])
        movie_info = movie.info(language=tmdb_language_code)

        title = movie_info['title']
        poster_url = 'https://image.tmdb.org/t/p/w500' + movie_info['poster_path']
        img = URLInputFile(poster_url)
        vote_average = movie_info['vote_average']
        genre_names = [genre['name'] for genre in movie_info['genres']]

        message_text = get_message_text_for_card_from_TMDB(language_code, title, vote_average, genre_names)

        another_button = types.InlineKeyboardButton(text="Another", callback_data='another_random')
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[another_button]])

        await bot.send_photo(chat_id=query.from_user.id,
                             photo=img,
                             caption=message_text,
                             reply_markup=keyboard,
                             parse_mode='HTML')
        await query.answer(show_alert=False)
    elif menu_code == '4':
        await bot.send_message(query.from_user.id, "You selected the fourth menu option.")


@dp.callback_query(lambda query: query.data.startswith('another_random'))
async def show_another_random_movie(query: types.CallbackQuery):
    language_code = user_languages.get(query.from_user.id, 'en')
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    discover = Discover()
    page = 1
    unshown_movies = []

    while not unshown_movies and page <= 100:
        response = discover.movie(vote_count_gte=1000, vote_average_gte=5,
                                  language=tmdb_language_code, page=page)

        if not response['results']:
            await bot.send_message(query.from_user.id, "No movies found that meet the criteria.")
            return

        unshown_movies = [movie for movie in response['results'] if movie['id'] not in shown_movies]
        page += 1

    if not unshown_movies:
        await bot.send_message(query.from_user.id, "No more movies left that meet the criteria.")
        return

    random_movie = random.choice(unshown_movies)

    movie = tmdb.Movies(random_movie['id'])
    movie_info = movie.info(language=tmdb_language_code)

    title = movie_info['title']
    poster_url = 'https://image.tmdb.org/t/p/w500' + movie_info['poster_path']
    img = URLInputFile(poster_url)
    vote_average = movie_info['vote_average']
    genre_names = [genre['name'] for genre in movie_info['genres']]

    message_text = get_message_text_for_card_from_TMDB(language_code, title, vote_average, genre_names)

    another_button = types.InlineKeyboardButton(text="Another", callback_data='another_random')
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[another_button]])

    shown_movies.add(movie_info['id'])

    await bot.send_photo(chat_id=query.from_user.id,
                         photo=img,
                         caption=message_text,
                         reply_markup=keyboard,
                         parse_mode='HTML')
    await query.answer(show_alert=False)


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
        page = 0
        genres_api = Genres()
        genres_response = genres_api.movie_list(language=tmdb_language_code)
        genres = {genre['id']: genre['name'] for genre in genres_response['genres']}

        keyboard = [
            [types.InlineKeyboardButton(text=genre_name, callback_data=f'filter_genre_{genre_id}_{language_code}')]
            for genre_id, genre_name in get_genres_page(genres, page)
        ]

        if len(genres) > GENRES_PER_PAGE:
            keyboard.append([
                types.InlineKeyboardButton(text='<<', callback_data=f'prev_page_{page}_{language_code}'),
                types.InlineKeyboardButton(text='>>', callback_data=f'next_page_{page}_{language_code}')
            ])

        keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

        message_text = get_text(language_code, 'select_genre')
        await bot.edit_message_text(message_text,
                                    chat_id=call.from_user.id,
                                    message_id=call.message.message_id,
                                    reply_markup=keyboard_markup)


GENRES_PER_PAGE = 5


def get_genres_page(genres, page):
    start = page * GENRES_PER_PAGE
    end = start + GENRES_PER_PAGE
    return list(genres.items())[start:end]


@dp.callback_query(lambda query: query.data.startswith('next_page') or query.data.startswith('prev_page'))
async def navigate_pages(call):
    action, _, page, *language_code = call.data.split('_')
    page = int(page)
    language_code = '_'.join(language_code)

    genres_api = Genres()
    genres_response = genres_api.movie_list(language=get_text(language_code, 'LANGUAGE_CODES'))
    genres = {genre['id']: genre['name'] for genre in genres_response['genres']}

    if action == 'next_page':
        if page < len(genres) // GENRES_PER_PAGE:
            page += 1
        else:
            return
    elif action == 'prev_page':
        if page > 0:
            page -= 1
        else:
            return

    # Now update the keyboard to show the new page
    keyboard = [
        [types.InlineKeyboardButton(text=genre_name, callback_data=f'filter_genre_{genre_id}_{language_code}')]
        for genre_id, genre_name in get_genres_page(genres, page)
    ]

    if len(genres) > GENRES_PER_PAGE:
        keyboard.append([
            types.InlineKeyboardButton(text='<<', callback_data=f'prev_page_{page}_{language_code}'),
            types.InlineKeyboardButton(text='>>', callback_data=f'next_page_{page}_{language_code}')
        ])

    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    await bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                        reply_markup=keyboard_markup)


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
        [types.InlineKeyboardButton(text=option_texts[0], callback_data=f'submenu_option_1_{language_code}')],
        [types.InlineKeyboardButton(text=option_texts[1], callback_data=f'submenu_option_2_{language_code}')],
        [types.InlineKeyboardButton(text=option_texts[2], callback_data=f'submenu_option_3_{language_code}')],

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
