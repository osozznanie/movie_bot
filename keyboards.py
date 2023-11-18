from aiogram import types


def get_next_action_message(language_code):
    messages = {
        'en': '<b>Menu\n</b>Please select the next action:',
        'ua': '<b>Меню\n</b>Будь ласка, виберіть наступну дію:',
        'ru': '<b>Меню\n</b>Пожалуйста, выберите следующее действие:',
    }
    return messages.get(language_code, 'Please select the next action')


def get_rating_mod(language_code):
    options = {
        'en': ['Starting from low', 'Starting from high'],
        'ua': ['Починаючи з низького', 'Починаючи з високого'],
        'ru': ['Начиная с низкого', 'Начиная с высокого'],
    }

    option_texts = options.get(language_code, options['en'])

    keyboard = [
        [types.InlineKeyboardButton(text=option_texts[0], callback_data=f'sort_option_low_{language_code}')],
        [types.InlineKeyboardButton(text=option_texts[1], callback_data=f'sort_option_high_{language_code}')]
    ]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return "Please select an option:", keyboard_markup


def language_keyboard():
    keyboard = [[types.InlineKeyboardButton(text='🇬🇧 English', callback_data='set_language_en')],
                [types.InlineKeyboardButton(text='🇺🇦 Українська', callback_data='set_language_ua')],
                [types.InlineKeyboardButton(text='🇷🇺 Русский', callback_data='set_language_ru')], ]

    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return keyboard_markup


def menu_keyboard(language_code):
    options = {
        'en': ['Movies', 'Series', 'Randomizer', 'Saved'],
        'ua': ['Фільми', 'Серіали', 'Рандомайзер', 'Збережене'],
        'ru': ['Фильмы', 'Сериалы', 'Рандомайзер', 'Сохранённое'],
    }

    option_texts = options.get(language_code, options[language_code])

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


def submenu_keyboard(language_code):
    options = {
        'en': ['Popular Now', 'By TMDB Rating', 'By Genre'],
        'ua': ['Популярне зараз', 'За рейтингом TMDB', 'За жанром'],
        'ru': ['Популярно сейчас', 'По рейтингу TMDB', 'По жанру'],
    }

    option_texts = options.get(language_code, options['en'])

    keyboard = [
        [types.InlineKeyboardButton(text=option_texts[0], callback_data=f'submenu_option_1_{language_code}')],
        [types.InlineKeyboardButton(text=option_texts[1], callback_data=f'submenu_option_2_{language_code}')],
        [types.InlineKeyboardButton(text=option_texts[2], callback_data=f'submenu_option_3_{language_code}')]

    ]
    keyboard_markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)

    return keyboard_markup