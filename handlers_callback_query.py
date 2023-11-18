import tmdb
from aiogram import types
from aiogram.enums import ParseMode
from tmdbsimple import Discover, Genres, Movies

from config import TMDB_API_KEY
from keyboards import get_next_action_message, submenu_keyboard, menu_keyboard, get_rating_mod
from main import dp, bot

user_languages = {}

tmdb.API_KEY = TMDB_API_KEY


@dp.callback_query(lambda query: query.data.startswith('set_language'))
async def set_language_callback(query: types.CallbackQuery):
    language_code = query.data.split('_')[2]
    set_user_language(query.from_user.id, language_code)
    next_action_message = get_next_action_message(language_code)
    await bot.send_message(query.from_user.id, next_action_message, reply_markup=menu_keyboard(language_code),
                           parse_mode=ParseMode.HTML)
    await bot.answer_callback_query(query.id, f"Language set to {language_code}")

    # Remove the menu buttons
    await bot.edit_message_reply_markup(query.from_user.id, query.message.message_id)


dp.callback_query(lambda query: query.data.startswith('menu_option'))


@dp.callback_query(lambda query: query.data.startswith('menu_option'))
async def set_menu_callback(query: types.CallbackQuery):
    menu_code = query.data.split('_')[2]
    language_code = query.data.split('_')[3]

    if menu_code == '1' or menu_code == '2':
        keyboard_markup = submenu_keyboard(language_code)
        await bot.edit_message_text("Please select an option:",
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

    if submenu_code == '1':
        discover = Discover()
        response = discover.movie(language=language_code)

        genres_api = Genres()
        genres_response = genres_api.movie_list(language=language_code)
        genres = {genre['id']: genre['name'] for genre in genres_response['genres']}

        for movie in response['results'][:3]:
            title = movie['title']
            poster_url = 'https://image.tmdb.org/t/p/w500' + movie['poster_path']
            vote_average = movie['vote_average']
            genre_names = [genres[genre_id] for genre_id in movie['genre_ids'] if genre_id in genres]

            message_text = f'<a href="{poster_url}">{title}</a>\nRating: {vote_average}\nGenres: {", ".join(genre_names)}'
            await bot.send_message(call.message.chat.id, text=message_text, parse_mode='HTML')

    elif submenu_code == '2':
        message_text, keyboard_markup = get_rating_mod(language_code)
        await bot.edit_message_text(message_text,
                                    chat_id=call.from_user.id,
                                    message_id=call.message.message_id,
                                    reply_markup=keyboard_markup)


@dp.callback_query(lambda c: c.data and c.data.startswith('sort_option_low'))
async def process_callback_low(callback_query: types.CallbackQuery):
    discover = Discover()
    response = discover.movie(vote_average_gte=1, vote_average_lte=10, sort_by='vote_average.asc')

    for s in response['results'][:3]:
        movie = Movies(s['id'])
        response = movie.info()
        poster_url = f"https://image.tmdb.org/t/p/w500{response['poster_path']}"
        title = response['title']
        vote_average = response['vote_average']
        genre_names = [genre['name'] for genre in response['genres']]
        message_text = f'<a href="{poster_url}">{title}</a>\nRating: {vote_average}\nGenres: {", ".join(genre_names)}'
        await bot.send_message(callback_query.from_user.id, text=message_text, parse_mode='HTML')

    await bot.answer_callback_query(callback_query.id)


@dp.callback_query(lambda c: c.data and c.data.startswith('sort_option_high'))
async def process_callback_high(callback_query: types.CallbackQuery):
    discover = Discover()
    response = discover.movie(vote_average_gte=1, vote_average_lte=10, sort_by='vote_average.desc')

    for s in response['results'][:4]:
        movie = Movies(s['id'])
        response = movie.info()
        vote_average = response['vote_average']
        if vote_average == 0:
            continue
        poster_url = f"https://image.tmdb.org/t/p/w500{response['poster_path']}"
        title = response['title']
        genre_names = [genre['name'] for genre in response['genres']]
        message_text = f'<a href="{poster_url}">{title}</a>\nRating: {vote_average}\nGenres: {", ".join(genre_names)}'
        await bot.send_message(callback_query.from_user.id, text=message_text, parse_mode='HTML')

    await bot.answer_callback_query(callback_query.id)


def set_user_language(user_id, language_code):
    user_languages[user_id] = language_code
