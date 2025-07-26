from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

format_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📘 Цифровая", callback_data="format:digital"),
            InlineKeyboardButton(text="📕 Физическая", callback_data="format:physical"),
        ]
    ]
)

source_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🛍 Магазин", callback_data="source:shop"),
            InlineKeyboardButton(text="✍ Author.Today", callback_data="source:author.today"),
            InlineKeyboardButton(text="📖 Фикбук", callback_data="source:ficbook"),
            InlineKeyboardButton(text="📖 ao3", callback_data="source:ao3")
        ]
    ]
)

yes_no_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Да"), KeyboardButton(text="Нет")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True  # клавиатура пропадёт после выбора
)