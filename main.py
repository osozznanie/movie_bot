import logging

from aiogram import Bot, types, filters
from aiogram import Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart

from db.database import *
from utils import api, texts
from utils.misc import *
from utils.texts import TEXTS

tmdb.API_KEY = api.TMDB_API_KEY
bot = Bot(config.BOT_TOKEN)
dp = Dispatcher(bot=bot)
connection = None

shown_movies = set()

# ========================================= Keyboard ========================================= #

kb = [[types.KeyboardButton(text='/menu'), types.KeyboardButton(text='/language')],
      [types.KeyboardButton(text='/saved'), ]]


# ========================================= Client side ========================================= #
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    bot_info = await bot.get_me()
    user_id = message.from_user.id

    user_language = get_user_language_from_db(user_id)
    main_keyboard, keyboard_markup = language_keyboard()
    message_txt = get_text(user_language, 'second_tap_to_start')

    if user_language:
        await bot.send_message(user_id, message_txt, reply_markup=main_keyboard, parse_mode=ParseMode.HTML)
    else:
        await message.answer(
            f"<b>Welcome to {bot_info.first_name}.</b>\n 🇬🇧 Please select language \n 🇺🇦 Будь ласка, виберіть мову \n "
            f"Пожалуйста, выберите язык", reply_markup=keyboard_markup, parse_mode=ParseMode.HTML)


# ========================================= Language =========================================  #
user_languages = {}

@dp.message(Command("language"))
async def cmd_language(message: types.Message):
    language_code = get_user_language_from_db(message.from_user.id)

    *_, keyboard_markup = language_keyboard()
    await message.answer(TEXTS[language_code]['select_language'], reply_markup=keyboard_markup)


@dp.callback_query(lambda query: query.data.startswith('set_language'))
async def set_language_callback(query: types.CallbackQuery):
    language_code = query.data.split('_')[2]

    user_id = query.from_user.id
    username = query.from_user.username
    language = language_code

    update_user_language_from_db(user_id, username, language)
    update_user_pages_from_db(user_id)

    select_menu = TEXTS[language_code]['select_menu']

    set_user_language(query.from_user.id, language_code)

    selected_language = TEXTS[language_code]['selected_language']

    await bot.send_message(query.from_user.id, select_menu, reply_markup=menu_keyboard(language_code),
                           parse_mode=ParseMode.HTML)
    await bot.answer_callback_query(query.id, f"Language set to {language_code}")

    await asyncio.create_task(delete_message_after_delay(15, query.from_user.id, query.message.message_id))

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
        keyboard = create_content_choice_keyboard(language_code)
        await bot.edit_message_text(select_option_text, chat_id=query.from_user.id, message_id=query.message.message_id,
                                    reply_markup=keyboard)
    elif menu_code == '4':
        await send_option_message(query, language_code, select_option_text)


@dp.callback_query(lambda query: query.data.startswith('choose_content_'))
async def set_content_choice_callback(query: types.CallbackQuery):
    language_code = get_user_language_from_db(query.from_user.id)
    content_type = query.data.split('_')[2]
    select_option_text = get_text(language_code, 'select_option')

    keyboard = create_rating_choice_keyboard(language_code, content_type)
    await bot.edit_message_text(select_option_text, chat_id=query.from_user.id, message_id=query.message.message_id,
                                reply_markup=keyboard)


@dp.callback_query(lambda query: query.data.startswith('choose_rating_'))
async def set_rating_choice_callback(query: types.CallbackQuery):
    language_code = get_user_language_from_db(query.from_user.id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')
    content_type = query.data.split('_')[2]
    rating_range = query.data.split('_')[3]

    rating_min, rating_max = map(float, rating_range.split('-'))

    await send_random_content(query, language_code, tmdb_language_code, content_type, (rating_min, rating_max))


@dp.callback_query(lambda query: query.data.startswith('another_'))
async def show_another_random_movie(query: types.CallbackQuery):
    language_code = get_user_language_from_db(query.from_user.id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')
    content_type = query.data.split('_')[1]
    rating_range = query.data.split('_')[2]

    rating_min, rating_max = map(float, rating_range.strip('()').split(', '))
    await send_random_content(query, language_code, tmdb_language_code, content_type, (rating_min, rating_max))


@dp.callback_query(lambda query: query.data.startswith('submenu_option_'))
async def set_submenu_callback(call):
    submenu_code = call.data.split('_')[2]
    content_type_code = call.data.split('_')[3]
    language_code = get_user_language_from_db(call.from_user.id)

    if submenu_code == '1':
        if content_type_code == '1':
            await send_next_media(call, language_code, 'movie')
        elif content_type_code == '2':
            await send_next_media(call, language_code, 'tv')
    elif submenu_code == '2':
        message_text, keyboard_markup = get_rating_mod(content_type_code, language_code)
        await bot.edit_message_text(message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                    reply_markup=keyboard_markup)
    elif submenu_code == '3':
        if content_type_code == '1':
            content_type = 'movie'
        elif content_type_code == '2':
            content_type = 'tv'
        message_text, keyboard_markup = generate_filter_submenu(language_code, content_type)
        await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                    reply_markup=keyboard_markup)
        await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('load_next_popular_'))
async def load_next_movies_callback(call):
    content_type = call.data.split('_')[3]

    language_code = get_user_language_from_db(call.from_user.id)

    if content_type == 'movie':
        await send_next_media(call, language_code, 'movie')
    elif content_type == 'tv':
        await send_next_media(call, language_code, 'tv')
    else:
        await bot.answer_callback_query(call.id, "Something went wrong")

    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('load_previous_popular_'))
async def load_previous_movies_callback(call):
    content_type = call.data.split('_')[3]

    language_code = get_user_language_from_db(call.from_user.id)
    if content_type == 'movie':
        await send_previous_media_by_popularity(call, language_code, 'movie')
    elif content_type == 'tv':
        await send_previous_media_by_popularity(call, language_code, 'tv')
    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('reset_page'))
async def reset_page_callback(call):
    await call.answer(show_alert=False)
    await reset_movies(call, call.from_user.id, call.message.chat.id)



@dp.callback_query(lambda query: query.data.startswith('filter_reset_page_'))
async def reset_page_filter_callback(call):
    await call.answer(show_alert=False)
    await reset_filters(call.from_user.id, call.message.chat.id, call.data.split('_')[3])


@dp.callback_query(lambda query: query.data.startswith('next_page_filter'))
async def next_page_filter_callback(call):
    user_id = call.from_user.id
    language_code = get_user_language_from_db(user_id)
    content_type = call.data.split('_')[3]

    if content_type == 'movie':
        await send_next_page_filter(call, language_code, 'movie')
    elif content_type == 'tv':
        await send_next_page_filter(call, language_code, 'tv')

    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('previous_page_filter'))
async def previous_page_filter_callback(call):
    user_id = call.from_user.id
    language_code = get_user_language_from_db(user_id)
    content_type = call.data.split('_')[3]

    if content_type == 'movie':
        await send_previous_page_filter(call, language_code, 'movie')
    elif content_type == 'tv':
        await send_previous_page_filter(call, language_code, 'tv')

    await call.answer(show_alert=False)


@dp.callback_query(lambda c: c.data.startswith('save_'))
async def process_callback_save(callback_query: types.CallbackQuery):
    movie_id = callback_query.data.split('_')[1]
    content_type = callback_query.data.split('_')[2]
    user_id = callback_query.from_user.id
    language_code = get_user_language_from_db(user_id)

    if content_type == 'movie':
        save_movie_to_db(user_id, movie_id)
    elif content_type == 'tv':
        save_series_to_db(user_id, movie_id)

    save_text = get_text(get_user_language_from_db(user_id), 'save')
    await callback_query.answer(get_text(language_code, 'save_yet'), show_alert=True)


@dp.callback_query(lambda c: c.data and c.data.startswith('sort_option_low_'))
async def handle_sort_option_low(callback_query: types.CallbackQuery):
    submenu_code = callback_query.data.split('_')[3]

    if submenu_code == '1':
        await send_next_media_by_rating(callback_query, 'asc', 1000, 'movie')
    elif submenu_code == '2':
        await send_next_media_by_rating(callback_query, 'asc', 500, 'tv')

    await callback_query.answer(show_alert=False)


@dp.callback_query(lambda c: c.data and c.data.startswith('sort_option_high_'))
async def handle_sort_option_high(callback_query: types.CallbackQuery):
    submenu_code = callback_query.data.split('_')[3]

    if submenu_code == '1':
        await send_next_media_by_rating(callback_query, 'desc', 1000, 'movie')
    elif submenu_code == '2':
        await send_next_media_by_rating(callback_query, 'desc', 500, 'tv')

    await callback_query.answer(show_alert=False)


@dp.callback_query(lambda c: c.data and c.data.startswith('next_page_rating_'))
async def handle_next_page_rating(callback_query: types.CallbackQuery):
    sort_order = callback_query.data.split('_')[3]
    content_type = callback_query.data.split('_')[4]

    if content_type == 'movie':
        await send_next_media_by_rating(callback_query, sort_order=sort_order, vote_count=1000, content_type='movie')
    elif content_type == 'tv':
        await send_next_media_by_rating(callback_query, sort_order=sort_order, vote_count=1000, content_type='tv')

    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await callback_query.answer(show_alert=False)


@dp.callback_query(lambda c: c.data and c.data.startswith('previous_page_rating_'))
async def handle_previous_page_rating(callback_query: types.CallbackQuery):
    sort_order = callback_query.data.split('_')[3]
    content_type = callback_query.data.split('_')[4]
    user_language = get_user_language_from_db(callback_query.from_user.id)
    if content_type == 'movie':
        await send_previous_movies_by_rating_TMDB(callback_query,
                                                  language_code=user_language, sort_order=sort_order, vote_count=1000,
                                                  content_type='movie')
    elif content_type == 'tv':
        await send_previous_movies_by_rating_TMDB(callback_query,
                                                  language_code=user_language, sort_order=sort_order, vote_count=1000,
                                                  content_type='tv')


    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await callback_query.answer(show_alert=False)


# ========================================= Filter =========================================  #
@dp.callback_query(lambda query: query.data.startswith('filter_genre_'))
async def process_callback_filter_genre(call: types.CallbackQuery):
    language_code = get_user_language_from_db(call.from_user.id)
    tmdb_language_code = get_text(language_code, 'LANGUAGE_CODES')
    content_type = call.data.split('_')[2]

    if content_type == 'movie':
        await generate_genre_submenu(call, tmdb_language_code, content_type)
    elif content_type == 'tv':
        await generate_genre_submenu(call, tmdb_language_code, content_type)


@dp.callback_query(lambda query: query.data.startswith('genre_'))
async def process_callback_genre(call: types.CallbackQuery):
    chosen_genre_id = call.data.split('_')[2]
    content_type = call.data.split('_')[1]
    language_code = get_user_language_from_db(call.from_user.id)

    if content_type == 'movie':
        save_fields_to_table_search_movie_db(call.from_user.id, chosen_genre_id, year_range=None, user_rating=None,
                                             rating=None)
    elif content_type == 'tv':
        save_fields_to_table_search_series_db(call.from_user.id, chosen_genre_id, year_range=None, user_rating=None,
                                              rating=None)

    message_text, keyboard_markup = generate_filter_submenu(language_code, content_type)
    await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                reply_markup=keyboard_markup)
    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('filter_releaseDate_'))
async def process_callback_filter_release_date(call: types.CallbackQuery):
    language_code = get_user_language_from_db(call.from_user.id)
    content_type = call.data.split('_')[2]

    release_date_keyboard = generate_release_date_submenu(language_code, content_type)

    await bot.edit_message_text(chat_id=call.from_user.id, text=get_text(language_code, 'filter_releaseDate_txt'),
                                reply_markup=release_date_keyboard, message_id=call.message.message_id)


@dp.callback_query(lambda query: query.data.startswith('release_date_'))
async def process_callback_filter_release_date_choice(call: types.CallbackQuery):
    chosen_release_date_option = call.data.split('_')[2]
    content_type = call.data.split('_')[3]
    language_code = get_user_language_from_db(call.from_user.id)

    if content_type == 'movie':
        save_fields_to_table_search_movie_db(call.from_user.id, None, chosen_release_date_option, None, None)
    elif content_type == 'tv':
        save_fields_to_table_search_series_db(call.from_user.id, None, chosen_release_date_option, None, None)

    message_text, keyboard_markup = generate_filter_submenu(language_code, content_type)
    await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                reply_markup=keyboard_markup)
    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('filter_voteCount_'))
async def process_callback_filter_vote_count(call: types.CallbackQuery):
    language_code = get_user_language_from_db(call.from_user.id)
    content_type = call.data.split('_')[2]

    keyboard_markup_vote_count = generate_vote_count_submenu(language_code, content_type)

    await bot.edit_message_text(text=get_text(language_code, 'filter_voteCount_txt'), chat_id=call.from_user.id,
                                message_id=call.message.message_id,
                                reply_markup=keyboard_markup_vote_count)


@dp.callback_query(lambda query: query.data.startswith('vote_count_'))
async def process_callback_filter_vote_count_choice(call: types.CallbackQuery):
    chosen_vote_count_option = call.data.split('_')[2]
    content_type = call.data.split('_')[3]
    language_code = get_user_language_from_db(call.from_user.id)

    if content_type == 'movie':
        save_fields_to_table_search_movie_db(call.from_user.id, None, None, chosen_vote_count_option, None)
    elif content_type == 'tv':
        save_fields_to_table_search_series_db(call.from_user.id, None, None, chosen_vote_count_option, None)

    message_text, keyboard_markup = generate_filter_submenu(language_code, content_type)
    await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                reply_markup=keyboard_markup)
    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('filter_rating_'))
async def process_callback_filter_rating(call: types.CallbackQuery):
    language_code = get_user_language_from_db(call.from_user.id)
    content_type = call.data.split('_')[2]

    keyboard_markup_rating = generate_rating_submenu(language_code, content_type)
    await bot.edit_message_text(text=get_text(language_code, 'filter_rating_txt')
                                , chat_id=call.from_user.id, message_id=call.message.message_id,
                                reply_markup=keyboard_markup_rating)


@dp.callback_query(lambda query: query.data.startswith('sort_option_'))
async def process_callback_sort_option(call: types.CallbackQuery):
    content_type = call.data.split('_')[4]
    language_code = get_user_language_from_db(call.from_user.id)
    chosen_sort_option = 'vote_' + call.data.split('_')[3]
    if content_type == 'movie':
        save_fields_to_table_search_movie_db(call.from_user.id, None, None, None, chosen_sort_option)
    elif content_type == 'tv':
        save_fields_to_table_search_series_db(call.from_user.id, None, None, None, chosen_sort_option)

    message_text, keyboard_markup = generate_filter_submenu(language_code, content_type)
    await bot.edit_message_text(text=message_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                reply_markup=keyboard_markup)
    await call.answer(show_alert=False)


@dp.callback_query(lambda query: query.data.startswith('filter_search_'))
async def process_search(call: types.CallbackQuery):
    user_id = call.from_user.id
    language_code = get_user_language_from_db(user_id)
    content_type = call.data.split('_')[2]

    set_filter_pages_and_movies_by_user_id(user_id, 1, 1, 0, 0)

    if check_filters_exist(user_id, content_type):
        msg_text = get_text(language_code, 'selected_filters') + "\n" + get_user_filters(user_id, content_type)
        await bot.edit_message_text(text=msg_text, chat_id=call.from_user.id, message_id=call.message.message_id,
                                    parse_mode=ParseMode.HTML)

    await send_next_page_filter(call, language_code, content_type)
    await call.answer(show_alert=False)


# ========================================= Saved movies =========================================  #
@dp.callback_query(lambda c: c.data in ['saved_movie', 'saved_tv'])
async def show_saved_media(call):
    user_id = call.from_user.id
    user_language = get_user_language_from_db(user_id)
    content_type = call.data.split('_')[1]
    store_message_id_in_db(user_id, 0)

    if content_type == 'movie':
        saved_media = [movie_id[0] for movie_id in get_saved_movies_from_db(user_id)]
    else:  # content_type == 'tv':
        saved_media = [series_id[0] for series_id in get_saved_series_from_db(user_id)]

    if not saved_media:
        not_found = await bot.send_message(call.from_user.id, get_text(user_language, 'not_found_saved_content'))
        await delete_message_after_delay(10, call.from_user.id, not_found.message_id)

    for media_id in saved_media:
        await send_content_details_by_content_id(media_id, content_type, call, True)
        await asyncio.sleep(0.5)


# ========================================= Delete =========================================  #

@dp.callback_query(lambda query: query.data.startswith('delete_'))
async def delete_callback(query: types.CallbackQuery):
    movie_id = query.data.split('_')[1]
    user_id = query.from_user.id

    delete_movie_from_db(user_id, movie_id)
    delete_tv_from_db(user_id, movie_id)

    await bot.delete_message(chat_id=query.message.chat.id, message_id=query.message.message_id)


# ========================================= Back =========================================  #
@dp.callback_query(lambda query: query.data.startswith('back'))
async def set_back_callback(query: types.CallbackQuery):
    language_code = get_user_language_from_db(query.from_user.id)

    select_option_text = get_text(language_code, 'select_option')

    await bot.edit_message_text(select_option_text, chat_id=query.from_user.id, message_id=query.message.message_id,
                                reply_markup=menu_keyboard(language_code))


# =========================================  Help =========================================  #
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    user_id = message.from_user.id
    language_code = get_user_language_from_db(user_id)

    bot_description = get_text(language_code, 'help_text')

    await message.answer(bot_description, parse_mode=ParseMode.HTML)


# =========================================  Menu =========================================  #
@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    user_id = message.from_user.id
    language_code = get_user_language_from_db(user_id)
    store_message_id_in_db(user_id, 0)
    reset_movies_without_sending_message(user_id)
    menu_message = TEXTS[language_code]['select_menu']

    await message.answer(menu_message, reply_markup=menu_keyboard(language_code))


# =========================================  Saved  =========================================  #
@dp.message(Command("saved"))
async def cmd_menu_for_save(message: types.Message):
    user_id = message.from_user.id
    language_code = get_user_language_from_db(user_id)
    select_option_text = get_text(language_code, 'select_option')

    await send_option_message(message, language_code, select_option_text, "kb")


# ========================================= Search film by id =========================================  #
from aiogram import types
import re


@dp.message()
async def cmd_film(message: types.Message):
    if message.text.startswith('/film'):
        match = re.match(r'^/film(\d+)$', message.text)

        if match:
            film_id = match.group(1)

            await send_content_details_by_content_id(film_id, 'movie', message)
        else:
            await message.answer("Please include a film ID.")
    elif message.text.startswith('/tv'):
        match = re.match(r'^/tv(\d+)$', message.text)
        if match:
            film_id = match.group(1)

            await send_content_details_by_content_id(film_id, 'tv', message)
        else:
            await message.answer("Please include a film ID.")
    else:
        msg_text = await message.answer(
            get_text(get_user_language_from_db(message.from_user.id), 'cannot_read_message'))
        await delete_message_after_delay(7, message.from_user.id, msg_text.message_id)


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
