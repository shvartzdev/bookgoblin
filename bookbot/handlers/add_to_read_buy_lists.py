from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from aiogram.fsm.state import State, StatesGroup

class ToBuyStates(StatesGroup):
    waiting_authors = State()
    waiting_title = State()
    waiting_notes = State()
    waiting_priority = State()

class ToReadStates(StatesGroup):
    waiting_book_search = State()
    waiting_book_selection = State()
    waiting_notes = State()

class DeleteConfirmStates(StatesGroup):
    waiting_confirmation = State()

# ============ TO-BUY-LIST ============

async def get_to_buy_list(message: types.Message):
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, authors, title, notes, priority, added_date
        FROM to_buy_list
        ORDER BY priority DESC, added_date ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить книгу", callback_data="add_to_buy")]
        ])
        await message.answer(
            "📚 Список покупок пуст. Хотите что-то добавить?",
            reply_markup=keyboard
        )
        return
    
    priority_names = {5: "🔥 Очень высокий", 4: "⭐ Высокий", 3: "📖 Средний", 2: "📋 Низкий", 1: "💤 Очень низкий"}
    grouped = {}
    for row in rows:
        priority = row[4]
        if priority not in grouped:
            grouped[priority] = []
        grouped[priority].append(row)
    
    text_parts = ["📚 <b>Список книг к покупке:</b>\n"]
    keyboard_buttons = []
    
    for priority in sorted(grouped.keys(), reverse=True):
        if grouped[priority]:
            text_parts.append(f"\n{priority_names.get(priority, f'Приоритет {priority}')}:")
            for book_id, authors, title, notes, _, added_date in grouped[priority]:
                book_info = []
                if title:
                    book_info.append(f"<b>{title}</b>")
                if authors:
                    book_info.append(f"Автор: {authors}")
                if notes:
                    book_info.append(f"Заметки: {notes}")
                
                text_parts.append(f"• {' | '.join(book_info)} (ID: {book_id})")
                
                # Добавляем кнопки для каждой книги
                book_row = [
                    InlineKeyboardButton(text="📖→📚", callback_data=f"move_to_lib_{book_id}"),
                    InlineKeyboardButton(text="🗑", callback_data=f"delete_buy_{book_id}")
                ]
                keyboard_buttons.append(book_row)
    
    keyboard_buttons.append([InlineKeyboardButton(text="➕ Добавить книгу", callback_data="add_to_buy")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer("\n".join(text_parts), parse_mode="HTML", reply_markup=keyboard)

async def add_to_buy_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ToBuyStates.waiting_authors)
    await callback.message.answer("Введите автора(ов) книги (или отправьте '-' если неизвестно):")

async def add_to_buy_authors(message: types.Message, state: FSMContext):
    authors = message.text.strip()
    if authors == "-":
        authors = None
    
    await state.update_data(authors=authors)
    await state.set_state(ToBuyStates.waiting_title)
    await message.answer("Введите название книги (или отправьте '-' если неизвестно):")

async def add_to_buy_title(message: types.Message, state: FSMContext):
    title = message.text.strip()
    if title == "-":
        title = None
    
    data = await state.get_data()
    authors = data.get("authors")
    
    if not title and not authors:
        await message.answer("Необходимо указать хотя бы автора или название. Введите название книги:")
        return
    
    await state.update_data(title=title)
    await state.set_state(ToBuyStates.waiting_notes)
    await message.answer("Добавьте заметки (или отправьте '-' чтобы пропустить):")

async def add_to_buy_notes(message: types.Message, state: FSMContext):
    notes = message.text.strip()
    if notes == "-":
        notes = None
    
    await state.update_data(notes=notes)
    await state.set_state(ToBuyStates.waiting_priority)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Очень высокий (5)", callback_data="priority_5")],
        [InlineKeyboardButton(text="⭐ Высокий (4)", callback_data="priority_4")],
        [InlineKeyboardButton(text="📖 Средний (3)", callback_data="priority_3")],
        [InlineKeyboardButton(text="📋 Низкий (2)", callback_data="priority_2")],
        [InlineKeyboardButton(text="💤 Очень низкий (1)", callback_data="priority_1")]
    ])
    
    await message.answer("Выберите приоритет:", reply_markup=keyboard)

async def add_to_buy_priority(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    priority = int(callback.data.split("_")[1])
    
    data = await state.get_data()
    authors = data.get("authors")
    title = data.get("title")
    notes = data.get("notes")
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO to_buy_list (authors, title, notes, priority)
        VALUES (?, ?, ?, ?)
    """, (authors, title, notes, priority))
    
    conn.commit()
    conn.close()
    
    book_info = []
    if title:
        book_info.append(f"<b>{title}</b>")
    if authors:
        book_info.append(f"Автор: {authors}")
    
    await callback.message.answer(
        f"✅ Книга добавлена в список покупок:\n{' | '.join(book_info)}",
        parse_mode="HTML"
    )
    await state.clear()


async def delete_buy_confirm(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    book_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    cursor.execute("SELECT authors, title FROM to_buy_list WHERE id = ?", (book_id,))
    book_info = cursor.fetchone()
    conn.close()
    
    if not book_info:
        await callback.message.answer("Книга не найдена.")
        return
    
    authors, title = book_info
    book_display = []
    if title:
        book_display.append(f"<b>{title}</b>")
    if authors:
        book_display.append(f"Автор: {authors}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_delete_buy_{book_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_delete")
        ]
    ])
    
    await callback.message.answer(
        f"Вы уверены, что хотите удалить книгу?\n\n{' | '.join(book_display)} (ID: {book_id})",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def delete_read_confirm(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    trl_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.authors, b.title FROM to_read_list trl
        JOIN books b ON trl.book_id = b.id
        WHERE trl.id = ?
    """, (trl_id,))
    book_info = cursor.fetchone()
    conn.close()
    
    if not book_info:
        await callback.message.answer("Книга не найдена.")
        return
    
    authors, title = book_info
    book_display = [f"<b>{title}</b>"]
    if authors:
        book_display.append(f"Автор: {authors}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_delete_read_{trl_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="cancel_delete")
        ]
    ])
    
    await callback.message.answer(
        f"Вы уверены, что хотите удалить книгу из списка для чтения?\n\n{' | '.join(book_display)} (ID: {trl_id})",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def confirm_delete_buy(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    book_id = int(callback.data.split("_")[3])
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM to_buy_list WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    
    await callback.message.answer("✅ Книга удалена из списка покупок.")

async def confirm_delete_read(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    trl_id = int(callback.data.split("_")[3])
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM to_read_list WHERE id = ?", (trl_id,))
    conn.commit()
    conn.close()
    
    await callback.message.answer("✅ Книга удалена из списка для чтения.")

async def cancel_delete(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("❌ Удаление отменено.")

async def move_to_library(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    book_id = int(callback.data.split("_")[3])
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    cursor.execute("SELECT authors, title, notes FROM to_buy_list WHERE id = ?", (book_id,))
    book_info = cursor.fetchone()
    conn.close()
    
    if not book_info:
        await callback.message.answer("Книга не найдена.")
        return
    
    authors, title, notes = book_info
    
    await state.update_data(
        from_to_buy=True,
        to_buy_id=book_id,
        prefilled_authors=authors,
        prefilled_title=title,
        prefilled_notes=notes
    )
    
    try:
        from .addmanual import addmanual_start  
        await addmanual_start(callback.message, state)
    except ImportError:
        await callback.message.answer("❌ Функция добавления книг не найдена. Обратитесь к разработчику.")

async def mark_as_read(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data_parts = callback.data.split("_")
    trl_id = int(data_parts[2])
    book_id = int(data_parts[3])
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("UPDATE books SET is_read = 1 WHERE id = ?", (book_id,))
    
    cursor.execute("DELETE FROM to_read_list WHERE id = ?", (trl_id,))
    
    cursor.execute("SELECT title, authors FROM books WHERE id = ?", (book_id,))
    book_info = cursor.fetchone()
    
    conn.commit()
    conn.close()
    
    if book_info:
        title, authors = book_info
        book_display = [f"<b>{title}</b>"]
        if authors:
            book_display.append(f"Автор: {authors}")
        
        await callback.message.answer(
            f"✅ Книга помечена как прочитанная:\n{' | '.join(book_display)}",
            parse_mode="HTML"
        )


async def get_to_read_list(message: types.Message):
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT trl.id, b.title, b.authors, b.series_name, b.series_number, trl.notes, trl.added_date, b.id
        FROM to_read_list trl
        JOIN books b ON trl.book_id = b.id
        ORDER BY trl.added_date ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить книгу", callback_data="add_to_read")]
        ])
        await message.answer(
            "📖 Список для чтения пуст. Хотите что-то добавить?",
            reply_markup=keyboard
        )
        return
    
    text_parts = ["📖 <b>Список книг для чтения:</b>\n"]
    keyboard_buttons = []
    
    for trl_id, title, authors, series_name, series_number, notes, added_date, book_id in rows:
        book_info = [f"<b>{title}</b>"]
        if authors:
            book_info.append(f"Автор: {authors}")
        if series_name:
            book_info.append(f"Серия: {series_name} (Том {series_number})")
        if notes:
            book_info.append(f"Заметки: {notes}")
        
        text_parts.append(f"• {' | '.join(book_info)} (ID: {trl_id})")
        
        book_row = [
            InlineKeyboardButton(text="✅ Прочитано", callback_data=f"mark_read_{trl_id}_{book_id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"delete_read_{trl_id}")
        ]
        keyboard_buttons.append(book_row)
    
    keyboard_buttons.append([InlineKeyboardButton(text="➕ Добавить книгу", callback_data="add_to_read")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer("\n".join(text_parts), parse_mode="HTML", reply_markup=keyboard)

async def add_to_read_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ToReadStates.waiting_book_search)
    await callback.message.answer("Найдите книгу в вашей библиотеке. Введите автора, название или серию:")

async def search_for_to_read(message: types.Message, state: FSMContext):
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

    cursor.execute("""
        SELECT b.id, b.title, b.authors, b.pages, b.series_name, b.series_number
        FROM books b
        LEFT JOIN to_read_list trl ON b.id = trl.book_id
        WHERE trl.book_id IS NULL
    """)
    rows = cursor.fetchall()

    filtered = []
    for row in rows:
        id, title, authors, pages, series_name, series_number = row
        searchable_text = " ".join([
            title or "",
            authors or "",
            series_name or ""
        ]).lower()

        if all(word in searchable_text for word in words):
            filtered.append(row)
            if len(filtered) >= 10:
                break

    conn.close()

    if not filtered:
        await message.answer("Ничего не найдено или все найденные книги уже в списке для чтения 😢")
        await state.clear()
        return

    await state.update_data(search_results=filtered)
    await state.set_state(ToReadStates.waiting_book_selection)
    
    text_parts = ["Выберите книгу (отправьте ID):"]
    for book_id, title, authors, pages, series_name, series_number in filtered:
        book_info = [f"<b>{title}</b>"]
        if authors:
            book_info.append(f"Автор: {authors}")
        if series_name:
            book_info.append(f"Серия: {series_name} (Том {series_number})")
        
        text_parts.append(f"ID: {book_id} - {' | '.join(book_info)}")
    
    await message.answer("\n".join(text_parts), parse_mode="HTML")

async def select_book_for_to_read(message: types.Message, state: FSMContext):
    try:
        book_id = int(message.text.strip())
    except ValueError:
        await message.answer("Введите корректный ID книги:")
        return
    
    data = await state.get_data()
    search_results = data.get("search_results", [])
    
    # Проверяем, что выбранная книга есть в результатах поиска
    selected_book = None
    for book in search_results:
        if book[0] == book_id:
            selected_book = book
            break
    
    if not selected_book:
        await message.answer("Книга с таким ID не найдена в результатах поиска. Введите корректный ID:")
        return
    
    await state.update_data(selected_book_id=book_id)
    await state.set_state(ToReadStates.waiting_notes)
    await message.answer("Добавьте заметки к книге (или отправьте '-' чтобы пропустить):")

async def add_to_read_notes(message: types.Message, state: FSMContext):
    notes = message.text.strip()
    if notes == "-":
        notes = None
    
    data = await state.get_data()
    book_id = data.get("selected_book_id")
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    # Получаем информацию о книге для подтверждения
    cursor.execute("SELECT title, authors FROM books WHERE id = ?", (book_id,))
    book_info = cursor.fetchone()
    
    cursor.execute("""
        INSERT INTO to_read_list (book_id, notes)
        VALUES (?, ?)
    """, (book_id, notes))
    
    conn.commit()
    conn.close()
    
    title, authors = book_info
    book_display = [f"<b>{title}</b>"]
    if authors:
        book_display.append(f"Автор: {authors}")
    
    await message.answer(
        f"✅ Книга добавлена в список для чтения:\n{' | '.join(book_display)}",
        parse_mode="HTML"
    )
    await state.clear()

def register_handlers(dp: Dispatcher):
    dp.message.register(get_to_buy_list, Command("gettbr"))
    dp.message.register(get_to_read_list, Command("gettrl"))
    
    dp.callback_query.register(add_to_buy_start, F.data == "add_to_buy")
    dp.callback_query.register(add_to_read_start, F.data == "add_to_read")
    
    dp.callback_query.register(add_to_buy_priority, F.data.startswith("priority_"))
    
    dp.callback_query.register(delete_buy_confirm, F.data.startswith("delete_buy_"))
    dp.callback_query.register(delete_read_confirm, F.data.startswith("delete_read_"))
    dp.callback_query.register(confirm_delete_buy, F.data.startswith("confirm_delete_buy_"))
    dp.callback_query.register(confirm_delete_read, F.data.startswith("confirm_delete_read_"))
    dp.callback_query.register(cancel_delete, F.data == "cancel_delete")
    
    dp.callback_query.register(move_to_library, F.data.startswith("move_to_lib_"))
    dp.callback_query.register(mark_as_read, F.data.startswith("mark_read_"))
    
    dp.message.register(add_to_buy_authors, ToBuyStates.waiting_authors)
    dp.message.register(add_to_buy_title, ToBuyStates.waiting_title)
    dp.message.register(add_to_buy_notes, ToBuyStates.waiting_notes)
    
    dp.message.register(search_for_to_read, ToReadStates.waiting_book_search)
    dp.message.register(select_book_for_to_read, ToReadStates.waiting_book_selection)
    dp.message.register(add_to_read_notes, ToReadStates.waiting_notes)