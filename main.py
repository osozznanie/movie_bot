# Description: Main file for bot logic and handlers (client side)

import telebot
import tmdbsimple as tmdb

import api
import config


tmdb.API_KEY = api.TMDB_API_KEY
bot = telebot.TeleBot(config.BOT_TOKEN)
bot.parse_mode = 'HTML'
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'


# ========================================= Client side ========================================= #
@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot_info = bot.get_me()
    bot.send_message(
        message.chat.id,
        f"<b>Welcome to {bot_info.first_name}.</b>\n 🇬🇧 Please select language \n 🇺🇦 Будь ласка, виберіть мову \n "
        f"🇷🇺 Пожалуйста, выберите язык", reply_markup=language_keyboard(), parse_mode='HTML')


# ========================================= Language =========================================  #
user_languages = {}


@bot.message_handler(commands=['language'])
def cmd_language(message):
    bot.send_message(message.chat.id, "Please select language:", reply_markup=language_keyboard())


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_language'))
def set_language_callback(call):
    language_code = call.data.split('_')[2]
    set_user_language(call.from_user.id, language_code)
    next_action_message = get_next_action_message(language_code)
    bot.send_message(call.from_user.id, next_action_message, reply_markup=menu_keyboard(language_code))
    bot.answer_callback_query(call.id, f"Language set to {language_code}")
    bot.edit_message_reply_markup(call.from_user.id, call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_option'))
def set_menu_callback(call):
    menu_code = call.data.split('_')[2]
    language_code = call.data.split('_')[3]

    if menu_code == '1' or menu_code == '2':
        keyboard_markup = submenu_keyboard(language_code)
        bot.edit_message_text("Please select an option:", chat_id=call.from_user.id, message_id=call.message.message_id,
                              reply_markup=keyboard_markup)
    elif menu_code == '3':
        bot.send_message(call.from_user.id, "You selected the third menu option.")
    elif menu_code == '4':
        bot.send_message(call.from_user.id, "You selected the fourth menu option.")


@bot.callback_query_handler(func=lambda call: call.data.startswith('submenu_option'))
def set_submenu_callback(call):
    submenu_code = call.data.split('_')[2]
    language_code = call.data.split('_')[3]

    if submenu_code == '1':
        discover = tmdb.Discover()
        response = discover.movie(sort_by='popularity.desc')

        for movie in response['results'][:3]:
            title = movie['title']
            rating = movie['vote_average']
            poster_url = f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"

            bot.send_message(call.message.chat.id, f"Poster:{poster_url} \n Title: {title}\nRating: {rating}\n")
            bot.send_photo(chat_id=call.message.chat.id, photo=poster_url)


def get_next_action_message(language_code):
    messages = {
        'en': '<b>Menu\n</b>Please select the next action:',
        'ua': '<b>Меню\n</b>Будь ласка, виберіть наступну дію:',
        'ru': '<b>Меню\n</b>Пожалуйста, выберите следующее действие:',
    }
    return messages.get(language_code, 'Please select the next action')


def language_keyboard():
    keyboard_markup = telebot.types.InlineKeyboardMarkup()
    keyboard_markup.add(telebot.types.InlineKeyboardButton(text='🇬🇧 English', callback_data='set_language_en'))
    keyboard_markup.add(telebot.types.InlineKeyboardButton(text='🇺🇦 Українська', callback_data='set_language_ua'))
    keyboard_markup.add(telebot.types.InlineKeyboardButton(text='🇷🇺 Русский', callback_data='set_language_ru'))

    return keyboard_markup


def menu_keyboard(language_code):
    options = {
        'en': ['Movies', 'Series', 'Randomizer', 'Saved'],
        'ua': ['Фільми', 'Серіали', 'Рандомайзер', 'Збережене'],
        'ru': ['Фильмы', 'Сериалы', 'Рандомайзер', 'Сохранённое'],
    }

    option_texts = options.get(language_code, options['en'])

    keyboard_markup = telebot.types.InlineKeyboardMarkup()
    keyboard_markup.add(
        telebot.types.InlineKeyboardButton(text=option_texts[0], callback_data=f'menu_option_1_{language_code}'))
    keyboard_markup.add(
        telebot.types.InlineKeyboardButton(text=option_texts[1], callback_data=f'menu_option_2_{language_code}'))
    keyboard_markup.add(
        telebot.types.InlineKeyboardButton(text=option_texts[2], callback_data=f'menu_option_3_{language_code}'))
    keyboard_markup.add(
        telebot.types.InlineKeyboardButton(text=option_texts[3], callback_data=f'menu_option_4_{language_code}'))

    return keyboard_markup


def submenu_keyboard(language_code):
    options = {
        'en': ['Popular Now', 'By TMDB Rating', 'By Genre'],
        'ua': ['Популярне зараз', 'За рейтингом TMDB', 'За жанром'],
        'ru': ['Популярно сейчас', 'По рейтингу TMDB', 'По жанру'],
    }

    option_texts = options.get(language_code, options['en'])

    keyboard_markup = telebot.types.InlineKeyboardMarkup()
    keyboard_markup.add(
        telebot.types.InlineKeyboardButton(text=option_texts[0], callback_data=f'submenu_option_1_{language_code}'))
    keyboard_markup.add(
        telebot.types.InlineKeyboardButton(text=option_texts[1], callback_data=f'submenu_option_2_{language_code}'))
    keyboard_markup.add(
        telebot.types.InlineKeyboardButton(text=option_texts[2], callback_data=f'submenu_option_3_{language_code}'))

    return keyboard_markup


def set_user_language(user_id, language_code):
    user_languages[user_id] = language_code


# =========================================  Help =========================================  #
@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.send_message(message.chat.id, "Welcome, please choose your language:")


# ========================================= Testing and Exception Handling =========================================
bot.polling()
