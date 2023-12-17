import asyncio
import random

import tmdbsimple as tmdb
from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, URLInputFile
from tmdbsimple import Genres

from db.database import get_user_language_from_db, get_current_popular_by_user_id, update_current_popular, \
    update_current_rating, update_current_page_random, get_current_page_random
from main import bot, user_languages
from utils.texts import TEXTS


def print_info(message):
    print(f"[INFO] {message}")


def create_keyboard(movie_id, language_code, text_key):
    text = get_text(language_code, text_key)
    button = InlineKeyboardButton(text=text, callback_data=f'{text_key}_{movie_id}')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard


async def send_next_media(callback_query: types.CallbackQuery, language_code, content_type):
    current_page, current_movie = get_current_popular_by_user_id(callback_query.from_user.id)

    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    if content_type == 'movie':
        media_api = tmdb.Movies()
        response = media_api.popular(language=tmdb_language_code, page=current_page)
    elif content_type == 'tv':
        media_api = tmdb.TV()
        response = media_api.popular(language=tmdb_language_code, page=current_page)
    else:
        raise ValueError("Invalid content_type. Expected 'movie' or 'tv'.")

    genres_api = tmdb.Genres()
    genres_response = genres_api.movie_list(language=tmdb_language_code)
    genres = {genre['id']: genre['name'] for genre in genres_response['genres']}

    for content in response['results'][current_movie:current_movie + 5]:
        await send_content_details(content, content_type, genres, language_code, callback_query)


async def send_content_details(content, content_type, genres, language_code, callback_query):
    title = content['title'] if content_type == 'movie' else content['name']
    poster_url = 'https://image.tmdb.org/t/p/w500' + content['poster_path']
    img = URLInputFile(poster_url)
    vote_average = content['vote_average']
    genre_names = [genres[genre_id] for genre_id in content['genre_ids'] if genre_id in genres]

    if content_type == 'movie':
        movie = tmdb.Movies(content['id'])
        details = movie.info()
        runtime = details['runtime']
        additional_info = None
    elif content_type == 'tv':
        show = tmdb.TV(content['id'])
        details = show.info()
        runtime = details['episode_run_time'][0] if details['episode_run_time'] else 'N/A'
        additional_info = details['number_of_seasons']

    original_title = content['original_title'] if content_type == 'movie' else content['original_name']
    release_date = content['release_date'] if content_type == 'movie' else content['first_air_date']

    message_text = get_message_text_for_card_from_TMDB(
        language_code, title, original_title, vote_average, genre_names,
        release_date.split('-')[0],
        runtime,
        content['adult'],
        content['overview'],
        content_type,
        additional_info
    )

    if len(message_text) > 1024:
        message_text = message_text[:1021] + '...'

    keyboard = create_keyboard(content["id"], language_code, 'save')
    await bot.send_chat_action(callback_query.message.chat.id, action='upload_photo')

    await asyncio.sleep(0.5)

    message = await bot.send_photo(callback_query.message.chat.id, photo=img, caption=message_text,
                                   parse_mode='HTML',
                                   reply_markup=keyboard)
    message_ids.append(message.message_id)


async def reset_movies(user_id, chat_id):
    current_page = 1
    current_movie = 0
    current_rating_movie = 0
    current_rating_page = 1

    update_current_popular(user_id, current_page, current_movie)
    update_current_rating(user_id, current_rating_page, current_rating_movie)

    await bot.send_message(chat_id, "The movie list has been reset. Click 'Next' to load the first 5 movies.")


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
        ],
        [
            InlineKeyboardButton(text=get_text(language_code, 'reset'), callback_data=f'filter_reset_{language_code}')
        ]
    ]
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


def search_movies(genre_filter, start_date, end_date, min_votes, max_votes, rating, language_code):
    discover = tmdb.Discover()
    print_info(f"Search parameters: genre_filter={genre_filter}, start_date={start_date}, end_date={end_date},"
               f"min_votes = {min_votes}, max_votes = {max_votes}")

    response = discover.movie(with_genres=genre_filter, primary_release_date_gte=start_date,
                              primary_release_date_lte=end_date,
                              vote_count_lte=max_votes, vote_count_gte=min_votes, sort_by=rating,
                              language=language_code)

    results = response['results']

    print_info(f"Search results: {results}")
    for movie in results:
        print_info(f"Vote count for {movie['title']}: {movie.get('vote_count', 0)}")
    return results


async def format_movie(user_id, movie):
    base_url = "https://image.tmdb.org/t/p/w500"
    poster_path = movie['poster_path']
    title = movie['title']
    overview = movie['overview']
    release_date = movie['release_date']
    genre_ids = movie['genre_ids']

    genre_names = get_genre_names(genre_ids)

    text = f"Title: {title}\nOverview: {overview}\nRelease Date: {release_date}\nGenres: {', '.join(genre_names)}"

    if poster_path is not None:
        await bot.send_photo(chat_id=user_id, photo=URLInputFile(base_url + poster_path), caption=text)
    else:
        await bot.send_message(chat_id=user_id, text=text)


def get_genre_names(genre_ids):
    genres = tmdb.Genres()
    response = genres.movie_list()
    genre_list = response['genres']
    genre_dict = {genre['id']: genre['name'] for genre in genre_list}
    genre_names = [genre_dict[genre_id] for genre_id in genre_ids if genre_id in genre_dict]
    return genre_names


global message_ids
message_ids = []


async def send_movies_by_rating_TMDB(callback_query: types.CallbackQuery, sort_order, vote_count, content_type):
    current_rating_page, current_rating_movie = get_current_popular_by_user_id(callback_query.from_user.id)

    chat_id = callback_query.message.chat.id
    language_code = get_user_language_from_db(callback_query.from_user.id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    if content_type == 'movie':
        discover = tmdb.Discover()
        response = discover.movie(sort_by=f'vote_average.{sort_order}', vote_count_gte=vote_count,
                                  language=tmdb_language_code, page=current_rating_page)
    elif content_type == 'tv':
        discover = tmdb.Discover()
        response = discover.tv(sort_by=f'vote_average.{sort_order}', vote_count_gte=vote_count,
                               language=tmdb_language_code, page=current_rating_page)
    else:
        raise ValueError("Invalid content_type. Expected 'movie' or 'tv'.")

    genres_api = tmdb.Genres()
    genres_response = genres_api.movie_list(language=tmdb_language_code)
    genres = {genre['id']: genre['name'] for genre in genres_response['genres']}

    for content in response['results'][current_rating_movie:current_rating_movie + 5]:
        title = content['title'] if content_type == 'movie' else content['name']
        original_title = content['original_title'] if 'original_title' in content else 'N/A'
        poster_url = 'https://image.tmdb.org/t/p/w500' + content['poster_path']
        img = URLInputFile(poster_url)

        vote_average = content['vote_average']
        genre_names = [genres[genre_id] for genre_id in content['genre_ids'] if genre_id in genres]
        release_date = content['release_date'][:4] if 'release_date' in content and content['release_date'] else 'N/A'
        runtime = content['runtime'] if 'runtime' in content else 'N/A'
        adult = content['adult'] if 'adult' in content else 'N/A'
        overview = content['overview'] if 'overview' in content else 'N/A'
        additional_info = content['additional_info'] if 'additional_info' in content else 'N/A'

        message_text = get_message_text_for_card_from_TMDB(
            language_code, title, original_title, vote_average, genre_names,
            release_date.split('-')[0],  # Extracting the release year
            runtime,
            adult,
            overview,
            content_type,
            additional_info
        )
        keyboard = create_keyboard(content["id"], language_code, 'save')
        await bot.send_chat_action(callback_query.message.chat.id, action='upload_photo')

        await asyncio.sleep(0.5)

        message = await bot.send_photo(callback_query.message.chat.id, photo=img, caption=message_text,
                                       parse_mode='HTML',
                                       reply_markup=keyboard)
        message_ids.append(message.message_id)

    current_rating_movie += 5
    if current_rating_movie >= len(response['results']):
        current_rating_page += 1
        current_rating_movie = 0

    update_current_rating(callback_query.from_user.id, current_rating_page, current_rating_movie)

    if sort_order == 'desc':
        callback_data_next_btn = f'next_page_rating_desc_{content_type}'
    else:
        callback_data_next_btn = f'next_page_rating_asc_{content_type}'

    next_button = types.InlineKeyboardButton(text=get_text(language_code, 'next'), callback_data=callback_data_next_btn)
    reset_button = types.InlineKeyboardButton(text=get_text(language_code, 'reset'), callback_data='reset_page')

    next_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[next_button, reset_button]])
    await bot.send_message(chat_id, get_text(language_code, 'next_5_movies'), reply_markup=next_keyboard)

    await bot.answer_callback_query(callback_query.id)


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


def get_message_text_for_card_from_TMDB(lang, title, original_title, vote_average, genre_names, release_year, runtime,
                                        adult, overview, content_type, additional_info=None):
    type_text = get_text(lang, 'type')
    release_year_text = get_text(lang, 'release_year')
    runtime_text = get_text(lang, 'runtime')
    genres_text = get_text(lang, 'genres')
    adult_text = get_text(lang, 'adult')
    rating_text = get_text(lang, 'rating_card')

    formatted_genres = ' | '.join(genre_names)
    formatted_adult = get_text(lang, 'no') if not adult else get_text(lang, 'yes')

    message_parts = [
        f'<b>{title}</b>\n\n',
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


async def send_random_content(query, language_code, tmdb_language_code):
    content_type = random.choice(['movie', 'tv'])

    if content_type == 'movie':
        random_content = await get_next_movie(query.from_user.id)
        content = tmdb.Movies(random_content['id'])
    else:  # content_type == 'tv'
        random_content = await get_next_tv_show(query.from_user.id)
        content = tmdb.TV(random_content['id'])

    content_info = content.info(language=tmdb_language_code)

    title = content_info['title'] if content_type == 'movie' else content_info['name']
    original_title = content_info['original_title'] if content_type == 'movie' else content_info['original_name']
    poster_url = 'https://image.tmdb.org/t/p/w500' + content_info['poster_path']
    vote_average = content_info['vote_average']
    genre_names = [genre['name'] for genre in content_info['genres']]
    release_year = content_info['release_date'].split('-')[0] if content_type == 'movie' else \
        content_info['first_air_date'].split('-')[0]
    runtime = content_info['runtime'] if content_type == 'movie' else content_info['episode_run_time'][0] if \
        content_info['episode_run_time'] else 'N/A'
    adult = content_info['adult'] if content_type == 'movie' else False
    overview = content_info['overview']
    additional_info = None if content_type == 'movie' else content_info['number_of_seasons']

    message_text = get_message_text_for_card_from_TMDB(language_code, title, original_title, vote_average, genre_names,
                                                       release_year, runtime, adult, overview, content_type,
                                                       additional_info)

    if len(message_text) > 1024:
        message_text = message_text[:1021] + '...'

    keyboard = create_keyboard(random_content["id"], language_code, 'save')
    another_button = create_keyboard(random_content["id"], language_code, 'another')

    keyboard.inline_keyboard.append(another_button.inline_keyboard[0])

    if query.message:
        await bot.delete_message(chat_id=query.from_user.id, message_id=query.message.message_id)

    await bot.send_photo(chat_id=query.from_user.id, photo=URLInputFile(poster_url), caption=message_text,
                         reply_markup=keyboard,
                         parse_mode='HTML')

    await query.answer(show_alert=False)


selected_movies = set()
selected_tv_shows = set()


async def get_next_movie(user_id):
    all_movies = await fetch_random_movies(user_id)
    while True:
        movie = random.choice(all_movies)
        if movie['id'] not in selected_movies:
            selected_movies.add(movie['id'])
            movie_counters[user_id] = movie_counters.get(user_id, 0) + 1
            return movie


movie_counters = {}
tv_counters = {}


async def get_next_tv_show(user_id):
    all_tv_shows = await fetch_random_tv_shows(user_id)
    while True:
        tv_show = random.choice(all_tv_shows)
        if tv_show['id'] not in selected_tv_shows:
            selected_tv_shows.add(tv_show['id'])
            tv_counters[user_id] = tv_counters.get(user_id, 0) + 1
            return tv_show


async def fetch_random_movies(user_id):
    current_page = await get_current_page_random(user_id, 'current_random_movie_page')
    all_movies = tmdb.Discover().movie(page=current_page, vote_count_gte=300)['results']
    random.shuffle(all_movies)
    if movie_counters.get(user_id, 0) >= 5:
        await update_current_page_random(user_id, 'current_random_movie_page')
        movie_counters[user_id] = 0
    return all_movies


async def fetch_random_tv_shows(user_id):
    current_page = await get_current_page_random(user_id, 'current_random_tv_page')
    all_tv_shows = tmdb.Discover().tv(page=current_page, vote_count_gte=300)['results']
    random.shuffle(all_tv_shows)
    if tv_counters.get(user_id, 0) >= 5:
        await update_current_page_random(user_id, 'current_random_tv_page')
        tv_counters[user_id] = 0
    return all_tv_shows
