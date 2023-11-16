import telebot
from telebot import types
import config

bot = telebot.TeleBot(config.BOT_TOKEN)


# ====================================== Start ====================================== #
@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot_info = bot.get_me()
    bot.send_message(message.chat.id,
                     f"<b>Welcome to {bot_info.first_name}.</b>\n 🇬🇧 Please select language \n 🇺🇦 Будь ласка, виберіть мову \n "
                     f"🇷🇺 Пожалуйста, выберите язык",
                     reply_markup=language_keyboard(),
                     parse_mode='HTML')
    bot.send_message(message.chat.id, f"Hi, {message.from_user.id}")


# ====================================== Language ====================================== #
def language_keyboard():
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton('🇬🇧 English', callback_data='set_language_en'))
    keyboard.add(types.InlineKeyboardButton('🇺🇦 Українська', callback_data='set_language_ua'))
    keyboard.add(types.InlineKeyboardButton('🇷🇺 Русский', callback_data='set_language_ru'))
    return keyboard


# ====================================== Callbacks ====================================== #
@bot.callback_query_handler(func=lambda call: call.data.startswith('set_language'))
def set_language_callback(call):
    language_code = call.data.split('_')[2]
    set_user_language(call.from_user.id, language_code)
    bot.answer_callback_query(call.id, f"Language set to {language_code}")


def set_user_language(user_id, language_code):
    pass


# ====================================== Help ====================================== #
@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.send_message(message.chat.id, "Welcome, please choose your language:")


# ====================================== Main ====================================== #
bot.polling()
