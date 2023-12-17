# Description: Main file for bot logic and handlers (client side)
import asyncio
import logging
import config

from aiogram import Bot
from aiogram import Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart

from db.database import *
from utils import api
from utils.misc import *
from utils.texts import TEXTS

tmdb.API_KEY = api.TMDB_API_KEY
bot = Bot(config.BOT_TOKEN)
dp = Dispatcher(bot=bot)
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'
connection = None

shown_movies = set()

# ========================================= Variable for filters ========================================= #
genre_names_filter = {}
# --------------
user_genre_choice = {}
user_release_date_choice = {}
user_vote_count_choice = {}
user_rating_choice = {}

# ========================================= Keyboard ========================================= #

kb = [[types.KeyboardButton(text='menu'), types.KeyboardButton(text='language')],
      [types.KeyboardButton(text='saved'), ]]


# ========================================= Handler for menu keyboard ========================================= #

@dp.message(lambda message: message.text.lower() == 'menu')
async def menu_command(message: types.Message):
    await cmd_menu(message)


@dp.message(lambda message: message.text.lower() == 'language')
async def language_command(message: types.Message):
    await cmd_language(message)


# ========================================= Client side ========================================= #
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    bot_info = await bot.get_me()
    user_id = message.from_user.id

    user_language = get_user_language_from_db(user_id)

    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, )

    if user_language:
        await message.answer(
            f"You have set your language to <b>{user_language}</b>. If you want to change it, use the language button.",
            reply_markup=keyboard, parse_mode=ParseMode.HTML)
    else:
        await message.answer(
            f"<b>Welcome to {bot_info.first_name}.</b>\n 🇬🇧 Please select language \n 🇺🇦 Будь ласка, виберіть мову \n "
            f"🇷🇺 Пожалуйста, выберите язык", reply_markup=language_keyboard(), parse_mode=ParseMode.HTML)


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
    update_user_pages_from_db(user_id)

    print_info(f"User {user_id} chose language {language_code} = set_language_callback")
    select_menu = TEXTS[language_code]['select_menu']

    set_user_language(query.from_user.id, language_code)

    selected_language = TEXTS[language_code]['selected_language']

    await bot.send_message(query.from_user.id, select_menu, reply_markup=menu_keyboard(language_code),
                           parse_mode=ParseMode.HTML)
    await bot.answer_callback_query(query.id, f"Language set to {language_code}")

    await bot.edit_message_reply_markup(query.from_user.id, query.message.message_id)
    await bot.edit_message_text(chat_id=query.from_user.id, message_id=query.message.message_id, text=selected_language,
                                parse_mode=ParseMode.HTML)


@dp.callback_query(lambda query: query.data.startswith('menu_option'))
async def set_menu_callback(query: types.CallbackQuery):
    menu_code = query.data.split('_')[2]
    language_code = get_user_language_from_db(query.from_user.id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    select_option_text = get_text(language_code, 'select_option')

    if menu_code == '1' or menu_code == '2':
        keyboard_markup = submenu_keyboard(language_code, menu_code)
        await bot.edit_message_text(select_option_text, chat_id=query.from_user.id, message_id=query.message.message_id,
                                    reply_markup=keyboard_markup)
    elif menu_code == '3':
        await send_random_content(query, language_code, tmdb_language_code)
    elif menu_code == '4':
        await send_option_message(query, language_code, select_option_text)


@dp.callback_query(lambda query: query.data.startswith('another_'))
async def show_another_random_movie(query: types.CallbackQuery):
    language_code = get_user_language_from_db(query.from_user.id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    await send_random_content(query, language_code, tmdb_language_code)


@dp.callback_query(lambda query: query.data.startswith('submenu_option_'))
async def set_submenu_callback(call):
    submenu_code = call.data.split('_')[2]
    submenu_code_2 = call.data.split('_')[3]
    language_code = get_user_language_from_db(call.from_user.id)

    if submenu_code == '1':
        if submenu_code_2 == '1':
            await send_next_media(call, language_code, 'movie')
        elif submenu_code_2 == '2':
            await send_next_media(call, language_code, 'tv')
    elif submenu_code == '2':
        message_text, keyboard_markup = get_rating_mod(submenu_code_2, language_code)
        await bot.edit_message_text(message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                    reply_markup=keyboard_markup)
    elif submenu_code == '3':
        message_text, keyboard_markup = generate_filter_submenu(language_code)
        await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                    reply_markup=keyboard_markup)


@dp.callback_query(lambda query: query.data.startswith('load_next_'))
async def load_next_movies_callback(call):
    content_type = call.data.split('_')[2]

    language_code = get_user_language_from_db(call.from_user.id)
    if content_type == 'movie':
        await send_next_media(call, language_code, 'movie')
    elif content_type == 'tv':
        await send_next_media(call, language_code, 'tv')


@dp.callback_query(lambda query: query.data.startswith('reset_page'))
async def reset_page_callback(call):
    await reset_movies(call.from_user.id, call.message.chat.id)


@dp.callback_query(lambda c: c.data.startswith('save_'))
async def process_callback_save(callback_query: types.CallbackQuery):
    movie_id = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id

    save_movie_to_db(user_id, movie_id)

    save_text = get_text(get_user_language_from_db(user_id), 'save')
    await bot.answer_callback_query(callback_query.id, save_text)


@dp.callback_query(lambda c: c.data and c.data.startswith('sort_option_low_'))
async def handle_sort_option_low(callback_query: types.CallbackQuery):
    submenu_code = callback_query.data.split('_')[3]
    if submenu_code == '1':
        await send_movies_by_rating_TMDB(callback_query, 'asc', 1000, 'movie')
    elif submenu_code == '2':
        await send_movies_by_rating_TMDB(callback_query, 'asc', 500, 'tv')


@dp.callback_query(lambda c: c.data and c.data.startswith('sort_option_high_'))
async def handle_sort_option_high(callback_query: types.CallbackQuery):
    submenu_code = callback_query.data.split('_')[3]
    if submenu_code == '1':
        await send_movies_by_rating_TMDB(callback_query, 'desc', 1000, 'movie')
    elif submenu_code == '2':
        await send_movies_by_rating_TMDB(callback_query, 'desc', 500, 'tv')


@dp.callback_query(lambda c: c.data and c.data.startswith('next_page_rating_'))
async def handle_next_page_rating(callback_query: types.CallbackQuery):
    sort_order = callback_query.data.split('_')[3]
    content_type = callback_query.data.split('_')[4]

    if content_type == 'movie':
        await send_movies_by_rating_TMDB(callback_query, sort_order=sort_order, vote_count=1000, content_type='movie')
    elif content_type == 'tv':
        await send_movies_by_rating_TMDB(callback_query, sort_order=sort_order, vote_count=1000, content_type='tv')

    while len(message_ids) > 5:
        message_id = message_ids.pop(0)
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=message_id)

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)


# ========================================= Filter =========================================  #
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

    save_fields_to_table_search_movie_db(call.from_user.id, chosen_genre_id, year_range=None, user_rating=None,
                                         rating=None)

    language_code = get_user_language_from_db(call.from_user.id)
    message_text, keyboard_markup = generate_filter_submenu(language_code)
    await bot.send_message(call.from_user.id, f"You chose genre {chosen_genre_name}")
    await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                reply_markup=keyboard_markup)
    await bot.send_message(call.from_user.id, f"Вы выбрали жанр, вы можете добавить еще "
                                              f"фильтры или нажать 'Поск' для "
                                              f"получения результата")
    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('filter_releaseDate_'))
async def process_callback_filter_release_date(call: types.CallbackQuery):
    language_code = get_user_language_from_db(call.from_user.id)
    release_date_keyboard = [[InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][0],
                                                   callback_data=f'release_date_1700-1980_{language_code}'),
                              InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][1],
                                                   callback_data=f'release_date_1981-2000_{language_code}')], [
                                 InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][2],
                                                      callback_data=f'release_date_2001-2020_{language_code}'),
                                 InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][3],
                                                      callback_data=f'release_date_2020-2030_{language_code}')], [
                                 InlineKeyboardButton(text=TEXTS[language_code]['release_date_options'][4],
                                                      callback_data=f'release_date_1500-2030_{language_code}')]]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=release_date_keyboard)
    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    await bot.send_message(call.from_user.id, get_text(language_code, 'filter_releaseDate_txt'),
                           reply_markup=keyboard_markup)


@dp.callback_query(lambda query: query.data.startswith('release_date_'))
async def process_callback_filter_release_date_choice(call: types.CallbackQuery):
    chosen_release_date_option = call.data.split('_')[2]
    user_release_date_choice[call.from_user.id] = chosen_release_date_option
    language_code = get_user_language_from_db(call.from_user.id)
    message_text, keyboard_markup = generate_filter_submenu(language_code)
    await bot.send_message(call.from_user.id, f"You chose option {chosen_release_date_option}")

    save_fields_to_table_search_movie_db(call.from_user.id, None, chosen_release_date_option, None, None)

    await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                reply_markup=keyboard_markup)
    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('filter_voteCount_'))
async def process_callback_filter_vote_count(call: types.CallbackQuery):
    language_code = get_user_language_from_db(call.from_user.id)
    vote_count_keyboard = [[InlineKeyboardButton(text=TEXTS[language_code]['vote_count_options'][0],
                                                 callback_data=f'vote_count_100-500_{language_code}'),
                            InlineKeyboardButton(text=TEXTS[language_code]['vote_count_options'][1],
                                                 callback_data=f'vote_count_500-1000_{language_code}')], [
                               InlineKeyboardButton(text=TEXTS[language_code]['vote_count_options'][2],
                                                    callback_data=f'vote_count_1000-10000_{language_code}'),
                               InlineKeyboardButton(text=TEXTS[language_code]['vote_count_options'][3],
                                                    callback_data=f'vote_count_100-10000000_{language_code}')]]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=vote_count_keyboard)
    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    await bot.send_message(call.from_user.id, get_text(language_code, 'filter_voteCount_txt'),
                           reply_markup=keyboard_markup)


@dp.callback_query(lambda query: query.data.startswith('vote_count_'))
async def process_callback_filter_vote_count_choice(call: types.CallbackQuery):
    chosen_vote_count_option = call.data.split('_')[2]
    user_vote_count_choice[call.from_user.id] = chosen_vote_count_option
    language_code = get_user_language_from_db(call.from_user.id)
    message_text, keyboard_markup = generate_filter_submenu(language_code)
    await bot.send_message(call.from_user.id, f"You chose option {chosen_vote_count_option}")

    save_fields_to_table_search_movie_db(call.from_user.id, None, None, chosen_vote_count_option, None)

    await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                reply_markup=keyboard_markup)
    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('filter_rating_'))
async def process_callback_filter_rating(call: types.CallbackQuery):
    language_code = get_user_language_from_db(call.from_user.id)
    rating_keyboard = [
        [InlineKeyboardButton(text=TEXTS[language_code]['starting_low'],
                              callback_data=f'sort_option_popularity.asc_{language_code}')],
        [InlineKeyboardButton(text=TEXTS[language_code]['starting_high'],
                              callback_data=f'sort_option_popularity.desc_{language_code}')]]
    keyboard_markup = InlineKeyboardMarkup(inline_keyboard=rating_keyboard)
    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    await bot.send_message(call.from_user.id, get_text(language_code, 'filter_rating_txt'),
                           reply_markup=keyboard_markup)


@dp.callback_query(lambda query: query.data.startswith('sort_option_'))
async def process_callback_sort_option(call: types.CallbackQuery):
    chosen_sort_option = call.data.split('_')[2]
    language_code = get_user_language_from_db(call.from_user.id)
    message_text, keyboard_markup = generate_filter_submenu(language_code)
    await bot.send_message(call.from_user.id, f"You chose option {chosen_sort_option}")

    save_fields_to_table_search_movie_db(call.from_user.id, None, None, None, chosen_sort_option)

    await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                reply_markup=keyboard_markup)
    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('filter_search_'))
async def process_search(call: types.CallbackQuery):
    user_id = call.from_user.id
    language_code = get_user_language_from_db(user_id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')

    filters = get_filters_from_db(user_id)

    print_info(f"Filters: {filters}")

    if filters is None:
        await bot.send_message(user_id,
                               "Вы не выбрали фильтры для фильма. Пожалуйста, выберите хотя бы один фильтр и попробуйте снова.")
    else:
        genre_filter = filters.get('genre')
        release_date_filter = filters.get('release_date')
        user_rating_filter = filters.get('user_rating')
        rating = filters.get('rating')

        if not any([genre_filter, release_date_filter, user_rating_filter, rating]):
            await bot.send_message(user_id,
                                   "Вы не выбрали фильтры для фильма. Пожалуйста, выберите хотя бы один фильтр и попробуйте снова.")
        else:
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

            movies = search_movies(genre_filter, start_date, end_date, min_votes, max_votes, rating, tmdb_language_code)
            print_info(f"Movies: {movies}")
            for movie in movies[:5]:
                await format_movie(user_id=user_id, movie=movie)

            # reset_filters_in_db(user_id)

            await call.answer(show_alert=False)


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

        await bot.send_photo(call.message.chat.id, photo=img, caption=message_text, parse_mode='HTML',
                             reply_markup=keyboard)
    await call.answer(show_alert=False)


# ========================================= Delete =========================================  #

@dp.callback_query(lambda query: query.data.startswith('delete_'))
async def delete_callback(query: types.CallbackQuery):
    movie_id = query.data.split('_')[1]
    user_id = query.from_user.id

    delete_movie_from_db(user_id, movie_id)

    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)


# ========================================= Back =========================================  #
@dp.callback_query(lambda query: query.data == 'back')
async def set_back_callback(query: types.CallbackQuery):
    language_code = get_user_language_from_db(query.from_user.id)

    select_option_text = get_text(language_code, 'select_option')

    print_info(f"User {query.from_user.id} chose back option = set_back_callback")
    await bot.edit_message_text(select_option_text, chat_id=query.from_user.id, message_id=query.message.message_id,
                                reply_markup=menu_keyboard(language_code))


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
    await cmd_menu_for_save(message)


@dp.message(Command("saved"))
async def cmd_menu_for_save(message: types.Message):
    user_id = message.from_user.id
    language_code = get_user_language_from_db(user_id)
    select_option_text = get_text(language_code, 'select_option')
    print(324)

    await send_option_message(message, language_code, select_option_text)


# ========================================= Another =========================================  #
@dp.callback_query(lambda c: c.data)
async def process_callback(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f"You chose option {callback_query.data}")


# ========================================= Testing and Exception Handling ========================================= #
async def testing():
    global connection
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
