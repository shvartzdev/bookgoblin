from aiogram import types, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from .keyboards import format_keyboard, source_keyboard, yes_no_keyboard
from db import add_book


class AddBookManualStates(StatesGroup):
    waiting_title = State()
    waiting_authors = State()
    waiting_format = State()
    waiting_source = State()
    waiting_year = State()
    waiting_pages = State()
    waiting_publisher = State()
    waiting_genre = State()
    waiting_description = State()
    waiting_isbn = State()
    waiting_url = State()
    waiting_is_series = State()
    waiting_series_title = State()
    waiting_series_number = State()
    waiting_is_read = State()
    waiting_confirmation = State()


async def addmanual_start(message: types.Message, state: FSMContext):
    await state.set_state(AddBookManualStates.waiting_title)
    await message.answer("Введите название книги:")


async def addmanual_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddBookManualStates.waiting_authors)
    await message.answer("Введите автора(ов) книги:")


async def addmanual_authors(message: types.Message, state: FSMContext):
    await state.update_data(authors=message.text)
    await state.set_state(AddBookManualStates.waiting_format)
    await message.answer("Выберите формат книги:", reply_markup=format_keyboard)


async def format_chosen(callback: types.CallbackQuery, state: FSMContext):
    fmt = callback.data.split(":", 1)[1]
    await state.update_data(format=fmt)
    await state.set_state(AddBookManualStates.waiting_source)
    await callback.message.edit_text("Выберите источник:", reply_markup=source_keyboard)
    await callback.answer()


async def source_chosen(callback: types.CallbackQuery, state: FSMContext):
    source = callback.data.split(":", 1)[1]
    await state.update_data(source=source)
    await state.set_state(AddBookManualStates.waiting_year)
    await callback.message.edit_text("Введите год публикации (от 1001 до 2030):")
    await callback.answer()


async def addmanual_year(message: types.Message, state: FSMContext):
    year_text = message.text
    if not year_text.isdigit() or not (1001 <= int(year_text) <= 2030):
        await message.answer("Год должен быть числом от 1001 до 2030. Попробуйте снова.")
        return
    await state.update_data(year=int(year_text))
    await state.set_state(AddBookManualStates.waiting_pages)
    await message.answer("Сколько страниц в книге?")


async def addmanual_pages(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("Введите количество страниц (целое число > 0):")
        return
    await state.update_data(pages=int(message.text))
    await state.set_state(AddBookManualStates.waiting_publisher)
    await message.answer("Введите издателя (можно оставить пустым):")


async def addmanual_publisher(message: types.Message, state: FSMContext):
    await state.update_data(publisher=message.text)
    await state.set_state(AddBookManualStates.waiting_genre)
    await message.answer("Введите жанр (можно оставить пустым):")


async def addmanual_genre(message: types.Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await state.set_state(AddBookManualStates.waiting_description)
    await message.answer("Введите описание (можно оставить пустым):")


async def addmanual_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddBookManualStates.waiting_isbn)
    await message.answer("Введите ISBN (можно оставить пустым):")


async def addmanual_isbn(message: types.Message, state: FSMContext):
    await state.update_data(isbn=message.text)
    data = await state.get_data()

    if data.get("format") == "digital":
        await state.set_state(AddBookManualStates.waiting_url)
        await message.answer("Введите URL (или напишите 'Пропустить', если не хотите указывать):")
    else:
        # Если формат не digital — сразу спрашиваем про серию
        await ask_is_series(message, state)


async def addmanual_url(message: types.Message, state: FSMContext):
    url = "" if message.text.lower() == "пропустить" else message.text
    await state.update_data(url=url)
    await ask_is_series(message, state)


async def ask_is_series(message: types.Message, state: FSMContext):
    await state.set_state(AddBookManualStates.waiting_is_series)
    await message.answer("Относится ли книга к серии?", reply_markup=yes_no_keyboard)


async def is_series_chosen(message: types.Message, state: FSMContext):
    answer = message.text.lower()
    if answer == "да":
        await state.set_state(AddBookManualStates.waiting_series_title)
        await message.answer("Введите название серии:", reply_markup=ReplyKeyboardRemove())
    elif answer == "нет":
        await state.set_state(AddBookManualStates.waiting_is_read)
        await message.answer("Книга прочитана?", reply_markup=yes_no_keyboard)
    else:
        await message.answer("Пожалуйста, выберите 'Да' или 'Нет'.")



async def series_title(message: types.Message, state: FSMContext):
    await state.update_data(series_title=message.text)
    await state.set_state(AddBookManualStates.waiting_series_number)
    await message.answer("Введите номер книги в серии (число):")


async def series_number(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число для номера книги в серии.")
        return
    await state.update_data(series_number=int(message.text))
    await state.set_state(AddBookManualStates.waiting_is_read)
    await message.answer("Книга прочитана?", reply_markup=yes_no_keyboard)


def format_book_summary(data: dict) -> str:
    lines = [
        f"Название: {data.get('title', '')}",
        f"Автор(ы): {data.get('authors', '')}",
        f"Формат: {data.get('format', '')}",
        f"Источник: {data.get('source', '')}",
        f"Год: {data.get('year', '')}",
        f"Страниц: {data.get('pages', '')}",
        f"Издатель: {data.get('publisher', '')}",
        f"Жанр: {data.get('genre', '')}",
        f"Описание: {data.get('description', '')}",
        f"ISBN: {data.get('isbn', '')}",
        f"URL: {data.get('url', '')}",
    ]

    if data.get("series_title"):
        lines.append(f"Серия: {data['series_title']}")
        lines.append(f"Номер в серии: {data.get('series_number', '')}")
    else:
        lines.append("Серия: нет")

    lines.append(f"Книга прочитана: {'Да' if data.get('is_read') else 'Нет'}")

    return "\n".join(lines)


async def is_read_chosen(message: types.Message, state: FSMContext):
    answer = message.text.lower()
    if answer not in {"да", "нет"}:
        await message.answer("Пожалуйста, выберите 'Да' или 'Нет'.")
        return
    is_read = answer == "да"
    await state.update_data(is_read=is_read)

    data = await state.get_data()
    summary = format_book_summary(data)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no"),
        ]
    ])

    # Убираем ReplyKeyboard, если был
    await message.answer(f"Проверьте введённые данные:\n\n{summary}\n\nДобавить книгу?", reply_markup=kb)
    await state.set_state(AddBookManualStates.waiting_confirmation)


async def finish_adding_book(message_or_callback, state: FSMContext, url=""):
    data = await state.get_data()
    # На случай, если url передали явно (например, пустую строку)
    if url:
        data["url"] = url

    book_id = add_book(
        authors=data.get("authors"),
        title=data.get("title"),
        description=data.get("description", ""),
        isbn=data.get("isbn", ""),
        format_type=data.get("format"),
        source=data.get("source"),
        year=data.get("year"),
        pages=data.get("pages"),
        publisher=data.get("publisher", ""),
        genre=data.get("genre", ""),
        url=data.get("url", ""),
        series_name=data.get("series_title", ""),  # <- здесь ключ 'series_title' соответствует новому столбцу 'series_name'
        series_number=data.get("series_number"),
        is_read=data.get("is_read", False)
    )

    # Проверяем тип объекта, чтобы ответить правильно
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(f"✅ Книга добавлена вручную! ID {book_id}")
    elif isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(f"✅ Книга добавлена вручную! ID {book_id}", reply_markup=None)
        await message_or_callback.answer()

    await state.clear()


async def confirm_chosen(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "confirm_yes":
        await finish_adding_book(callback, state)
    elif callback.data == "confirm_no":
        await callback.message.edit_text("❌ Добавление книги отменено.", reply_markup=None)
        await state.clear()
        await callback.answer()


def register_handlers(dp: Dispatcher):
    dp.message.register(addmanual_start, Command("addmanual"))
    dp.message.register(addmanual_title, AddBookManualStates.waiting_title)
    dp.message.register(addmanual_authors, AddBookManualStates.waiting_authors)
    dp.callback_query.register(format_chosen, F.data.startswith("format:"), AddBookManualStates.waiting_format)
    dp.callback_query.register(source_chosen, F.data.startswith("source:"), AddBookManualStates.waiting_source)
    dp.message.register(addmanual_year, AddBookManualStates.waiting_year)
    dp.message.register(addmanual_pages, AddBookManualStates.waiting_pages)
    dp.message.register(addmanual_publisher, AddBookManualStates.waiting_publisher)
    dp.message.register(addmanual_genre, AddBookManualStates.waiting_genre)
    dp.message.register(addmanual_description, AddBookManualStates.waiting_description)
    dp.message.register(addmanual_isbn, AddBookManualStates.waiting_isbn)
    dp.message.register(addmanual_url, AddBookManualStates.waiting_url)

    dp.message.register(is_series_chosen, AddBookManualStates.waiting_is_series)
    dp.message.register(series_title, AddBookManualStates.waiting_series_title)
    dp.message.register(series_number, AddBookManualStates.waiting_series_number)
    dp.message.register(is_read_chosen, AddBookManualStates.waiting_is_read)

    dp.callback_query.register(confirm_chosen, F.data.startswith("confirm_"), AddBookManualStates.waiting_confirmation)
