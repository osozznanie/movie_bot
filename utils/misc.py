import random

import tmdbsimple as tmdb
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, URLInputFile
from tmdbsimple import Genres

from db.database import get_user_language_from_db
from main import bot, user_languages
from utils.texts import TEXTS

current_page = 1
current_movie = 0


def print_info(message):
    print(f"[INFO] {message}")


def create_keyboard(movie_id, language_code, text_key):
    text = get_text(language_code, text_key)
    button = InlineKeyboardButton(text=text, callback_data=f'{text_key}_{movie_id}')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard


async def send_next_movies(chat_id, language_code):
    global current_page
    global current_movie

    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')
    movies = tmdb.Movies()
    response = movies.popular(language=tmdb_language_code, page=current_page)

    genres_api = Genres()
    genres_response = genres_api.movie_list(language=tmdb_language_code)
    genres = {genre['id']: genre['name'] for genre in genres_response['genres']}

    for movie in response['results'][current_movie:current_movie + 5]:
        title = movie['title']
        poster_url = 'https://image.tmdb.org/t/p/w500' + movie['poster_path']
        img = URLInputFile(poster_url)
        vote_average = movie['vote_average']
        genre_names = [genres[genre_id] for genre_id in movie['genre_ids'] if genre_id in genres]

        message_text = get_message_text_for_card_from_TMDB(language_code, title, vote_average, genre_names)

        keyboard = create_keyboard(movie["id"], language_code, 'save')

        await bot.send_photo(chat_id, photo=img, caption=message_text, parse_mode='HTML', reply_markup=keyboard)

    current_movie += 5
    if current_movie >= len(response['results']):
        current_page += 1
        current_movie = 0

    next_button = types.InlineKeyboardButton(text="Next", callback_data='load_next')
    reset_button = types.InlineKeyboardButton(text="Reset", callback_data='reset_page')
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[next_button, reset_button]])

    await bot.send_message(chat_id, "Click 'Next' to load next 5 movies or 'Reset' to start over",
                           reply_markup=keyboard)


async def reset_movies(chat_id):
    global current_page
    global current_movie

    current_page = 1
    current_movie = 0

    await bot.send_message(chat_id, "The movie list has been reset. Click 'Next' to load the first 5 movies.")


def generate_filter_submenu(language_code):
    submenu_texts = get_text(language_code, 'filter_submenu')

    text = get_text(language_code, 'select_option')
    buttons = [[InlineKeyboardButton(text=submenu_texts[0], callback_data=f'filter_genre_{language_code}'),
                InlineKeyboardButton(text=submenu_texts[1], callback_data=f'filter_releaseDate_{language_code}')],
               [InlineKeyboardButton(text=submenu_texts[2], callback_data=f'filter_voteCount_{language_code}'),
                InlineKeyboardButton(text=submenu_texts[3], callback_data=f'filter_rating_{language_code}')],
               [InlineKeyboardButton(text=submenu_texts[4], callback_data=f'filter_search_{language_code}'),
                InlineKeyboardButton(text=submenu_texts[5], callback_data=f'filter_back_{language_code}')]]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard_markup


async def generate_genre_submenu(call, tmdb_language_code):
    genres_api = Genres()
    genres_response = genres_api.movie_list(language=tmdb_language_code)
    genres = {genre['id']: genre['name'] for genre in genres_response['genres']}

    saved_genres = genres

    buttons = [[InlineKeyboardButton(text=genre_name, callback_data=f'genre_{genre_id}')] for genre_id, genre_name in
               saved_genres.items()]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    message_text = get_text(call.data.split('_')[2], 'select_option')
    await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                reply_markup=keyboard_markup)


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

        await bot.send_photo(callback_query.message.chat.id, photo=img, caption=message_text, parse_mode='HTML',
                             reply_markup=keyboard)

    await bot.answer_callback_query(callback_query.id)


def get_rating_mod(language_code, text_key_low='starting_low', text_key_high='starting_high',
                   text_key_option='select_option'):
    texts = TEXTS[language_code]
    default_texts = TEXTS['en']

    option_low = texts.get(text_key_low, default_texts[text_key_low])
    option_high = texts.get(text_key_high, default_texts[text_key_high])
    select_option = texts.get(text_key_option, default_texts[text_key_option])

    keyboard = [[types.InlineKeyboardButton(text=option_low, callback_data=f'sort_option_low_{language_code}')],
                [types.InlineKeyboardButton(text=option_high, callback_data=f'sort_option_high_{language_code}')], ]
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

    keyboard = [[types.InlineKeyboardButton(text=option_texts[0], callback_data=f'menu_option_1_{language_code}'),
                 types.InlineKeyboardButton(text=option_texts[1], callback_data=f'menu_option_2_{language_code}'), ],
                [types.InlineKeyboardButton(text=option_texts[2], callback_data=f'menu_option_3_{language_code}'),
                 types.InlineKeyboardButton(text=option_texts[3], callback_data=f'menu_option_4_{language_code}'), ]]
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

    keyboard = [[types.InlineKeyboardButton(text=option_texts[0], callback_data=f'submenu_option_1_{language_code}')],
                [types.InlineKeyboardButton(text=option_texts[1], callback_data=f'submenu_option_2_{language_code}')],
                [types.InlineKeyboardButton(text=option_texts[2], callback_data=f'submenu_option_3_{language_code}')],
                [types.InlineKeyboardButton(text=option_texts[3], callback_data=f'back')]
                ]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return keyboard_markup


def set_user_language(user_id, language_code):
    user_languages[user_id] = language_code


async def send_option_message(query, language_code, select_option_text):
    movies_text = get_text(language_code, 'movies')
    series_text = get_text(language_code, 'series')
    back_text = get_text(language_code, 'back')

    movies_button = types.InlineKeyboardButton(text=movies_text, callback_data='saved_movies')
    series_button = types.InlineKeyboardButton(text=series_text, callback_data='saved_series')
    back_button = types.InlineKeyboardButton(text=back_text, callback_data='back')

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[movies_button, series_button], [back_button]])

    await bot.send_message(chat_id=query.from_user.id, text=select_option_text, reply_markup=keyboard)


shown_movies = set()
movies = tmdb.Movies()
page_number = 1


async def get_next_movie():
    global shown_movies
    global page_number

    while True:
        popular_movies = movies.popular(page=page_number)

        unshown_movies = [movie for movie in popular_movies['results'] if movie['id'] not in shown_movies]

        if not unshown_movies:
            shown_movies = set()
            page_number += 1
            continue

        random_movie = random.choice(unshown_movies)
        shown_movies.add(random_movie['id'])

        return random_movie


async def send_random_movie(query, language_code, tmdb_language_code):
    random_movie = await get_next_movie()

    movie = tmdb.Movies(random_movie['id'])
    movie_info = movie.info(language=tmdb_language_code)

    title = movie_info['title']
    poster_url = 'https://image.tmdb.org/t/p/w500' + movie_info['poster_path']
    vote_average = movie_info['vote_average']
    genre_names = [genre['name'] for genre in movie_info['genres']]

    message_text = get_message_text_for_card_from_TMDB(language_code, title, vote_average, genre_names)

    keyboard = create_keyboard(random_movie["id"], language_code, 'save')
    another_button = create_keyboard(random_movie["id"], language_code, 'another')

    keyboard.inline_keyboard.append(another_button.inline_keyboard[0])

    if query.message:
        await bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)

    await bot.send_photo(chat_id=query.from_user.id, photo=URLInputFile(poster_url), caption=message_text,
                         reply_markup=keyboard,
                         parse_mode='HTML')

    await query.answer(show_alert=False)
