from aiogram import Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

async def log_book_event(book_id: int, event_type: str, notes: str = None, list_item_id: int = None):
    """
    Логирует событие с книгой в таблицу book_log
    
    Args:
        book_id: ID книги (может быть None для событий с to_buy_list)
        event_type: Тип события из разрешенного списка
        notes: Дополнительные заметки
        list_item_id: ID записи из списка (для связи с to_buy_list или to_read_list)
    """
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO book_log (book_id, event_type, notes, list_item_id)
        VALUES (?, ?, ?, ?)
    """, (book_id, event_type, notes, list_item_id))
    
    conn.commit()
    conn.close()

async def log_to_buy_event(event_type: str, book_id: int = None, list_item_id: int = None, 
                          title: str = None, authors: str = None, notes: str = None):
    """
    Специальная функция для логирования событий to_buy_list
    Для событий где книги еще нет в основной библиотеке
    """

    log_notes = []
    if title:
        log_notes.append(f"Название: {title}")
    if authors:
        log_notes.append(f"Автор: {authors}")
    if notes:
        log_notes.append(f"Заметки: {notes}")
    
    log_description = " | ".join(log_notes) if log_notes else None
    
    await log_book_event(book_id, event_type, log_description, list_item_id)



async def get_book_logs(message: types.Message):
    """Показывает последние записи из логов"""
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            bl.event_type,
            bl.event_date,
            bl.notes,
            b.title,
            b.authors,
            bl.list_item_id
        FROM book_log bl
        LEFT JOIN books b ON bl.book_id = b.id
        ORDER BY bl.event_date DESC
        LIMIT 20
    """)
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        await message.answer("📋 Логи пусты.")
        return
    
    event_translations = {
        'added': '📚 Добавлена в библиотеку',
        'started_reading': '📖 Начато чтение',
        'finished_reading': '✅ Завершено чтение',
        'reviewed': '💭 Добавлен отзыв',
        'moved_to_read_list': '📋 Перенесена в список чтения',
        'added_to_buy_list': '🛒 Добавлена в список покупок',
        'removed_from_buy_list': '🗑 Удалена из списка покупок',
        'moved_from_buy_to_library': '📚 Перенесена из покупок в библиотеку',
        'added_to_read_list': '📋 Добавлена в список чтения',
        'removed_from_read_list': '🗑 Удалена из списка чтения',
        'marked_as_read': '✅ Отмечена как прочитанная',
        'priority_changed': '⏫ Изменен приоритет'
    }
    
    text_parts = ["📋 <b>Последние действия:</b>\n"]
    
    for event_type, event_date, notes, title, authors, list_item_id in rows:
        try:
            date_obj = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
        except:
            formatted_date = event_date
        
        event_name = event_translations.get(event_type, event_type)
        
        book_info = []
        if title:
            book_info.append(f"<b>{title}</b>")
        if authors:
            book_info.append(f"Автор: {authors}")
        
        book_display = " | ".join(book_info) if book_info else "Неизвестная книга"
        
        notes_display = f"\n   💬 {notes}" if notes else ""
        
        text_parts.append(f"🕐 {formatted_date}")
        text_parts.append(f"   {event_name}: {book_display}{notes_display}")
        text_parts.append("") 
    
    if text_parts and text_parts[-1] == "":
        text_parts.pop()
    
    await message.answer("\n".join(text_parts), parse_mode="HTML")

async def get_book_specific_log(message: types.Message):
    """Показывает логи для конкретной книги"""
    try:
        book_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("❌ Укажите ID книги. Пример: /booklog 123")
        return
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT title, authors FROM books WHERE id = ?", (book_id,))
    book_info = cursor.fetchone()
    
    if not book_info:
        conn.close()
        await message.answer("❌ Книга с таким ID не найдена.")
        return
    
    title, authors = book_info
    
    cursor.execute("""
        SELECT event_type, event_date, notes, list_item_id
        FROM book_log
        WHERE book_id = ?
        ORDER BY event_date DESC
    """, (book_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        await message.answer(f"📋 Логи для книги <b>{title}</b> отсутствуют.", parse_mode="HTML")
        return
    
    book_display = [f"<b>{title}</b>"]
    if authors:
        book_display.append(f"Автор: {authors}")
    
    text_parts = [f"📋 <b>История книги:</b> {' | '.join(book_display)}\n"]
    
    event_translations = {
        'added': '📚 Добавлена в библиотеку',
        'started_reading': '📖 Начато чтение',
        'finished_reading': '✅ Завершено чтение',
        'reviewed': '💭 Добавлен отзыв',
        'moved_to_read_list': '📋 Перенесена в список чтения',
        'added_to_read_list': '📋 Добавлена в список чтения',
        'removed_from_read_list': '🗑 Удалена из списка чтения',
        'marked_as_read': '✅ Отмечена как прочитанная'
    }
    
    for event_type, event_date, notes, list_item_id in rows:
        try:
            date_obj = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
            formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
        except:
            formatted_date = event_date
        
        event_name = event_translations.get(event_type, event_type)
        notes_display = f" | {notes}" if notes else ""
        
        text_parts.append(f"🕐 {formatted_date} - {event_name}{notes_display}")
    
    await message.answer("\n".join(text_parts), parse_mode="HTML")

class ToBuyStates(StatesGroup):
    waiting_authors = State()
    waiting_title = State()
    waiting_notes = State()
    waiting_priority = State()

class ToReadStates(StatesGroup):
    waiting_book_search = State()
    waiting_book_selection = State()
    waiting_notes = State()
    waiting_priority = State() 


class ActionStates(StatesGroup):
    waiting_buy_delete_id = State()
    waiting_buy_move_id = State()
    waiting_read_delete_id = State()
    waiting_read_mark_id = State()
    waiting_read_priority_id = State()    
    waiting_new_priority = State()        


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
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖→📚 Перенести в библиотеку", callback_data="move_to_lib_action")],
        [InlineKeyboardButton(text="🗑 Удалить книгу", callback_data="delete_buy_action")],
        [InlineKeyboardButton(text="➕ Добавить книгу", callback_data="add_to_buy")]
    ])
    
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
    
    # Проверяем что хотя бы одно поле заполнено
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
    
    list_item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    await log_to_buy_event('added_to_buy_list', None, list_item_id, title, authors, notes)
    
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


async def move_to_lib_action(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ActionStates.waiting_buy_move_id)
    await callback.message.answer("Введите ID книги, которую хотите перенести в библиотеку:")

async def delete_buy_action(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ActionStates.waiting_buy_delete_id)
    await callback.message.answer("Введите ID книги, которую хотите удалить:")

async def process_buy_move_id(message: types.Message, state: FSMContext):
    try:
        book_id = int(message.text.strip())
    except ValueError:
        await message.answer("Некорректный ID. Введите число:")
        return
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    cursor.execute("SELECT authors, title, notes FROM to_buy_list WHERE id = ?", (book_id,))
    book_info = cursor.fetchone()
    conn.close()
    
    if not book_info:
        await message.answer("Книга с таким ID не найдена. Введите корректный ID:")
        return
    
    authors, title, notes = book_info
    
    await log_to_buy_event('moved_from_buy_to_library', None, book_id, title, authors, notes)
    
    await state.update_data(
        from_to_buy=True,
        to_buy_id=book_id,
        prefilled_authors=authors,
        prefilled_title=title,
        prefilled_notes=notes
    )
    
    try:
        from .addmanual import addmanual_start  
        await addmanual_start(message, state)
    except ImportError:
        await message.answer("❌ Функция добавления книг не найдена. Обратитесь к разработчику.")
        await state.clear()

async def process_buy_delete_id(message: types.Message, state: FSMContext):
    try:
        book_id = int(message.text.strip())
    except ValueError:
        await message.answer("Некорректный ID. Введите число:")
        return
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    cursor.execute("SELECT authors, title, notes FROM to_buy_list WHERE id = ?", (book_id,))
    book_info = cursor.fetchone()
    
    if not book_info:
        conn.close()
        await message.answer("Книга с таким ID не найдена. Введите корректный ID:")
        return
    
    authors, title, notes = book_info
    
    await log_to_buy_event('removed_from_buy_list', None, book_id, title, authors, notes)
    
    cursor.execute("DELETE FROM to_buy_list WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    
    book_display = []
    if title:
        book_display.append(f"<b>{title}</b>")
    if authors:
        book_display.append(f"Автор: {authors}")
    
    await message.answer(
        f"✅ Книга удалена из списка покупок:\n{' | '.join(book_display)}",
        parse_mode="HTML"
    )
    await state.clear()

async def mark_read_action(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ActionStates.waiting_read_mark_id)
    await callback.message.answer("Введите ID книги, которую хотите отметить как прочитанную:")

async def delete_read_action(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ActionStates.waiting_read_delete_id)
    await callback.message.answer("Введите ID книги, которую хотите удалить из списка:")

async def process_read_mark_id(message: types.Message, state: FSMContext):
    try:
        trl_id = int(message.text.strip())
    except ValueError:
        await message.answer("Некорректный ID. Введите число:")
        return
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT b.id, b.title, b.authors, trl.notes FROM to_read_list trl
        JOIN books b ON trl.book_id = b.id
        WHERE trl.id = ?
    """, (trl_id,))
    book_info = cursor.fetchone()
    
    if not book_info:
        conn.close()
        await message.answer("Книга с таким ID не найдена. Введите корректный ID:")
        return
    
    book_id, title, authors, read_notes = book_info
    
    cursor.execute("UPDATE books SET is_read = 1 WHERE id = ?", (book_id,))
    
    cursor.execute("DELETE FROM to_read_list WHERE id = ?", (trl_id,))
    
    conn.commit()
    conn.close()
    
    await log_book_event(book_id, 'marked_as_read', read_notes, trl_id)
    
    book_display = [f"<b>{title}</b>"]
    if authors:
        book_display.append(f"Автор: {authors}")
    
    await message.answer(
        f"✅ Книга отмечена как прочитанная:\n{' | '.join(book_display)}",
        parse_mode="HTML"
    )
    await state.clear()

async def process_read_delete_id(message: types.Message, state: FSMContext):
    try:
        trl_id = int(message.text.strip())
    except ValueError:
        await message.answer("Некорректный ID. Введите число:")
        return
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT b.id, b.title, b.authors, trl.notes FROM to_read_list trl
        JOIN books b ON trl.book_id = b.id
        WHERE trl.id = ?
    """, (trl_id,))
    book_info = cursor.fetchone()
    
    if not book_info:
        conn.close()
        await message.answer("Книга с таким ID не найдена. Введите корректный ID:")
        return
    
    book_id, title, authors, read_notes = book_info
    
    await log_book_event(book_id, 'removed_from_read_list', read_notes, trl_id)
    
    cursor.execute("DELETE FROM to_read_list WHERE id = ?", (trl_id,))
    conn.commit()
    conn.close()
    
    book_display = [f"<b>{title}</b>"]
    if authors:
        book_display.append(f"Автор: {authors}")
    
    await message.answer(
        f"✅ Книга удалена из списка для чтения:\n{' | '.join(book_display)}",
        parse_mode="HTML"
    )
    await state.clear()

# ============ TO-READ-LIST ============

async def get_to_read_list(message: types.Message):
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT trl.id, b.title, b.authors, b.series_name, b.series_number, 
               trl.notes, trl.added_date, b.id, trl.priority
        FROM to_read_list trl
        JOIN books b ON trl.book_id = b.id
        ORDER BY trl.priority DESC, trl.added_date ASC
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
    
    priority_names = {5: "🔥 Очень высокий", 4: "⭐ Высокий", 3: "📖 Средний", 2: "📋 Низкий", 1: "💤 Очень низкий"}
    grouped = {}
    
    for row in rows:
        priority = row[8]  
        if priority not in grouped:
            grouped[priority] = []
        grouped[priority].append(row)
    
    text_parts = ["📖 <b>Список книг для чтения:</b>\n"]
    
    for priority in sorted(grouped.keys(), reverse=True):
        if grouped[priority]:
            text_parts.append(f"\n{priority_names.get(priority, f'Приоритет {priority}')}:")
            
            for trl_id, title, authors, series_name, series_number, notes, added_date, book_id, _ in grouped[priority]:
                book_info = []
                
                if title:
                    book_info.append(f"<b>{title}</b>")
                
                if authors:
                    book_info.append(f"Автор: {authors}")
                
                if series_name:
                    series_info = f"Серия: {series_name}"
                    if series_number:
                        series_info += f" (Том {series_number})"
                    book_info.append(series_info)
                
                if notes:
                    book_info.append(f"Заметки: {notes}")
                
                text_parts.append(f"• {' | '.join(book_info)} (ID: {trl_id})")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏫ Изменить приоритет", callback_data="change_read_priority_action")],
        [InlineKeyboardButton(text="✅ Отметить как прочитанную", callback_data="mark_read_action")],
        [InlineKeyboardButton(text="🗑 Удалить из списка", callback_data="delete_read_action")],
        [InlineKeyboardButton(text="➕ Добавить книгу", callback_data="add_to_read")]
    ])
    
    await message.answer("\n".join(text_parts), parse_mode="HTML", reply_markup=keyboard)

async def change_read_priority_action(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(ActionStates.waiting_read_priority_id)
    await callback.message.answer("Введите ID книги, для которой хотите изменить приоритет:")

async def process_read_priority_id(message: types.Message, state: FSMContext):
    try:
        trl_id = int(message.text.strip())
    except ValueError:
        await message.answer("Некорректный ID. Введите число:")
        return
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT b.title, b.authors, trl.priority FROM to_read_list trl
        JOIN books b ON trl.book_id = b.id
        WHERE trl.id = ?
    """, (trl_id,))
    book_info = cursor.fetchone()
    conn.close()
    
    if not book_info:
        await message.answer("Книга с таким ID не найдена. Введите корректный ID:")
        return
    
    title, authors, current_priority = book_info
    book_display = [f"<b>{title}</b>"]
    if authors:
        book_display.append(f"Автор: {authors}")
    
    priority_names = {5: "🔥 Очень высокий", 4: "⭐ Высокий", 3: "📖 Средний", 2: "📋 Низкий", 1: "💤 Очень низкий"}
    current_priority_name = priority_names.get(current_priority, f'Приоритет {current_priority}')
    
    await state.update_data(trl_id=trl_id)
    await state.set_state(ActionStates.waiting_new_priority)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Очень высокий (5)", callback_data="new_priority_5")],
        [InlineKeyboardButton(text="⭐ Высокий (4)", callback_data="new_priority_4")],
        [InlineKeyboardButton(text="📖 Средний (3)", callback_data="new_priority_3")],
        [InlineKeyboardButton(text="📋 Низкий (2)", callback_data="new_priority_2")],
        [InlineKeyboardButton(text="💤 Очень низкий (1)", callback_data="new_priority_1")]
    ])
    
    await message.answer(
        f"Книга: {' | '.join(book_display)}\n"
        f"Текущий приоритет: {current_priority_name}\n\n"
        f"Выберите новый приоритет:",
        parse_mode="HTML",
        reply_markup=keyboard
    )

async def process_new_priority(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    new_priority = int(callback.data.split("_")[2])  # new_priority_5 -> 5
    
    data = await state.get_data()
    trl_id = data.get("trl_id")
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT b.id, b.title, b.authors, trl.priority FROM to_read_list trl
        JOIN books b ON trl.book_id = b.id
        WHERE trl.id = ?
    """, (trl_id,))
    book_info = cursor.fetchone()
    
    if not book_info:
        conn.close()
        await callback.message.edit_text("❌ Книга не найдена.")
        await state.clear()
        return
    
    book_id, title, authors, old_priority = book_info
    
    cursor.execute("UPDATE to_read_list SET priority = ? WHERE id = ?", (new_priority, trl_id))
    conn.commit()
    conn.close()
    
    priority_names = {5: "🔥 Очень высокий", 4: "⭐ Высокий", 3: "📖 Средний", 2: "📋 Низкий", 1: "💤 Очень низкий"}
    log_note = f"Приоритет изменен с {old_priority} на {new_priority}"
    await log_book_event(book_id, 'priority_changed', log_note, trl_id)
    
    book_display = [f"<b>{title}</b>"]
    if authors:
        book_display.append(f"Автор: {authors}")
    
    await callback.message.edit_text(
        f"✅ Приоритет обновлен:\n{' | '.join(book_display)}\n"
        f"Новый приоритет: {priority_names.get(new_priority, f'Приоритет {new_priority}')}",
        parse_mode="HTML"
    )
    await state.clear()

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
    
    await state.update_data(notes=notes)
    await state.set_state(ToReadStates.waiting_priority)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Очень высокий (5)", callback_data="read_priority_5")],
        [InlineKeyboardButton(text="⭐ Высокий (4)", callback_data="read_priority_4")],
        [InlineKeyboardButton(text="📖 Средний (3)", callback_data="read_priority_3")],
        [InlineKeyboardButton(text="📋 Низкий (2)", callback_data="read_priority_2")],
        [InlineKeyboardButton(text="💤 Очень низкий (1)", callback_data="read_priority_1")]
    ])
    
    await message.answer("Выберите приоритет для чтения:", reply_markup=keyboard)


async def add_to_read_priority(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    priority = int(callback.data.split("_")[2])  # read_priority_5 -> 5
    
    data = await state.get_data()
    book_id = data.get("selected_book_id")
    notes = data.get("notes")
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    # Получаем информацию о книге для подтверждения
    cursor.execute("SELECT title, authors FROM books WHERE id = ?", (book_id,))
    book_info = cursor.fetchone()
    
    cursor.execute("""
        INSERT INTO to_read_list (book_id, notes, priority)
        VALUES (?, ?, ?)
    """, (book_id, notes, priority))
    
    list_item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    await log_book_event(book_id, 'added_to_read_list', notes, list_item_id)
    
    title, authors = book_info
    book_display = [f"<b>{title}</b>"]
    if authors:
        book_display.append(f"Автор: {authors}")
    
    priority_names = {5: "🔥 Очень высокий", 4: "⭐ Высокий", 3: "📖 Средний", 2: "📋 Низкий", 1: "💤 Очень низкий"}
    
    await callback.message.answer(
        f"✅ Книга добавлена в список для чтения:\n{' | '.join(book_display)}\n"
        f"Приоритет: {priority_names.get(priority, f'Приоритет {priority}')}",
        parse_mode="HTML"
    )
    await state.clear()



async def cancel_delete(callback: types.CallbackQuery, state: FSMContext):
    """Отмена удаления книги"""
    await callback.answer()
    await callback.message.edit_text("❌ Удаление отменено.")
    await state.clear()

async def move_to_library(callback: types.CallbackQuery, state: FSMContext):
    """Перемещение книги из списка покупок в библиотеку"""
    await callback.answer()
    
    book_id = int(callback.data.split("_")[-1])
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    # Получаем информацию о книге
    cursor.execute("SELECT authors, title, notes FROM to_buy_list WHERE id = ?", (book_id,))
    book_info = cursor.fetchone()
    
    if not book_info:
        conn.close()
        await callback.message.edit_text("❌ Книга не найдена.")
        return
    
    authors, title, notes = book_info
    
    await state.update_data(
        from_to_buy=True,
        to_buy_id=book_id,
        prefilled_authors=authors,
        prefilled_title=title,
        prefilled_notes=notes
    )
    
    conn.close()
    
    try:
        # Импортируем функцию добавления книги
        from .addmanual import addmanual_start  
        await addmanual_start(callback.message, state)
    except ImportError:
        await callback.message.edit_text("❌ Функция добавления книг не найдена. Обратитесь к разработчику.")
        await state.clear()

async def mark_as_read(callback: types.CallbackQuery, state: FSMContext):
    """Пометка книги как прочитанной"""
    await callback.answer()
    
    trl_id = int(callback.data.split("_")[-1])
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT b.id, b.title, b.authors FROM to_read_list trl
        JOIN books b ON trl.book_id = b.id
        WHERE trl.id = ?
    """, (trl_id,))
    book_info = cursor.fetchone()
    
    if not book_info:
        conn.close()
        await callback.message.edit_text("❌ Книга не найдена.")
        return
    
    book_id, title, authors = book_info
    
    cursor.execute("UPDATE books SET is_read = 1 WHERE id = ?", (book_id,))
    
    cursor.execute("DELETE FROM to_read_list WHERE id = ?", (trl_id,))
    
    conn.commit()
    conn.close()
    
    book_display = [f"<b>{title}</b>"]
    if authors:
        book_display.append(f"Автор: {authors}")
    
    await callback.message.edit_text(
        f"✅ Книга отмечена как прочитанная:\n{' | '.join(book_display)}",
        parse_mode="HTML"
    )
    await state.clear()

async def confirm_delete_read(callback: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления книги из списка для чтения"""
    await callback.answer()
    
    # Получаем ID записи из callback_data (формат: confirm_delete_read_{trl_id})
    trl_id = int(callback.data.split("_")[-1])
    
    conn = sqlite3.connect("data/library.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT b.title, b.authors FROM to_read_list trl
        JOIN books b ON trl.book_id = b.id
        WHERE trl.id = ?
    """, (trl_id,))
    book_info = cursor.fetchone()
    
    if not book_info:
        conn.close()
        await callback.message.edit_text("❌ Книга не найдена.")
        return
    
    title, authors = book_info
    
    cursor.execute("DELETE FROM to_read_list WHERE id = ?", (trl_id,))
    conn.commit()
    conn.close()
    
    book_display = [f"<b>{title}</b>"]
    if authors:
        book_display.append(f"Автор: {authors}")
    
    await callback.message.edit_text(
        f"✅ Книга удалена из списка для чтения:\n{' | '.join(book_display)}",
        parse_mode="HTML"
    )
    await state.clear()

def register_handlers(dp: Dispatcher):
    # Команды
    dp.message.register(get_to_buy_list, Command("gettbr"))
    dp.message.register(get_to_read_list, Command("gettrl"))
    
    # Callback'и для кнопок добавления
    dp.callback_query.register(add_to_buy_start, F.data == "add_to_buy")
    dp.callback_query.register(add_to_read_start, F.data == "add_to_read")
    
    # Callback'и для действий
    dp.callback_query.register(move_to_lib_action, F.data == "move_to_lib_action")
    dp.callback_query.register(delete_buy_action, F.data == "delete_buy_action")
    dp.callback_query.register(mark_read_action, F.data == "mark_read_action")
    dp.callback_query.register(delete_read_action, F.data == "delete_read_action")
    
    # Callback'и для подтверждения действий
    dp.callback_query.register(confirm_delete_read, F.data.startswith("confirm_delete_read_"))
    dp.callback_query.register(cancel_delete, F.data == "cancel_delete")
    
    # Обработка перемещения и пометки как прочитанное
    dp.callback_query.register(move_to_library, F.data.startswith("move_to_lib_"))
    dp.callback_query.register(mark_as_read, F.data.startswith("mark_read_"))
    
    # Обработка приоритетов для to-buy-list
    dp.callback_query.register(add_to_buy_priority, F.data.startswith("priority_"))
    
    # Состояния для добавления в to-buy-list
    dp.message.register(add_to_buy_authors, ToBuyStates.waiting_authors)
    dp.message.register(add_to_buy_title, ToBuyStates.waiting_title)
    dp.message.register(add_to_buy_notes, ToBuyStates.waiting_notes)
    
    # Состояния для добавления в to-read-list
    dp.message.register(search_for_to_read, ToReadStates.waiting_book_search)
    dp.message.register(select_book_for_to_read, ToReadStates.waiting_book_selection)
    dp.message.register(add_to_read_notes, ToReadStates.waiting_notes)
    
    # Состояния для действий по ID
    dp.message.register(process_buy_move_id, ActionStates.waiting_buy_move_id)
    dp.message.register(process_buy_delete_id, ActionStates.waiting_buy_delete_id)
    dp.message.register(process_read_mark_id, ActionStates.waiting_read_mark_id)
    dp.message.register(process_read_delete_id, ActionStates.waiting_read_delete_id)

    dp.callback_query.register(add_to_read_priority, F.data.startswith("read_priority_"))
    dp.callback_query.register(change_read_priority_action, F.data == "change_read_priority_action")
    dp.callback_query.register(process_new_priority, F.data.startswith("new_priority_"))
    
    # Обновленные состояния
    dp.message.register(add_to_read_notes, ToReadStates.waiting_notes)
    dp.message.register(process_read_priority_id, ActionStates.waiting_read_priority_id)

    dp.message.register(get_book_logs, Command("logs"))
    dp.message.register(get_book_specific_log, Command("booklog"))