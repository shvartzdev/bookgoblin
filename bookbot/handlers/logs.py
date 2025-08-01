from aiogram import Dispatcher, types
from aiogram.filters import Command
import sqlite3
from db import get_conn
import logging

logger = logging.getLogger(__name__)

def get_log_summary():
    """Получает краткую и подробную статистику логов"""
    conn = get_conn()
    cursor = conn.cursor()

    try:
        summary = {}

        # Общее количество событий
        cursor.execute('SELECT COUNT(*) FROM book_log')
        summary['total_events'] = cursor.fetchone()[0]

        # Последние 5 событий
        cursor.execute('''
        SELECT id, book_id, event_type, event_date, notes, list_item_id
        FROM book_log
        ORDER BY event_date DESC
        LIMIT 5
        ''')
        recent_logs = cursor.fetchall()
        summary['recent_logs'] = [
            {
                'event_type': row[2],
                'event_date': row[3],
                'book_id': row[1],
                'details': row[4],
                'list_item_id': row[5]
            }
            for row in recent_logs
        ]

        logger.info("Логи успешно получены")
        return summary

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении логов: {e}")
        raise
    finally:
        conn.close()

def format_log_summary(summary):
    """Форматирует информацию о логах для Telegram"""
    if not summary:
        return "Логи пусты"

    formatted = []
    formatted.append("🧾 <b>АКТИВНОСТЬ</b>")
    formatted.append(f"Всего действий: {summary['total_events']}")
    formatted.append("")

    formatted.append("<b>Последние события:</b>")
    if summary['recent_logs']:
        for log in summary['recent_logs']:
            formatted.append(
                f"• <i>{log['event_type']}</i> — {log['event_date']}"
                + (f", книга ID {log['book_id']}" if log['book_id'] else "")
                + (f" — {log['details']}" if log['details'] else "")
            )
    else:
        formatted.append("Нет событий.")
    
    return "\n".join(formatted)

async def cmd_log(message: types.Message):
    summary = get_log_summary()
    text = format_log_summary(summary)
    await message.answer(text, parse_mode="HTML")

def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_log, Command("log"))

