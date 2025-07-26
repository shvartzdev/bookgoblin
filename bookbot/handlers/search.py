from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import sqlite3
from aiogram.fsm.state import State, StatesGroup

class SearchStates(StatesGroup):
    waiting_query = State()

async def search_start(message: types.Message, state: FSMContext):
    await state.set_state(SearchStates.waiting_query)
    await message.answer("Введите автора, название книги или название серии:")

async def search_books(message: types.Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer("Пустой запрос. Введите снова:")
        return

    words = query.lower().split()
    if not words:
        await message.answer("Пустой запрос. Введите снова:")
        return

    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()

    # Загружаем все данные, которые нужны для поиска
    cursor.execute("""
        SELECT id, title, authors, pages, series_name, series_number
        FROM books
    """)
    rows = cursor.fetchall()

    # Фильтрация в Python
    filtered = []
    for row in rows:
        id, title, authors, pages, series_name, series_number = row
        # Конкатенируем все текстовые поля в один большой текст для удобства
        searchable_text = " ".join([
            title or "",
            authors or "",
            series_name or ""
        ]).lower()

        if all(word in searchable_text for word in words):
            filtered.append(row)
            if len(filtered) >= 10:  # лимит результатов
                break

    conn.close()

    if not filtered:
        await message.answer("Ничего не найдено 😢")
    else:
        text = "\n\n".join(
            f"<b>{title}</b> (ID: {book_id})\n"
            f"Автор: {authors}"
            + (f"\nСерия: {series_name} (Том {series_number})" if series_name else "")
            + (f"\nСтраниц: {pages}" if pages else "")
            for book_id, title, authors, pages, series_name, series_number in filtered
        )
        await message.answer(text, parse_mode="HTML")

    await state.clear()




def register_handlers(dp: Dispatcher):
    dp.message.register(search_start, Command("search"))
    dp.message.register(search_books, SearchStates.waiting_query)
