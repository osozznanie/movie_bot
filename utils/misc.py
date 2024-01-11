import asyncio
import json
import random

import tmdbsimple as tmdb
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, URLInputFile, KeyboardButton
from tmdbsimple import Genres

from db.database import get_user_language_from_db, get_current_popular_by_user_id, update_current_popular, \
    update_current_rating, update_current_page_random, get_current_page_random, get_filters_movie_from_db, \
    get_filters_series_from_db, \
    set_filter_movie_page_movie_by_user_id, \
    get_filter_movie_page_movie_by_user_id, get_filter_series_page_movie_by_user_id, \
    set_filter_series_page_movie_by_user_id, reset_filters_movie, reset_filters_series, get_message_id_from_db, \
    store_message_id_in_db
from main import bot, user_languages
from utils.texts import TEXTS

def create_keyboard(movie_id, language_code, text_key, content_type):
    text = get_text(language_code, text_key)
    button = InlineKeyboardButton(text=text, callback_data=f'{text_key}_{movie_id}_{content_type}')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard


def check_type(content_type):
    if content_type == 'movie':
        return 'movie'
    elif content_type == 'tv':
        return 'tv'
    else:
        raise ValueError("Invalid content_type. Expected 'movie' or 'tv'.")


async def send_next_media(callback_query: types.CallbackQuery, language_code, content_type):
    user_id = callback_query.from_user.id
    current_page, current_movie = get_current_popular_by_user_id(user_id)

    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    if content_type == 'movie':
        media_api = tmdb.Movies()
        response = media_api.popular(language=tmdb_language_code, page=current_page)
    elif content_type == 'tv':
        media_api = tmdb.TV()
        response = media_api.popular(language=tmdb_language_code, page=current_page)
    else:
        raise ValueError("Invalid content_type. Expected 'movie' or 'tv'.")

    genres = get_genres(tmdb_language_code)

    message_text = ""
    index = 1
    for content in response['results'][current_movie:current_movie + 10]:
        content_details = await send_content_details(index, content, content_type, genres, language_code)
        message_text += content_details + "\n\n"
        index += 1

    current_movie += 10
    if current_movie >= len(response['results']):
        current_page += 1
        current_movie = 0

    update_current_popular(user_id, current_page, current_movie)

    message_id = get_message_id_from_db(user_id)
    if message_id is None or message_id == 0:
        sent_message = await bot.send_message(user_id, text=message_text, parse_mode='HTML')
        store_message_id_in_db(user_id, sent_message.message_id)
        await create_keyboard_with_next_button(user_id, language_code, content_type)
    else:
        await bot.edit_message_text(chat_id=user_id, message_id=message_id, text=message_text, parse_mode='HTML')


async def create_keyboard_with_next_button(user_id, language_code, content_type, call_for_next=None,
                                           call_for_back=None):
    if call_for_next is None:
        call_for_next = f'load_next_popular_{content_type}'

    if call_for_back is None:
        call_for_back = f'load_previous_popular_{content_type}'

    next_button_text = get_text(language_code, 'next')
    back_button_text = get_text(language_code, 'back')
    reset_button_text = get_text(language_code, 'reset')

    buttons = [
        [
            types.InlineKeyboardButton(text=back_button_text, callback_data=call_for_back),
            types.InlineKeyboardButton(text=next_button_text, callback_data=call_for_next),
        ],
        [
            types.InlineKeyboardButton(text=reset_button_text, callback_data=f'reset_page_{content_type}')
        ]
    ]

    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=buttons)

    msg_text = get_text(language_code, 'next_movies')
    await bot.send_message(user_id, msg_text, reply_markup=keyboard_markup)


async def send_content_details(index, content, content_type, genres, language_code):
    if index == None:
        index = 1
    title = content['title'] if 'title' in content and content_type == 'movie' else content[
        'name'] if 'name' in content else 'N/A'
    vote_average = content['vote_average'] if 'vote_average' in content else 'N/A'
    genre_names = [genres[genre_id] for genre_id in content['genre_ids'] if genre_id in genres]
    if not genre_names:
        genre_names = ['N/A']

    if content_type == 'movie':
        movie = tmdb.Movies(content['id'])
        details = movie.info()
        runtime = details['runtime']
        additional_info = None
        adult = details['adult'] if 'adult' in details else 'N/A'
    elif content_type == 'tv':
        show = tmdb.TV(content['id'])
        details = show.info()
        runtime = details['episode_run_time'][0] if details['episode_run_time'] else 'N/A'
        additional_info = details['number_of_seasons']
        adult = details['adult'] if 'adult' in details else 'N/A'

    original_title = content['original_title'] if content_type == 'movie' else content['original_name']
    release_date = content['release_date'] if content_type == 'movie' else content['first_air_date']
    overview = content['overview'] if 'overview' in content else 'N/A'
    if len(overview) > 100:
        overview = overview[:100] + '...'

    message_text = get_message_text_for_card_from_TMDB(index, language_code, title, vote_average,
                                                       genre_names,
                                                       release_date.split('-')[0], overview,
                                                       content_type, content['id'])
    if len(message_text) > 1024:
        message_text = message_text[:1021] + '...'

    return message_text or ""


async def reset_movies(call, user_id, chat_id):
    current_page = 1
    current_movie = 0
    current_rating_movie = 0
    current_rating_page = 1
    current_filter_tv_page = 1
    current_filter_tv_movie = 0
    current_filter_movie_page = 1
    current_filter_movie_movie = 0

    update_current_popular(user_id, current_page, current_movie)
    update_current_rating(user_id, current_rating_page, current_rating_movie)
    set_filter_movie_page_movie_by_user_id(user_id, current_filter_movie_page, current_filter_movie_movie)
    set_filter_series_page_movie_by_user_id(user_id, current_filter_tv_page, current_filter_tv_movie)

    await update_current_page_random(user_id, 'current_random_movie_page')

    msg = await bot.send_message(chat_id, get_text(get_user_language_from_db(user_id), 'movie_list_reset'))
    await delete_message_after_delay(5, call.from_user.id, msg.message_id)


async def reset_filters(user_id, chat_id, content_type):
    if content_type == 'movie':
        reset_filters_movie(user_id)
    elif content_type == 'tv':
        reset_filters_series(user_id)
    else:
        raise ValueError("Invalid content_type. Expected 'movie' or 'tv'.")

    message = await bot.send_message(chat_id, get_text(get_user_language_from_db(user_id), 'filters_reset'))
    await delete_message_after_delay(5, chat_id, message.message_id)


def generate_filter_submenu(language_code, content_type="any"):
    submenu_texts = get_text(language_code, 'filter_submenu')

    text = get_text(language_code, 'select_option')
    buttons = [
        [
            InlineKeyboardButton(text=submenu_texts[0], callback_data=f'filter_genre_{content_type}'),
            InlineKeyboardButton(text=submenu_texts[1], callback_data=f'filter_releaseDate_{content_type}')
        ],
        [
            InlineKeyboardButton(text=submenu_texts[2], callback_data=f'filter_voteCount_{content_type}'),
            InlineKeyboardButton(text=submenu_texts[3], callback_data=f'filter_rating_{content_type}')
        ],
        [
            InlineKeyboardButton(text=submenu_texts[4], callback_data=f'filter_search_{content_type}'),
            InlineKeyboardButton(text=submenu_texts[5], callback_data=f'back_{content_type}')
        ],
        [
            InlineKeyboardButton(text=get_text(language_code, 'reset'),
                                 callback_data=f'filter_reset_page_{content_type}')
        ]
    ]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return text, keyboard_markup


async def generate_genre_submenu(call, tmdb_language_code, content_type):
    genres_api = Genres()
    if content_type == 'movie':
        genres_response = genres_api.movie_list(language=tmdb_language_code)
    elif content_type == 'tv':
        genres_response = genres_api.tv_list(language=tmdb_language_code)
    else:
        raise ValueError("Invalid content_type. Expected 'movie' or 'tv'.")

    genres = {genre['id']: genre['name'] for genre in genres_response['genres']}

    buttons_per_row = 2

    genres_items = list(genres.items())
    genre_groups = [genres_items[i:i + buttons_per_row] for i in range(0, len(genres_items), buttons_per_row)]

    buttons = [[InlineKeyboardButton(text=genre_name, callback_data=f'genre_{content_type}_{genre_id}') for
                genre_id, genre_name in group] for group in genre_groups]

    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=buttons)

    message_text = get_text(call.data.split('_')[2], 'select_option')
    await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                reply_markup=keyboard_markup)


def generate_vote_count_submenu(language_code, content_type):
    vote_count_keyboard = [[InlineKeyboardButton(text=TEXTS[language_code]['vote_count_options'][0],
                                                 callback_data=f'vote_count_100-500_{content_type}'),
                            InlineKeyboardButton(text=TEXTS[language_code]['vote_count_options'][1],
                                                 callback_data=f'vote_count_500-1000_{content_type}')], [
                               InlineKeyboardButton(text=TEXTS[language_code]['vote_count_options'][2],
                                                    callback_data=f'vote_count_1000-10000_{content_type}'),
                               InlineKeyboardButton(text=TEXTS[language_code]['vote_count_options'][3],
                                                    callback_data=f'vote_count_100-10000000_{content_type}')]]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=vote_count_keyboard)

    return keyboard_markup


def generate_rating_submenu(language_code, content_type):
    rating_keyboard = [
        [InlineKeyboardButton(text=TEXTS[language_code]['starting_low'],
                              callback_data=f'sort_option_popularity.asc_{content_type}')],
        [InlineKeyboardButton(text=TEXTS[language_code]['starting_high'],
                              callback_data=f'sort_option_popularity.desc_{content_type}')]]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=rating_keyboard)

    return keyboard_markup


def generate_release_date_submenu(language_code, content_type):
    release_date_keyboard = [[InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][0],
                                                   callback_data=f'release_date_1700-1980_{content_type}'),
                              InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][1],
                                                   callback_data=f'release_date_1981-2000_{content_type}')], [
                                 InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][2],
                                                      callback_data=f'release_date_2001-2020_{content_type}'),
                                 InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][3],
                                                      callback_data=f'release_date_2020-2030_{content_type}')], [
                                 InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][4],
                                                      callback_data=f'release_date_1500-2030_{content_type}')]]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=release_date_keyboard)

    return keyboard_markup


def search_movies(genre_filter, start_date, end_date, min_votes, max_votes, rating, language_code, page=1):
    discover = tmdb.Discover()

    if min_votes is None:
        min_votes = 400

    response = discover.movie(with_genres=genre_filter, primary_release_date_gte=start_date,
                              primary_release_date_lte=end_date,
                              vote_count_lte=max_votes, vote_count_gte=min_votes, sort_by=rating,
                              language=language_code, page=page)

    results = response['results']

    return results


def search_tv_shows(genre_filter, start_date, end_date, min_votes, max_votes, rating, language_code, page=1):
    discover = tmdb.Discover()

    if min_votes is None:
        min_votes = 400

    response = discover.tv(with_genres=genre_filter, first_air_date_gte=start_date,
                           first_air_date_lte=end_date,
                           vote_count_lte=max_votes, vote_count_gte=min_votes, sort_by=rating,
                           language=language_code, page=page)

    results = response['results']

    return results


global message_ids
message_ids = []


async def send_next_media_by_rating(callback_query: types.CallbackQuery, sort_order, vote_count, content_type):
    user_id = callback_query.from_user.id
    current_page, current_movie = get_current_popular_by_user_id(user_id)

    language_code = get_user_language_from_db(user_id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    if content_type == 'movie':
        media_api = tmdb.Discover()
        response = media_api.movie(sort_by=f'vote_average.{sort_order}', vote_count_gte=vote_count,
                                   language=tmdb_language_code, page=current_page)
    elif content_type == 'tv':
        media_api = tmdb.Discover()
        response = media_api.tv(sort_by=f'vote_average.{sort_order}', vote_count_gte=vote_count,
                                language=tmdb_language_code, page=current_page)
    else:
        raise ValueError("Invalid content_type. Expected 'movie' or 'tv'.")

    genres = get_genres(tmdb_language_code)

    message_text = ""
    index = 1
    for content in response['results'][current_movie:current_movie + 10]:
        content_details = await send_content_details(index, content, content_type, genres, language_code)
        message_text += content_details + "\n\n"
        index += 1

    current_movie += 10
    if current_movie >= len(response['results']):
        current_page += 1
        current_movie = 0

    update_current_popular(user_id, current_page, current_movie)

    message_id = get_message_id_from_db(user_id)
    if message_id is None or message_id == 0:
        sent_message = await bot.send_message(user_id, text=message_text, parse_mode='HTML')
        store_message_id_in_db(user_id, sent_message.message_id)
    else:
        await bot.edit_message_text(chat_id=user_id, message_id=message_id, text=message_text, parse_mode='HTML')

    await create_keyboard_with_next_button(user_id, language_code, content_type,
                                           f'next_page_rating_{sort_order}_{content_type}',
                                           f'previous_page_rating_{sort_order}_{content_type}')


def get_genres(language_code, content_type='movie'):
    genres_api = tmdb.Genres()

    if content_type == 'movie':
        genres_response = genres_api.movie_list(language=language_code)
    elif content_type == 'tv':
        genres_response = genres_api.tv_list(language=language_code)
    else:
        raise ValueError(f"Invalid content_type: {content_type}")

    genres = {genre['id']: genre['name'] for genre in genres_response['genres']}
    return genres


def get_rating_mod(submenu_code_2, language_code, text_key_low='starting_low', text_key_high='starting_high',
                   text_key_option='select_option'):
    texts = TEXTS[language_code]
    default_texts = TEXTS['en']

    option_low = texts.get(text_key_low, default_texts[text_key_low])
    option_high = texts.get(text_key_high, default_texts[text_key_high])
    select_option = texts.get(text_key_option, default_texts[text_key_option])

    keyboard = [[types.InlineKeyboardButton(text=option_low, callback_data=f'sort_option_low_{submenu_code_2}')],
                [types.InlineKeyboardButton(text=option_high, callback_data=f'sort_option_high_{submenu_code_2}')], ]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return select_option, keyboard_markup


def language_keyboard():
    keyboard = [[types.InlineKeyboardButton(text='🇬🇧 English', callback_data='set_language_en')],
                [types.InlineKeyboardButton(text='🇺🇦 Українська', callback_data='set_language_ua')],
                [types.InlineKeyboardButton(text='🇷🇺 Русский', callback_data='set_language_ru')], ]

    main_keyboard = [
        [KeyboardButton(text='/menu'), KeyboardButton(text='/language')],
        [KeyboardButton(text='/saved')],
    ]

    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    keyboard = types.ReplyKeyboardMarkup(keyboard=main_keyboard, resize_keyboard=True, one_time_keyboard=True,
                                         row_width=2)
    return keyboard, keyboard_markup


async def delete_message_after_delay(delay, chat_id, message_id):
    await asyncio.sleep(delay)
    await bot.delete_message(chat_id, message_id)


def menu_keyboard(language_code):
    option_texts = get_text(language_code, 'menu_keyboard')

    keyboard = [[types.InlineKeyboardButton(text=option_texts[0], callback_data=f'menu_option_1_{language_code}'),
                 types.InlineKeyboardButton(text=option_texts[1], callback_data=f'menu_option_2_{language_code}'), ],
                [types.InlineKeyboardButton(text=option_texts[2], callback_data=f'menu_option_3_{language_code}'),
                 types.InlineKeyboardButton(text=option_texts[3], callback_data=f'menu_option_4_{language_code}'), ]]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return keyboard_markup


def get_message_text_for_card_by_film_id(lang, title, original_title, vote_average, genre_names, release_year, runtime,
                                         overview, content_type, adult=None, additional_info=None, id=None):
    type_text = get_text(lang, 'type')
    release_year_text = get_text(lang, 'release_year')
    runtime_text = get_text(lang, 'runtime')
    genres_text = get_text(lang, 'genres')
    adult_text = get_text(lang, 'adult')
    rating_text = get_text(lang, 'rating_card')

    formatted_genres = ' | '.join(genre_names)

    formatted_adult = get_text(lang, 'yes') if adult is not None and adult else get_text(lang, 'no')
    message_parts = [
        f'<b>{title}</b> (/film{id})\n\n',
        f'<i>{original_title}</i>\n\n',
        f'📺 {type_text}: {get_text(lang, content_type)}\n',
        f'🎥 {release_year_text}: {release_year}\n'
    ]

    if additional_info is not None:
        seasons_text = get_text(lang, 'seasons')
        message_parts.append(f'📅 {seasons_text}: {additional_info}\n')

    message_parts.extend([
        f'⏰ {runtime_text}: {runtime} min.\n',
        f'ℹ️ {genres_text}: {formatted_genres}\n',
        f'🚸 {adult_text}: {formatted_adult}\n',
        f'✅ {rating_text}: {vote_average}/10\n\n'
    ])

    if overview:
        description_text = get_text(lang, 'description')
        message_parts.append(f'<b>{description_text}:</b>\n{overview}')  # Made the description bold

    return ''.join(message_parts)


def get_message_text_for_card_from_TMDB(index, lang, title, vote_average, genre_names, release_year,
                                        overview, content_type, id=None):
    rating_text = get_text(lang, 'rating_card')
    release_year_text = get_text(lang, 'release_year')
    description_text = get_text(lang, 'description')

    formatted_genres = ' | '.join(genre_names)

    if content_type == 'movie':
        msg_text = f'/film{id}'
    else:
        msg_text = f'/tv{id}'

    message_parts = [
        f'{index}. <b> {title} ({msg_text}) </b>\n',
        f'✅ {rating_text}: {vote_average}/10\n',
        f'🎥 {release_year_text}: {release_year}\n',
        f'ℹ️ {formatted_genres}\n'
    ]

    if overview:
        message_parts.append(f'<b>{description_text}</b>:\n{overview}\n')

    message_text = ''.join(message_parts)

    if len(message_text) > 1024:
        message_text = message_text[:1021] + '...'

    return message_text or ""


def get_text(lang, key):
    return TEXTS.get(lang, TEXTS['en']).get(key, '')


def submenu_keyboard(language_code, choose_option_menu):
    option_texts = get_text(language_code, 'submenu_keyboard')

    keyboard = [
        [types.InlineKeyboardButton(text=option_texts[0], callback_data=f'submenu_option_1_{choose_option_menu}')],
        [types.InlineKeyboardButton(text=option_texts[1], callback_data=f'submenu_option_2_{choose_option_menu}')],
        [types.InlineKeyboardButton(text=option_texts[2], callback_data=f'submenu_option_3_{choose_option_menu}')],
        [types.InlineKeyboardButton(text=option_texts[3], callback_data=f'back')]
    ]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return keyboard_markup


def get_movie_details_from_TMDB(movie_id, tmdb_language_code):
    movie = tmdb.Movies(movie_id)
    movie_details = movie.info(language=tmdb_language_code)

    return movie_details


def get_series_details_from_TMDB(series_id, tmdb_language_code):
    series = tmdb.TV(series_id)
    series_details = series.info(language=tmdb_language_code)

    return series_details


def get_media_details_and_format_message(media_id, media_type, lang, tmdb_language_code):
    if media_type == 'movie':
        media_details = get_movie_details_from_TMDB(media_id, tmdb_language_code)
    elif media_type == 'tv':
        media_details = get_series_details_from_TMDB(media_id, tmdb_language_code)
    else:
        raise ValueError("Invalid media type. Expected 'movie' or 'series'.")

    title, original_title, poster_path, vote_average, genre_names, release_year, runtime, adult, overview, additional_info = extract_content_info(
        media_details, media_type)

    message_text = get_message_text_for_card_from_TMDB(lang, title, original_title, vote_average, genre_names,
                                                       release_year, runtime,
                                                       overview, media_type, adult, additional_info, media_id)

    return message_text, poster_path


def set_user_language(user_id, language_code):
    user_languages[user_id] = language_code


async def send_option_message(query, language_code, select_option_text, check=None):
    movies_text = get_text(language_code, 'movies')
    series_text = get_text(language_code, 'series')
    back_text = get_text(language_code, 'back')

    movies_button = types.InlineKeyboardButton(text=movies_text, callback_data='saved_movie')
    series_button = types.InlineKeyboardButton(text=series_text, callback_data='saved_tv')
    back_button = types.InlineKeyboardButton(text=back_text, callback_data='back')

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[movies_button, series_button], [back_button]])

    if check == "kb":
        await bot.send_message(chat_id=query.from_user.id, text=select_option_text, reply_markup=keyboard)
    else:
        await bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.message_id,
                                    text=select_option_text, reply_markup=keyboard)


def extract_content_info(content_info, content_type):
    title = content_info['title'] if content_type == 'movie' else content_info['name']
    original_title = content_info['original_title'] if content_type == 'movie' else content_info['original_name']
    poster_url = 'https://image.tmdb.org/t/p/w500' + content_info['poster_path']
    vote_average = content_info['vote_average']
    genre_names = [genre['name'] for genre in content_info['genres']]
    release_year = content_info['release_date'].split('-')[0] if content_type == 'movie' else \
        content_info['first_air_date'].split('-')[0]
    runtime = content_info['runtime'] if content_type == 'movie' else content_info['episode_run_time'][0] if \
        content_info['episode_run_time'] else 'N/A'
    adult = content_info['adult'] if 'adult' in content_info else 'N/A'
    overview = content_info['overview']
    additional_info = None if content_type == 'movie' else content_info['number_of_seasons']

    return title, original_title, poster_url, vote_average, genre_names, release_year, runtime, adult, overview, additional_info


async def send_content_details_by_content_id(content_id, content_type, call, save=False):
    language_code = get_user_language_from_db(call.from_user.id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    if content_type == 'movie':
        content_info = get_movie_details_from_TMDB(content_id, tmdb_language_code)
    elif content_type == 'tv':
        content_info = get_series_details_from_TMDB(content_id, tmdb_language_code)

    title, original_title, poster_url, vote_average, genre_names, release_year, runtime, adult, overview, additional_info = extract_content_info(
        content_info, content_type)

    message_text = get_message_text_for_card_by_film_id(language_code, title, original_title, vote_average,
                                                        genre_names,
                                                        release_year, runtime, overview, content_type, adult,
                                                        additional_info, content_id)

    if len(message_text) > 1024:
        message_text = message_text[:1021] + '...'

    keyboard = create_keyboard(content_id, language_code, 'save', check_type(content_type))
    if save:
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text=get_text(language_code, 'delete'), callback_data=f'delete_{content_id}')])

    await bot.send_photo(chat_id=call.from_user.id, photo=URLInputFile(poster_url), caption=message_text,
                         reply_markup=keyboard,
                         parse_mode='HTML')


async def send_random_content(query, language_code, tmdb_language_code, content_type, rating):
    if content_type == 'movie':
        random_content = await get_next_movie(query.from_user.id, rating)
        content = tmdb.Movies(random_content['id'])
    else:  # content_type == 'tv'
        random_content = await get_next_tv_show(query.from_user.id, rating)
        content = tmdb.TV(random_content['id'])

    content_info = content.info(language=tmdb_language_code)

    title, original_title, poster_url, vote_average, genre_names, release_year, runtime, adult, overview, additional_info = extract_content_info(
        content_info, content_type)

    message_text = get_message_text_for_card_by_film_id(language_code, title, original_title, vote_average, genre_names,
                                                        release_year, runtime, overview, content_type, adult,
                                                        additional_info, random_content['id'])

    if len(message_text) > 1024:
        message_text = message_text[:1021] + '...'

    keyboard = create_keyboard(random_content["id"], language_code, 'save', check_type(content_type))
    another_button = InlineKeyboardButton(text=get_text(language_code, 'another'),
                                          callback_data=f'another_{content_type}_{rating}')

    keyboard.inline_keyboard.append([another_button])

    if query.message:
        await bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)

    await bot.send_photo(chat_id=query.from_user.id, photo=URLInputFile(poster_url), caption=message_text,
                         reply_markup=keyboard,
                         parse_mode='HTML')

    await query.answer(show_alert=False)


selected_movies = {}
selected_tv_shows = {}
movie_counters = {}
tv_counters = {}


async def get_next_movie(user_id, rating):
    all_movies = await fetch_random_movies(user_id, rating)
    while True:
        movie = random.choice(all_movies)
        if movie['id'] not in selected_movies.get(user_id, set()):
            selected_movies.setdefault(user_id, set()).add(movie['id'])
            movie_counters[user_id] = movie_counters.get(user_id, 0) + 1
            return movie


async def get_next_tv_show(user_id, rating):
    all_tv_shows = await fetch_random_tv_shows(user_id, rating)
    while True:
        tv_show = random.choice(all_tv_shows)
        if tv_show['id'] not in selected_tv_shows.get(user_id, set()):
            selected_tv_shows.setdefault(user_id, set()).add(tv_show['id'])
            tv_counters[user_id] = tv_counters.get(user_id, 0) + 1
            return tv_show


async def fetch_random_movies(user_id, rating):
    current_page = await get_current_page_random(user_id, 'current_random_movie_page')
    all_movies = tmdb.Discover().movie(page=current_page, vote_count_gte=300)['results']
    all_movies = [movie for movie in all_movies if rating[0] <= movie['vote_average'] <= rating[1]]
    random.shuffle(all_movies)
    if movie_counters.get(user_id, 0) >= 5:
        await update_current_page_random(user_id, 'current_random_movie_page')
        movie_counters[user_id] = 0
    return all_movies


async def fetch_random_tv_shows(user_id, rating):
    current_page = await get_current_page_random(user_id, 'current_random_tv_page')
    all_tv_shows = tmdb.Discover().tv(page=current_page, vote_count_gte=300)['results']
    all_tv_shows = [tv_show for tv_show in all_tv_shows if rating[0] <= tv_show['vote_average'] <= rating[1]]
    random.shuffle(all_tv_shows)
    if tv_counters.get(user_id, 0) >= 5:
        await update_current_page_random(user_id, 'current_random_tv_page')
        tv_counters[user_id] = 0
    return all_tv_shows


async def send_next_page_filter(call, language_code, content_type):
    user_id = call.from_user.id
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    filters = get_filters_movie_from_db(user_id) if content_type == 'movie' else get_filters_series_from_db(user_id)

    genre_filter = filters.get('genre')
    release_date_filter = filters.get('release_date')
    user_rating_filter = filters.get('user_rating')
    rating = filters.get('rating')

    if not any([genre_filter, release_date_filter, user_rating_filter, rating]):
        await bot.send_message(user_id, get_text(language_code, 'no_filters'))
        return

    if release_date_filter is not None:
        start_year, end_year = release_date_filter.split('-')
        start_date = f'{start_year}-01-01'
        end_date = f'{end_year}-12-31'
    else:
        start_date = None
        end_date = None

    if user_rating_filter is not None:
        min_votes, max_votes = user_rating_filter.split('-')
    else:
        min_votes = None
        max_votes = None

    current_page, current_movie = get_filter_movie_page_movie_by_user_id(user_id)

    if content_type == 'movie':
        current_page, current_movie = get_filter_movie_page_movie_by_user_id(user_id)
        contents = search_movies(genre_filter, start_date, end_date, min_votes, max_votes, rating, tmdb_language_code,
                                 current_page)

    else:  # content_type == 'tv'
        current_page, current_movie = get_filter_series_page_movie_by_user_id(user_id)
        contents = search_tv_shows(genre_filter, start_date, end_date, min_votes, max_votes, rating, tmdb_language_code,
                                   current_page)

    if not contents:
        msg = await bot.send_message(user_id, get_text(language_code, 'no_results'))
        await delete_message_after_delay(5, user_id, msg.message_id)
        return

    genres = get_genres(tmdb_language_code, content_type=content_type)

    message_text = ""
    index = 1
    for content in contents[current_movie:current_movie + 10]:
        content_details = await send_content_details(index, content, content_type, genres, language_code)
        message_text += content_details + "\n\n"
        index += 1

    current_movie += 10
    if current_movie >= len(contents):
        current_page += 1
        current_movie = 0

    if content_type == 'movie':
        set_filter_movie_page_movie_by_user_id(user_id, current_page, current_movie)
    elif content_type == 'tv':
        set_filter_series_page_movie_by_user_id(user_id, current_page, current_movie)

    message_id = get_message_id_from_db(user_id)
    if not message_id or message_id == 0:
        sent_message = await bot.send_message(user_id, text=message_text, parse_mode='HTML')
        store_message_id_in_db(user_id, sent_message.message_id)
        await create_keyboard_with_next_button(user_id, language_code, content_type, f'next_page_filter_{content_type}', f'previous_page_filter_{content_type}')
    else:
        await bot.edit_message_text(chat_id=user_id, message_id=message_id, text=message_text, parse_mode='HTML')


async def send_previous_page_filter(call, language_code, content_type):
    if content_type == 'movie':
        current_page, current_movie = get_filter_movie_page_movie_by_user_id(call.from_user.id)
    elif content_type == 'tv':
        current_page, current_movie = get_filter_series_page_movie_by_user_id(call.from_user.id)

    if current_page == 1 and current_movie == 10 or current_page == 1 and current_movie == 0:
        msg_text = await bot.send_message(call.from_user.id, get_text(language_code, 'first_page'))
        await delete_message_after_delay(5, msg_text.message_id, call.message.message_id)
        return
    elif current_movie == 0:
        current_page -= 1
        current_movie = 0
    elif current_movie == 10:
        current_page -= 1
        current_movie = 10

    set_filter_movie_page_movie_by_user_id(call.from_user.id, current_page, current_movie)
    await send_next_page_filter(call, language_code, content_type)


async def handle_previous_media(call, language_code, content_type, sort_order=None, vote_count=None):
    current_page, current_movie = get_current_popular_by_user_id(call.from_user.id)

    if current_page == 1 and current_movie == 10 or current_page == 1 and current_movie == 0:
        await call.answer(get_text(language_code, 'first_page'), show_alert=True)
        return
    elif current_movie == 0:
        current_page -= 1
        current_movie = 0
    elif current_movie == 10:
        current_page -= 1
        current_movie = 10
    update_current_popular(call.from_user.id, current_page, current_movie)

    if sort_order is None:
        await send_next_media(call, language_code, content_type)
    else:
        await send_next_media_by_rating(call, sort_order=sort_order, vote_count=vote_count, content_type=content_type)


async def send_previous_media_by_popularity(call, language_code, content_type):
    await handle_previous_media(call, language_code, content_type)


async def send_previous_movies_by_rating_TMDB(call, language_code, sort_order, vote_count, content_type):
    await handle_previous_media(call, language_code, content_type, sort_order, vote_count)


def create_content_choice_keyboard(language_code):
    film_text = get_text(language_code, 'movies')
    series_text = get_text(language_code, 'series')
    film_button = InlineKeyboardButton(text=film_text, callback_data=f'choose_content_movie')
    series_button = InlineKeyboardButton(text=series_text, callback_data=f'choose_content_tv')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[film_button, series_button]])

    return keyboard


def create_rating_choice_keyboard(language_code, content_type):
    low = get_text(language_code, 'any_rating')
    height = get_text(language_code, 'good_rating')
    low_button = InlineKeyboardButton(text=low, callback_data=f'choose_rating_{content_type}_0-10')
    height_button = InlineKeyboardButton(text=height, callback_data=f'choose_rating_{content_type}_6-10')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[low_button], [height_button]])

    return keyboard


def get_movie_genres(language_code):
    genres = tmdb.Genres()
    response = genres.movie_list(language=language_code)
    return response.get('genres', {})


def get_tv_genres(language_code):
    genres = tmdb.Genres()
    response = genres.tv_list(language=language_code)
    return response.get('genres', {})


def get_user_filters(user_id, content_type):
    language_code = get_user_language_from_db(user_id)
    if content_type == 'movie':
        filters = get_filters_movie_from_db(user_id)
        genres = get_movie_genres(get_text(language_code, 'LANGUAGE_CODES'))
    elif content_type == 'tv':
        filters = get_filters_series_from_db(user_id)
        genres = get_tv_genres(get_text(language_code, 'LANGUAGE_CODES'))
    else:
        raise ValueError("Invalid content_type. Expected 'movie' or 'tv'.")

    # Convert list of genres to dictionary for easy lookup
    genres_dict = {genre['id']: genre['name'] for genre in genres}

    year = get_text(language_code, 'year')
    not_indicated = get_text(language_code, 'not_indicated')
    filter_descriptions = []

    rating_text_map = {
        'popularity.desc': get_text(language_code, 'popularity_desc'),
        'popularity.asc': get_text(language_code, 'popularity_asc'),
    }

    filter_keys = ['genre', 'release_date', 'user_rating', 'rating']

    for filter_key in filter_keys:
        filter_value = filters.get(filter_key)
        if filter_key == 'genre':
            genre_name = genres_dict.get(int(filter_value), filter_value) if filter_value else not_indicated
            filter_descriptions.append(f"{get_text(language_code, 'genre')}: {genre_name}")
        elif filter_key == 'release_date':
            date_text = f"{filter_value.split('-')[0]}{year}  - {filter_value.split('-')[1]}{year}" if filter_value else not_indicated
            filter_descriptions.append(f"{get_text(language_code, 'release_date')}: {date_text}")
        elif filter_key == 'user_rating':
            rating_text = filter_value if filter_value and filter_value != '100-10000000' else not_indicated
            filter_descriptions.append(f"{get_text(language_code, 'user_rating')}: {rating_text}")
        elif filter_key == 'rating':
            rating_text = rating_text_map.get(filter_value, filter_value) if filter_value else not_indicated
            filter_descriptions.append(f"{get_text(language_code, 'sort_by_rating')}: {rating_text}")

    filter_text = "\n".join(filter_descriptions)

    return filter_text


def check_filters_exist(user_id, content_type):
    if content_type == 'movie':
        filters = get_filters_movie_from_db(user_id)
    elif content_type == 'tv':
        filters = get_filters_series_from_db(user_id)
    else:
        raise ValueError("Invalid content_type. Expected 'movie' or 'tv'.")

    genre = filters.get('genre')
    release_date = filters.get('release_date')
    user_rating = filters.get('user_rating')
    rating = filters.get('rating')

    if genre or release_date or user_rating or rating:
        return True
    else:
        return False
