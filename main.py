# Description: Main file for bot logic and handlers (client side)
import asyncio
import logging
import os
import random

import psycopg2
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
shown_movies = set()

# ========================================= Variable for filters ========================================= #
genre_names_filter = {}
# --------------
user_genre_choice = {}
user_release_date_choice = {}
user_vote_count_choice = {}
user_rating_choice = {}


# ========================================= Print =========================================  #
def print_info(message):
    print(f"[INFO] {message}")


# ========================================= Keyboard ========================================= #

kb = [
    [
        types.KeyboardButton(text='menu'),
        types.KeyboardButton(text='language')
    ],
    [
        types.KeyboardButton(text='saved'),
    ]
]


# ========================================= Handler for menu keyboard ========================================= #

@dp.message(lambda message: message.text.lower() == 'menu')
async def menu_command(message: types.Message):
    await cmd_menu(message)


@dp.message(lambda message: message.text.lower() == 'language')
async def language_command(message: types.Message):
    await cmd_language(message)


# ========================================= DataBase ========================================= #
async def setup_database():
    global connection
    connection = psycopg2.connect(
        host=config.host,
        database=os.getenv("db_name"),
        password=os.getenv("db_pass"),
        user=os.getenv("db_user"),
        port=os.getenv("db_port")
    )
    connection.autocommit = True

    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        print("Server version:", cursor.fetchone())

    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "user_id SERIAL PRIMARY KEY, "
            "username VARCHAR(32) NOT NULL, "
            "language VARCHAR(5), "
            " reg_date DATE, "
            "update_date DATE);")
        print("Table 'users' created successfully")

    with connection.cursor() as cursor:
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS saved_movies ("
            "user_id INT, "
            "movie_id INT, "
            "PRIMARY KEY (user_id, movie_id));")
        print("Table 'saved_movies' created successfully")


def get_user_language_from_db(user_id):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT language FROM users WHERE user_id = %s;",
            (user_id,)
        )
        result = cursor.fetchone()
        if result is not None:
            return result[0]
        else:
            return None


def get_saved_movies_from_db(user_id):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM saved_movies WHERE user_id = %s;",
            (user_id,)
        )
        return cursor.fetchall()


def update_user_language_from_db(user_id, username, language):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (user_id, username, language, reg_date, update_date) "
            "VALUES (%s, %s, %s, CURRENT_DATE, CURRENT_DATE) "
            "ON CONFLICT (user_id) DO UPDATE SET language = %s, update_date = CURRENT_DATE;",
            (user_id, username, language, language)
        )


def save_movie_to_db(user_id, movie_id):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO saved_movies (user_id, movie_id) "
            "VALUES (%s, %s) "
            "ON CONFLICT (user_id, movie_id) DO NOTHING;",
            (user_id, movie_id)
        )


def delete_movie_from_db(user_id, movie_id):
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM saved_movies WHERE user_id = %s AND movie_id = %s;",
            (user_id, movie_id)
        )


# ========================================= Client side ========================================= #
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    bot_info = await bot.get_me()
    user_id = message.from_user.id

    user_language = get_user_language_from_db(user_id)

    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
    )

    if user_language:
        await message.answer(
            f"You have set your language to <b>{user_language}</b>. If you want to change it, use the language button.",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            f"<b>Welcome to {bot_info.first_name}.</b>\n 🇬🇧 Please select language \n 🇺🇦 Будь ласка, виберіть мову \n "
            f"🇷🇺 Пожалуйста, выберите язык", reply_markup=language_keyboard(), parse_mode=ParseMode.HTML
        )


# ========================================= Language =========================================  #
user_languages = {}


@dp.message(Command("language"))
async def cmd_language(message: types.Message):
    language_code = get_user_language_from_db(message.from_user.id)
    print_info(f"User {message.from_user.id} chose language {language_code} = cmd_language")
    await message.answer(TEXTS[language_code]['select_language'], reply_markup=language_keyboard())


@dp.callback_query(lambda query: query.data.startswith('set_language'))
async def set_language_callback(query: types.CallbackQuery):
    language_code = query.data.split('_')[2]

    user_id = query.from_user.id
    username = query.from_user.username
    language = language_code

    update_user_language_from_db(user_id, username, language)
    print_info(f"User {user_id} chose language {language_code} = set_language_callback")
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
    language_code = get_user_language_from_db(query.from_user.id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    select_option_text = get_text(language_code, 'select_option')

    print_info(f"User {query.from_user.id} chose menu option {menu_code} = set_menu_callback")

    if menu_code == '1' or menu_code == '2':
        keyboard_markup = submenu_keyboard(language_code)
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
        await send_option_message(query, language_code, select_option_text)


@dp.callback_query(lambda query: query.data.startswith('another_random'))
async def show_another_random_movie(query: types.CallbackQuery):
    language_code = get_user_language_from_db(query.from_user.id)
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

    # await bot.send_photo(chat_id=query.from_user.id,
    #                      photo=img,
    #                      caption=message_text,
    #                      reply_markup=keyboard,
    #                      parse_mode='HTML')
    await query.message.edit_media(media=img, reply_markup=keyboard)
    await query.message.edit_text(text=message_text, reply_markup=keyboard, parse_mode='HTML')
    await query.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('submenu_option'))
async def set_submenu_callback(call):
    submenu_code = call.data.split('_')[2]
    language_code = get_user_language_from_db(call.from_user.id)
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

            keyboard = create_keyboard(movie["id"], language_code, 'save')

            await bot.send_photo(call.message.chat.id, photo=img, caption=message_text,
                                 parse_mode='HTML', reply_markup=keyboard)
            await call.answer(show_alert=False)

    elif submenu_code == '2':
        message_text, keyboard_markup = get_rating_mod(language_code)
        await bot.edit_message_text(message_text,
                                    chat_id=call.from_user.id,
                                    message_id=call.message.message_id,
                                    reply_markup=keyboard_markup)
    elif submenu_code == '3':
        message_text, keyboard_markup = generate_filter_submenu(language_code)
        await bot.edit_message_text(text=message_text,
                                    chat_id=call.from_user.id,
                                    message_id=call.message.message_id,
                                    reply_markup=keyboard_markup)


@dp.callback_query(lambda c: c.data.startswith('save_'))
async def process_callback_save(callback_query: types.CallbackQuery):
    movie_id = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id

    save_movie_to_db(user_id, movie_id)

    save_text = get_text(get_user_language_from_db(user_id), 'save')
    await bot.answer_callback_query(callback_query.id, save_text)


def generate_filter_submenu(language_code):
    submenu_texts = get_text(language_code, 'filter_submenu')

    text = get_text(language_code, 'select_option')
    buttons = [
        [
            InlineKeyboardButton(text=submenu_texts[0], callback_data=f'filter_genre_{language_code}'),
            InlineKeyboardButton(text=submenu_texts[1], callback_data=f'filter_releaseDate_{language_code}')
        ],
        [
            InlineKeyboardButton(text=submenu_texts[2], callback_data=f'filter_voteCount_{language_code}'),
            InlineKeyboardButton(text=submenu_texts[3], callback_data=f'filter_rating_{language_code}')
        ],
        [
            InlineKeyboardButton(text=submenu_texts[4], callback_data=f'filter_search_{language_code}'),
            InlineKeyboardButton(text=submenu_texts[5], callback_data=f'filter_back_{language_code}')
        ]
    ]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard_markup


@dp.callback_query(lambda query: query.data.startswith('filter_genre_'))
async def process_callback_filter_genre(call: types.CallbackQuery):
    language_code = get_user_language_from_db(call.from_user.id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    genres_api = Genres()
    genres_response = genres_api.movie_list(language=tmdb_language_code)
    genre_names_filter[call.from_user.id] = {genre['id']: genre['name'] for genre in genres_response['genres']}

    logging.info(f"genre_names_filter: {genre_names_filter}")

    await generate_genre_submenu(call, tmdb_language_code)


@dp.callback_query(lambda query: query.data.startswith('genre_'))
async def process_callback_genre(call: types.CallbackQuery):
    chosen_genre_id = int(call.data.split('_')[1])

    if call.from_user.id in genre_names_filter:
        chosen_genre_name = genre_names_filter[call.from_user.id].get(chosen_genre_id, "Unknown genre")
    else:
        chosen_genre_name = "Unknown genre"

    user_genre_choice[call.from_user.id] = chosen_genre_id

    language_code = get_user_language_from_db(call.from_user.id)
    message_text, keyboard_markup = generate_filter_submenu(language_code)
    await bot.send_message(call.from_user.id, f"You chose genre {chosen_genre_name}")
    await bot.edit_message_text(text=message_text,
                                chat_id=call.from_user.id,
                                message_id=call.message.message_id,
                                reply_markup=keyboard_markup)
    await bot.send_message(call.from_user.id, f"Вы выбрали жанр, вы можете добавить еще "
                                              f"фильтры или нажать 'Поск' для "
                                              f"получения результата")
    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('filter_releaseDate_'))
async def process_callback_filter_release_date(call: types.CallbackQuery):
    language_code = get_user_language_from_db(call.from_user.id)
    release_date_keyboard = [
        [
            InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][0],
                                 callback_data=f'release_date_before_1980_{language_code}'),
            InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][1],
                                 callback_data=f'release_date_1980_2000_{language_code}')
        ],
        [
            InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][2],
                                 callback_data=f'release_date_2000_2020_{language_code}'),
            InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][3],
                                 callback_data=f'release_date_after_2020_{language_code}')
        ],
        [
            InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][4],
                                 callback_data=f'release_date_any_{language_code}')
        ]
    ]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=release_date_keyboard)
    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    await bot.send_message(call.from_user.id, get_text(language_code, 'filter_releaseDate_txt'),
                           reply_markup=keyboard_markup)


@dp.callback_query(lambda query: query.data.startswith('release_date_'))
async def process_callback_filter_release_date_choice(call: types.CallbackQuery):
    chosen_release_date_option = call.data

    user_release_date_choice[call.from_user.id] = chosen_release_date_option
    language_code = get_user_language_from_db(call.from_user.id)
    message_text, keyboard_markup = generate_filter_submenu(language_code)
    await bot.send_message(call.from_user.id, f"You chose option {chosen_release_date_option}")

    await bot.edit_message_text(text=message_text,
                                chat_id=call.from_user.id,
                                message_id=call.message.message_id,
                                reply_markup=keyboard_markup)
    await call.answer(show_alert=False)


async def generate_genre_submenu(call, tmdb_language_code):
    genres_api = Genres()
    genres_response = genres_api.movie_list(language=tmdb_language_code)
    genres = {genre['id']: genre['name'] for genre in genres_response['genres']}

    saved_genres = genres

    buttons = [[InlineKeyboardButton(text=genre_name, callback_data=f'genre_{genre_id}')] for genre_id, genre_name in
               saved_genres.items()]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    message_text = get_text(call.data.split('_')[2], 'select_option')
    await bot.edit_message_text(text=message_text,
                                chat_id=call.from_user.id,
                                message_id=call.message.message_id,
                                reply_markup=keyboard_markup)


@dp.callback_query(lambda query: query.data.startswith('filter_search_'))
async def process_search(call: types.CallbackQuery):
    user_id = call.from_user.id

    genre_filter = user_genre_choice.get(user_id)
    release_date_filter = user_release_date_choice.get(user_id)

    if genre_filter is None and release_date_filter is None:
        await bot.send_message(user_id,
                               "Вы не выбрали фильтры для фильма. Пожалуйста, выберите хотя бы один фильтр и попробуйте снова.")
    else:
        if release_date_filter is not None:
            year = release_date_filter.split('_')[2]
            release_date_filter = f'{year}-01-01'

        movies = search_movies(genre_filter, release_date_filter)
        print(movies)
        print(release_date_filter)

        for movie in movies[:2]:
            await format_movie(user_id, movie)

        user_genre_choice[user_id] = None
        user_release_date_choice[user_id] = None

    await call.answer(show_alert=False)


def search_movies(genre_filter, release_date_after):
    discover = tmdb.Discover()
    if genre_filter and release_date_after:
        response = discover.movie(with_genres=genre_filter, primary_release_date_gte=release_date_after)
    elif genre_filter:
        response = discover.movie(with_genres=genre_filter)
    elif release_date_after:
        response = discover.movie(primary_release_date_gte=release_date_after)
    else:
        response = discover.movie()
    print(response)
    return response['results']


async def format_movie(user_id, movie):
    base_url = "https://image.tmdb.org/t/p/w500"
    poster_path = movie['poster_path']
    title = movie['title']
    overview = movie['overview']
    release_date = movie['release_date']
    genre_ids = movie['genre_ids']

    genre_names = get_genre_names(genre_ids)

    text = f"Title: {title}\nOverview: {overview}\nRelease Date: {release_date}\nGenres: {', '.join(genre_names)}"

    await bot.send_photo(chat_id=user_id, photo=URLInputFile(base_url + poster_path), caption=text)


def get_genre_names(genre_ids):
    genres = tmdb.Genres()
    response = genres.movie_list()
    genre_list = response['genres']
    genre_dict = {genre['id']: genre['name'] for genre in genre_list}
    genre_names = [genre_dict[genre_id] for genre_id in genre_ids if genre_id in genre_dict]
    return genre_names


async def send_movies(callback_query: types.CallbackQuery, sort_order: str, vote_count: int):
    language_code = get_user_language_from_db(callback_query.from_user.id)
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

        keyboard = create_keyboard(movie["id"], language_code, 'save')

        await bot.send_photo(callback_query.message.chat.id, photo=img, caption=message_text,
                             parse_mode='HTML', reply_markup=keyboard)

    await bot.answer_callback_query(callback_query.id)


@dp.callback_query(lambda c: c.data and c.data.startswith('sort_option_low'))
async def process_callback_low(callback_query: types.CallbackQuery):
    await send_movies(callback_query, 'asc', 1000)
    await bot.delete_message(chat_id=callback_query.from_user.id,
                             message_id=callback_query.message.message_id)


@dp.callback_query(lambda c: c.data and c.data.startswith('sort_option_high'))
async def process_callback_high(callback_query: types.CallbackQuery):
    await send_movies(callback_query, 'desc', 1000)
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


def get_movie_details_from_tmdb(movie_id, language_code):
    movie = tmdb.Movies(movie_id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')
    response = movie.info(language=tmdb_language_code)

    print_info(f"Movie details: {response}")

    title = response['title']
    poster_path = response['poster_path']
    vote_average = response['vote_average']
    genres = response['genres']

    return title, poster_path, vote_average, genres


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


# ========================================= Saved movies =========================================  #
@dp.callback_query(lambda c: c.data == 'saved_movies')
async def show_saved_movies(call):
    user_id = call.from_user.id
    saved_movies = get_saved_movies_from_db(user_id)
    user_language = get_user_language_from_db(user_id)

    for movie in saved_movies:
        movie_id = movie[1]
        title, poster_path, vote_average, genres = get_movie_details_from_tmdb(movie_id, user_language)

        poster_url = 'https://image.tmdb.org/t/p/w500' + poster_path
        img = URLInputFile(poster_url)
        genre_names = [genre['name'] for genre in genres]

        message_text = get_message_text_for_card_from_TMDB(user_language, title, vote_average, genre_names)

        keyboard = create_keyboard(movie_id, user_language, 'delete')

        await bot.send_photo(call.message.chat.id, photo=img, caption=message_text,
                             parse_mode='HTML', reply_markup=keyboard)
    await call.answer(show_alert=False)


# ========================================= Delete =========================================  #

@dp.callback_query(lambda query: query.data.startswith('delete_'))
async def delete_callback(query: types.CallbackQuery):
    movie_id = query.data.split('_')[1]
    user_id = query.from_user.id

    delete_movie_from_db(user_id, movie_id)

    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)


# ========================================= SubMenu Saved =========================================  #
async def send_option_message(query, language_code, select_option_text):
    movies_text = get_text(language_code, 'movies')
    series_text = get_text(language_code, 'series')
    back_text = get_text(language_code, 'back')

    movies_button = types.InlineKeyboardButton(text=movies_text, callback_data='saved_movies')
    series_button = types.InlineKeyboardButton(text=series_text, callback_data='saved_series')
    back_button = types.InlineKeyboardButton(text=back_text, callback_data='back')

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[movies_button, series_button], [back_button]])

    await bot.send_message(chat_id=query.from_user.id, text=select_option_text, reply_markup=keyboard)


# ========================================= Back =========================================  #
@dp.callback_query(lambda query: query.data == 'back')
async def set_back_callback(query: types.CallbackQuery):
    language_code = get_user_language_from_db(query.from_user.id)

    select_option_text = get_text(language_code, 'select_option')

    print_info(f"User {query.from_user.id} chose back option = set_back_callback")
    await bot.edit_message_text(select_option_text,
                                chat_id=query.from_user.id,
                                message_id=query.message.message_id,
                                reply_markup=menu_keyboard(language_code))


# ========================================= Default Method =========================================  #
def create_keyboard(movie_id, language_code, text_key):
    text = get_text(language_code, text_key)
    button = InlineKeyboardButton(text=text, callback_data=f'{text_key}_{movie_id}')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard


# =========================================  Help =========================================  #
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Welcome, please choose your language:")


# =========================================  Menu =========================================  #
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    user_id = message.from_user.id
    language_code = get_user_language_from_db(user_id)

    menu_message = TEXTS[language_code]['select_menu']

    await message.answer(menu_message, reply_markup=menu_keyboard(language_code))


# =========================================  Saved  =========================================  #

@dp.message(lambda message: message.text.lower() == 'saved')
async def process_saved(message: types.CallbackQuery):
    await cmd_menu(message)


@dp.message(Command("saved"))
async def cmd_menu(message: types.Message):
    user_id = message.from_user.id
    language_code = get_user_language_from_db(user_id)
    select_option_text = get_text(language_code, 'select_option')

    await send_option_message(message, language_code, select_option_text)


# ========================================= Another =========================================  #
@dp.callback_query(lambda c: c.data)
async def process_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f"You chose option {callback_query.data}")


# ========================================= Testing and Exception Handling ========================================= #
async def testing():
    global bot
    try:
        logging.basicConfig(level=logging.INFO)

        await setup_database()

        bot = Bot(token=config.BOT_TOKEN)
        polling_task = asyncio.create_task(dp.start_polling(bot))
        await polling_task
    except Exception as e:
        logging.exception("An error occurred:")
        print(e)
    finally:
        logging.info("Bot stopped.")
        connection.close()
        await bot.close()


async def main():
    await testing()


if __name__ == '__main__':
    asyncio.run(main())
