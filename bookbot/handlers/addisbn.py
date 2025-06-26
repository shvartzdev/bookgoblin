from aiogram import types, Dispatcher, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.filters import Command
import requests
import re
from db import add_book
import logging

logger = logging.getLogger(__name__)

class AddBookISBNStates(StatesGroup):
    waiting_isbn = State()

async def addisbn_start(message: types.Message, state: FSMContext):
    await state.set_state(AddBookISBNStates.waiting_isbn)
    await message.answer("📚 Введите ISBN (10 или 13 цифр, без тире):")

async def addisbn_received(message: types.Message, state: FSMContext):
    raw_isbn = message.text.strip()
    isbn = re.sub(r"\D", "", raw_isbn)
    if len(isbn) not in (10, 13):
        await message.answer("❌ Неверный ISBN, попробуйте снова.")
        return
    await message.answer("🔍 Ищу книгу...")
    try:
        url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
        resp = requests.get(url, timeout=10).json()
        key = f"ISBN:{isbn}"
        if key not in resp:
            await message.answer("❌ Книга не найдена.")
            await state.clear()
            return
        data = resp[key]
        book = {
            "isbn": isbn,
            "title": data.get("title", ""),
            "authors": ", ".join([a["name"] for a in data.get("authors", [])]) if "authors" in data else "",
            "description": data.get("notes", "") if isinstance(data.get("notes", ""), str) else "",
            "year": data.get("publish_date", "")[-4:] if data.get("publish_date") else "0",
            "pages": data.get("number_of_pages", 0),
            "publisher": ", ".join(data.get("publishers", [])) if "publishers" in data else "",
            "genre": "",
        }
        book_id = add_book(
            authors=book["authors"],
            title=book["title"],
            description=book["description"],
            isbn=book["isbn"],
            format_type="physical",
            year=int(book["year"]) if book["year"].isdigit() else 0,
            pages=int(book["pages"]) if isinstance(book["pages"], int) else 0,
            publisher=book["publisher"],
            genre=book["genre"],
            url=None
        )
        await message.answer(f"✅ Книга добавлена! ID {book_id}")
    except Exception as e:
        logger.error(e)
        await message.answer("❌ Ошибка или книга не найдена.")
    await state.clear()

def register_handlers(dp: Dispatcher):
    dp.message.register(addisbn_start, Command("addisbn"))
    dp.message.register(addisbn_received, AddBookISBNStates.waiting_isbn)
