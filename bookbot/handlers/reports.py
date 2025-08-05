from aiogram import Dispatcher, types, Bot
from aiogram.filters import Command
import sqlite3
from db import get_conn
import logging
from datetime import datetime, timedelta
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import calendar

logger = logging.getLogger(__name__)

# Глобальные переменные для планировщика
scheduler = None
bot_instance = None
user_id = None  # ID пользователя для отправки автоматических отчетов

def get_monthly_reading_report():
    """Получает отчет о прочитанных книгах за текущий календарный месяц"""
    conn = get_conn()
    cursor = conn.cursor()

    try:
        # Начало текущего месяца
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1, 0, 0, 0)
        month_start_str = month_start.strftime('%Y-%m-%d %H:%M:%S')

        # Получаем все события "finished_reading" за текущий календарный месяц с информацией о книгах
        cursor.execute('''
        SELECT 
            bl.id,
            bl.book_id,
            bl.event_date,
            bl.notes,
            b.title,
            b.authors,
            b.series_name,
            b.series_number,
            b.pages,
            b.format
        FROM book_log bl
        JOIN books b ON bl.book_id = b.id
        WHERE bl.event_type = 'finished_reading' 
        AND bl.event_date >= ?
        ORDER BY bl.event_date DESC
        ''', (month_start_str,))
        
        finished_books = cursor.fetchall()
        
        # Получаем также события "marked_as_read" (если используется)
        cursor.execute('''
        SELECT 
            bl.id,
            bl.book_id,
            bl.event_date,
            bl.notes,
            b.title,
            b.authors,
            b.series_name,
            b.series_number,
            b.pages,
            b.format
        FROM book_log bl
        JOIN books b ON bl.book_id = b.id
        WHERE bl.event_type = 'marked_as_read' 
        AND bl.event_date >= ?
        ORDER BY bl.event_date DESC
        ''', (month_start_str,))
        
        marked_books = cursor.fetchall()
        
        # Объединяем результаты и удаляем дубликаты по book_id
        all_books = {}
        
        for book in finished_books + marked_books:
            book_id = book[1]
            # Если книга уже есть, берем более позднюю дату
            if book_id not in all_books or book[2] > all_books[book_id][2]:
                all_books[book_id] = book
        
        # Преобразуем в список и сортируем по дате
        books_list = list(all_books.values())
        books_list.sort(key=lambda x: x[2], reverse=True)
        
        # Подсчитываем статистику
        total_books = len(books_list)
        total_pages = sum(book[8] for book in books_list if book[8])
        
        result = {
            'books': books_list,
            'total_books': total_books,
            'total_pages': total_pages,
            'period': month_start.strftime('%d.%m.%Y'),
            'month_name': month_start.strftime('%B %Y')  # название месяца для отображения
        }
        
        logger.info(f"Получен отчет о чтении за {month_start.strftime('%B %Y')}: {total_books} книг")
        return result

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении отчета о чтении: {e}")
        raise
    finally:
        conn.close()

def get_monthly_purchases_report():
    """Получает отчет о купленных книгах за текущий календарный месяц"""
    conn = get_conn()
    cursor = conn.cursor()

    try:
        # Начало текущего месяца
        now = datetime.now()
        month_start = datetime(now.year, now.month, 1, 0, 0, 0)
        month_start_str = month_start.strftime('%Y-%m-%d %H:%M:%S')

        # Получаем все события покупки за текущий календарный месяц
        cursor.execute('''
        SELECT 
            bl.id,
            bl.book_id,
            bl.event_date,
            bl.notes,
            b.title,
            b.authors,
            b.series_name,
            b.series_number,
            b.format,
            b.source
        FROM book_log bl
        JOIN books b ON bl.book_id = b.id
        WHERE bl.event_type IN ('moved_from_buy_to_library', 'added') 
        AND bl.event_date >= ?
        AND b.source = 'shop'
        ORDER BY bl.event_date DESC
        ''', (month_start_str,))
        
        purchased_books = cursor.fetchall()
        
        # Удаляем дубликаты по book_id (берем последнее событие)
        unique_books = {}
        for book in purchased_books:
            book_id = book[1]
            if book_id not in unique_books or book[2] > unique_books[book_id][2]:
                unique_books[book_id] = book
        
        books_list = list(unique_books.values())
        books_list.sort(key=lambda x: x[2], reverse=True)
        
        result = {
            'books': books_list,
            'total_books': len(books_list),
            'period': month_start.strftime('%d.%m.%Y'),
            'month_name': month_start.strftime('%B %Y')  # название месяца для отображения
        }
        
        logger.info(f"Получен отчет о покупках за {month_start.strftime('%B %Y')}: {len(books_list)} книг")
        return result

    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении отчета о покупках: {e}")
        raise
    finally:
        conn.close()

def format_reading_report(report):
    """Форматирует отчет о прочитанном для Telegram"""
    if not report or not report['books']:
        return f"📚 <b>ПРОЧИТАНО ЗА МЕСЯЦ</b>\n\nНет прочитанных книг с {report['period'] if report else 'последнего месяца'}"

    formatted = []
    formatted.append(f"С {report['period']}")
    formatted.append(f"Всего книг: <b>{report['total_books']}</b>")
    
    if report['total_pages']:
        formatted.append(f"Всего страниц: <b>{report['total_pages']}</b>")
    
    formatted.append("")

    for book in report['books']:
        book_id = book[1]
        event_date = datetime.strptime(book[2], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
        title = book[4]
        authors = book[5]
        series_name = book[6]
        series_number = book[7]
        pages = book[8]
        book_format = book[9]
        notes = book[3]
        
        # Формируем строку с информацией о книге
        book_info = []
        book_info.append(f"📖 <b>{title}</b>")
        book_info.append(f"👤 {authors}")
        
        if series_name:
            series_info = f"📚 {series_name}"
            if series_number:
                series_info += f" #{series_number}"
            book_info.append(series_info)
        
        details = []
        details.append(f"ID: {book_id}")
        details.append(f"📅 {event_date}")
        
        if pages:
            details.append(f"📄 {pages} стр.")
        
        if book_format:
            format_emoji = "📱" if book_format == "digital" else "📚"
            details.append(f"{format_emoji} {book_format}")
            
        book_info.append(f"<i>{' • '.join(details)}</i>")
        
        if notes:
            book_info.append(f"💭 {notes}")
        
        formatted.append("\n".join(book_info))
        formatted.append("")
    
    return "\n".join(formatted)

def format_purchases_report(report):
    """Форматирует отчет о покупках для Telegram"""
    if not report or not report['books']:
        return f"🛒 <b>КУПЛЕНО ЗА МЕСЯЦ</b>\n\nНет покупок с {report['period'] if report else 'последнего месяца'}"

    formatted = []
    formatted.append(f"С {report['period']}")
    formatted.append(f"Всего книг: <b>{report['total_books']}</b>")
    formatted.append("")

    for book in report['books']:
        book_id = book[1]
        event_date = datetime.strptime(book[2], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
        title = book[4]
        authors = book[5]
        series_name = book[6]
        series_number = book[7]
        book_format = book[8]
        notes = book[3]
        
        # Формируем строку с информацией о книге
        book_info = []
        book_info.append(f"📚 <b>{title}</b>")
        book_info.append(f"👤 {authors}")
        
        if series_name:
            series_info = f"📚 {series_name}"
            if series_number:
                series_info += f" #{series_number}"
            book_info.append(series_info)
        
        details = []
        details.append(f"ID: {book_id}")
        details.append(f"🛒 {event_date}")
        
        if book_format:
            format_emoji = "📱" if book_format == "digital" else "📚"
            details.append(f"{format_emoji} {book_format}")
            
        book_info.append(f"<i>{' • '.join(details)}</i>")
        
        if notes:
            book_info.append(f"💭 {notes}")
        
        formatted.append("\n".join(book_info))
        formatted.append("")
    
    return "\n".join(formatted)

def format_combined_report(reading_report, purchases_report):
    """Форматирует объединенный отчет о прочитанном и купленном"""
    formatted = []
    formatted.append("📊 <b>МЕСЯЧНЫЙ ОТЧЕТ</b>")
    
    # Используем красивое название месяца
    month_name = reading_report.get('month_name', 'текущий месяц')
    formatted.append(f"За {month_name}")
    formatted.append("")
    
    # Статистика
    stats = []
    if reading_report['total_books'] > 0:
        stats.append(f"📚 Прочитано: <b>{reading_report['total_books']}</b> книг")
        if reading_report['total_pages']:
            stats.append(f"📄 Страниц: <b>{reading_report['total_pages']}</b>")
    
    if purchases_report['total_books'] > 0:
        stats.append(f"🛒 Куплено: <b>{purchases_report['total_books']}</b> книг")
    
    if stats:
        formatted.extend(stats)
        formatted.append("")
    
    # Раздел прочитанного
    if reading_report['books']:
        
        for book in reading_report['books']:
            book_id = book[1]
            event_date = datetime.strptime(book[2], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
            title = book[4]
            authors = book[5]
            series_name = book[6]
            series_number = book[7]
            pages = book[8]
            book_format = book[9]
            notes = book[3]
            
            book_info = []
            book_info.append(f"📚 <b>{title}</b>")
            book_info.append(f"👤 {authors}")
            
            if series_name:
                series_info = f"📚 {series_name}"
                if series_number:
                    series_info += f" #{series_number}"
                book_info.append(series_info)
            
            details = []
            details.append(f"ID: {book_id}")
            details.append(f"📅 {event_date}")
            
            if pages:
                details.append(f"📄 {pages} стр.")
            
            if book_format:
                format_emoji = "📱" if book_format == "digital" else "📚"
                details.append(f"{format_emoji} {book_format}")
                
            book_info.append(f"<i>{' • '.join(details)}</i>")
            
            if notes:
                book_info.append(f"💭 {notes}")
            
            formatted.append("\n".join(book_info))
            formatted.append("")
    
    # Раздел купленного
    if purchases_report['books']:
        formatted.append("🛒 <b>КУПЛЕНО:</b>")
        formatted.append("")
        
        for book in purchases_report['books']:
            book_id = book[1]
            event_date = datetime.strptime(book[2], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
            title = book[4]
            authors = book[5]
            series_name = book[6]
            series_number = book[7]
            book_format = book[8]
            notes = book[3]
            
            book_info = []
            book_info.append(f"📚 <b>{title}</b>")
            book_info.append(f"👤 {authors}")
            
            if series_name:
                series_info = f"📚 {series_name}"
                if series_number:
                    series_info += f" #{series_number}"
                book_info.append(series_info)
            
            details = []
            details.append(f"ID: {book_id}")
            details.append(f"🛒 {event_date}")
            
            if book_format:
                format_emoji = "📱" if book_format == "digital" else "📚"
                details.append(f"{format_emoji} {book_format}")
                
            book_info.append(f"<i>{' • '.join(details)}</i>")
            
            if notes:
                book_info.append(f"💭 {notes}")
            
            formatted.append("\n".join(book_info))
            formatted.append("")
    
    # Если нет ни прочитанного, ни купленного
    if not reading_report['books'] and not purchases_report['books']:
        formatted.append(f"Нет активности за {month_name}")
    
    return "\n".join(formatted)

def split_message(text, max_length=4000):
    """Разбивает длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    lines = text.split('\n')
    current_part = []
    current_length = 0
    
    for line in lines:
        line_length = len(line) + 1  # +1 для \n
        
        if current_length + line_length > max_length and current_part:
            parts.append('\n'.join(current_part))
            current_part = [line]
            current_length = line_length
        else:
            current_part.append(line)
            current_length += line_length
    
    if current_part:
        parts.append('\n'.join(current_part))
    
    return parts

async def send_monthly_report_auto():
    """Автоматическая отправка месячного отчета"""
    if not bot_instance or not user_id:
        logger.warning("Бот или ID пользователя не настроены для автоматических отчетов")
        return
    
    try:
        # Определяем за какой месяц отчет (предыдущий месяц)
        now = datetime.now()
        if now.month == 1:
            prev_month = 12
            prev_year = now.year - 1
        else:
            prev_month = now.month - 1
            prev_year = now.year
            
        prev_month_name = datetime(prev_year, prev_month, 1).strftime('%B %Y')
        
        logger.info(f"Отправка автоматического отчета за {prev_month_name}")
        
        # Получаем отчеты за предыдущий месяц
        reading_report = get_previous_month_reading_report()
        purchases_report = get_previous_month_purchases_report()
        
        # Форматируем объединенный отчет с префиксом
        header = f"🗓 <b>АВТОМАТИЧЕСКИЙ ОТЧЕТ ЗА {prev_month_name.upper()}</b>\n\n"
        report_text = format_combined_report(reading_report, purchases_report)
        full_text = header + report_text
        
        # Разбиваем на части если нужно
        parts = split_message(full_text)
        
        # Отправляем части
        for i, part in enumerate(parts):
            if i == 0:
                await bot_instance.send_message(user_id, part, parse_mode="HTML")
            else:
                await bot_instance.send_message(
                    user_id, 
                    f"<i>Продолжение отчета...</i>\n\n{part}", 
                    parse_mode="HTML"
                )
        
        logger.info(f"Автоматический отчет за {prev_month_name} успешно отправлен")
        
    except Exception as e:
        logger.error(f"Ошибка при отправке автоматического отчета: {e}")
        try:
            await bot_instance.send_message(
                user_id, 
                "❌ Произошла ошибка при формировании автоматического месячного отчета"
            )
        except:
            pass

def setup_scheduler(bot: Bot, target_user_id: int):
    """Настройка планировщика для автоматических отчетов"""
    global scheduler, bot_instance, user_id
    
    bot_instance = bot
    user_id = target_user_id
    
    if scheduler is None:
        scheduler = AsyncIOScheduler()
        
        # Запуск в последний день каждого месяца в 9:00
        scheduler.add_job(
            send_monthly_report_auto,
            trigger=CronTrigger(
                day='last',  # последний день месяца
                hour=9,
                minute=0
            ),
            id='monthly_report',
            replace_existing=True,
            misfire_grace_time=3600  # если пропустили запуск, выполнить в течение часа
        )
        
        scheduler.start()
        logger.info(f"Планировщик настроен для пользователя {target_user_id}")
    else:
        logger.info("Планировщик уже настроен")

def stop_scheduler():
    """Остановка планировщика"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logger.info("Планировщик остановлен")


async def cmd_last_read(message: types.Message):
    """Команда для получения объединенного отчета о прочитанном и купленном за месяц"""
    try:
        # Получаем оба отчета
        reading_report = get_monthly_reading_report()
        purchases_report = get_monthly_purchases_report()
        
        # Форматируем объединенный отчет
        text = format_combined_report(reading_report, purchases_report)
        
        # Разбиваем на части если нужно
        parts = split_message(text)
        
        for i, part in enumerate(parts):
            if i == 0:
                await message.answer(part, parse_mode="HTML")
            else:
                await message.answer(f"<i>Продолжение отчета...</i>\n\n{part}", parse_mode="HTML")
                
    except Exception as e:
        logger.error(f"Ошибка при выполнении команды last_read: {e}")
        await message.answer("❌ Произошла ошибка при получении месячного отчета")

def register_handlers(dp: Dispatcher):
    """Регистрация обработчиков команд"""
    dp.message.register(cmd_last_read, Command("last_read"))
