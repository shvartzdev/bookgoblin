from aiogram import types, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command

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
    await message.answer("Формат книги? Введите 'physical' или 'digital':")

async def addmanual_format(message: types.Message, state: FSMContext):
    fmt = message.text.lower()
    if fmt not in {"physical", "digital"}:
        await message.answer("Формат должен быть 'physical' или 'digital'. Попробуйте снова.")
        return
    await state.update_data(format=fmt)
    await state.set_state(AddBookManualStates.waiting_source)
    await message.answer("Источник? Введите 'shop', 'author.today' или 'fic':")

async def addmanual_source(message: types.Message, state: FSMContext):
    source = message.text.lower()
    if source not in {"shop", "author.today", "fic"}:
        await message.answer("Источник должен быть 'shop', 'author.today' или 'fic'. Попробуйте снова.")
        return
    await state.update_data(source=source)
    await state.set_state(AddBookManualStates.waiting_year)
    await message.answer("Введите год публикации (от 1001 до 2030):")

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
    await state.set_state(AddBookManualStates.waiting_url)
    await message.answer("Введите URL (или напишите 'Пропустить', если не хотите указывать):")

async def addmanual_url(message: types.Message, state: FSMContext):
    url = message.text
    if url.lower() == "пропустить":
        url = ""
    await state.update_data(url=url)
    
    data = await state.get_data()

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
        url=data.get("url", "")
    )

    await message.answer(f"✅ Книга добавлена вручную! ID {book_id}")
    await state.clear()


def register_handlers(dp: Dispatcher):
    dp.message.register(addmanual_start, Command("addmanual"))
    dp.message.register(addmanual_title, AddBookManualStates.waiting_title)
    dp.message.register(addmanual_authors, AddBookManualStates.waiting_authors)
    dp.message.register(addmanual_format, AddBookManualStates.waiting_format)
    dp.message.register(addmanual_source, AddBookManualStates.waiting_source)
    dp.message.register(addmanual_year, AddBookManualStates.waiting_year)
    dp.message.register(addmanual_pages, AddBookManualStates.waiting_pages)
    dp.message.register(addmanual_publisher, AddBookManualStates.waiting_publisher)
    dp.message.register(addmanual_genre, AddBookManualStates.waiting_genre)
    dp.message.register(addmanual_description, AddBookManualStates.waiting_description)
    dp.message.register(addmanual_isbn, AddBookManualStates.waiting_isbn)
    dp.message.register(addmanual_url, AddBookManualStates.waiting_url)
