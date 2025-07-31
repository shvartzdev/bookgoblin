import sqlite3
import os
from dotenv import load_dotenv
import logging

load_dotenv()
DB_FILE = os.getenv('DB_PATH', '/app/data/library.db')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_conn():
    """Создает подключение к базе данных с включенными внешними ключами"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute("PRAGMA foreign_keys = ON")  
        return conn
    except sqlite3.Error as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        raise

def init_db():
    """Инициализация базы данных - создание всех таблиц"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            authors TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            isbn TEXT,
            format TEXT NOT NULL CHECK (format IN ('physical', 'digital')),
            source TEXT CHECK (source IN ('shop', 'author.today', 'ficbook', 'ao3')),
            year INTEGER CHECK (year > 1000 AND year <= 2030),
            pages INTEGER CHECK (pages > 0),
            char_count INTEGER CHECK (char_count >= 0),  
            publisher TEXT,
            genre TEXT,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            series_name TEXT,
            series_number INTEGER,
            is_read BOOLEAN DEFAULT 0
        )
        ''')

        # Список для чтения (только книги, которые уже есть в библиотеке)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS to_read_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
        ''')

        # Список для покупки 
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS to_buy_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            authors TEXT,
            title TEXT,
            notes TEXT,
            priority INTEGER DEFAULT 1 CHECK (priority IN (1, 2, 3, 4, 5)),
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT check_author_or_title CHECK (authors IS NOT NULL OR title IS NOT NULL)
        )
        ''')

        # Лог событий с книгами
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS book_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type IN ('added', 'started_reading', 'finished_reading', 'reviewed', 'moved_to_read_list')),
            event_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_authors ON books(authors)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_log_date ON book_log(event_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_book_log_type ON book_log(event_type)')

        conn.commit()
        logger.info("База данных успешно инициализирована")
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def add_book(authors, title, description=None, isbn=None, format_type='physical', 
             source='shop', year=None, pages=None, char_count=None, publisher=None, genre=None, url=None,
             series_name=None, series_number=None, is_read=False):
    """Добавляет новую книгу в библиотеку"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO books (
            authors, title, description, isbn, format, source, year, pages, char_count, publisher, genre, url,
            series_name, series_number, is_read
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            authors, title, description, isbn, format_type, source, year, pages, char_count, publisher, genre, url,
            series_name, series_number, int(is_read)  
        ))
        
        book_id = cursor.lastrowid
        
        cursor.execute('''
        INSERT INTO book_log (book_id, event_type, notes)
        VALUES (?, 'added', 'Книга добавлена в библиотеку')
        ''', (book_id,))
        
        conn.commit()
        logger.info(f"Книга '{title}' успешно добавлена с ID: {book_id}")
        return book_id
        
    except sqlite3.IntegrityError as e:
        logger.error(f"Ошибка целостности данных при добавлении книги: {e}")
        conn.rollback()
        raise
    except sqlite3.Error as e:
        logger.error(f"Ошибка при добавлении книги: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_all_books():
    """Получает все книги из библиотеки"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM books ORDER BY title')
        books = cursor.fetchall()
        return books
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении списка книг: {e}")
        raise
    finally:
        conn.close()

def search_books(query):
    """Поиск книг по названию или автору"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT * FROM books 
        WHERE title LIKE ? OR authors LIKE ?
        ORDER BY title
        ''', (f'%{query}%', f'%{query}%'))
        
        books = cursor.fetchall()
        return books
    except sqlite3.Error as e:
        logger.error(f"Ошибка при поиске книг: {e}")
        raise
    finally:
        conn.close()

def add_to_read_list(book_id, notes=None):
    """Добавляет книгу в список для чтения"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id FROM books WHERE id = ?', (book_id,))
        if not cursor.fetchone():
            raise ValueError(f"Книга с ID {book_id} не найдена")
        
        cursor.execute('SELECT id FROM to_read_list WHERE book_id = ?', (book_id,))
        if cursor.fetchone():
            raise ValueError("Книга уже в списке для чтения")
        
        cursor.execute('''
        INSERT INTO to_read_list (book_id, notes)
        VALUES (?, ?)
        ''', (book_id, notes))
        
        cursor.execute('''
        INSERT INTO book_log (book_id, event_type, notes)
        VALUES (?, 'moved_to_read_list', ?)
        ''', (book_id, notes or 'Книга добавлена в список для чтения'))
        
        conn.commit()
        logger.info(f"Книга с ID {book_id} добавлена в список для чтения")
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка при добавлении в список для чтения: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def add_to_buy_list(authors=None, title=None, notes=None, priority=1):
    """Добавляет книгу в список для покупки"""
    if not authors and not title:
        raise ValueError("Необходимо указать хотя бы автора или название")
    
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO to_buy_list (authors, title, notes, priority)
        VALUES (?, ?, ?, ?)
        ''', (authors, title, notes, priority))
        
        conn.commit()
        logger.info(f"Книга добавлена в список для покупки: {title or 'Без названия'}")
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка при добавлении в список для покупки: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_to_read_list():
    """Получает список книг для чтения"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT trl.id, b.title, b.authors, trl.added_date, trl.notes
        FROM to_read_list trl
        JOIN books b ON trl.book_id = b.id
        ORDER BY trl.added_date DESC
        ''')
        
        books = cursor.fetchall()
        return books
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении списка для чтения: {e}")
        raise
    finally:
        conn.close()

def get_to_buy_list():
    """Получает список книг для покупки"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT * FROM to_buy_list 
        ORDER BY priority DESC, added_date DESC
        ''')
        
        books = cursor.fetchall()
        return books
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении списка для покупки: {e}")
        raise
    finally:
        conn.close()

def log_book_event(book_id, event_type, notes=None):
    """Добавляет событие в лог книги"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT INTO book_log (book_id, event_type, notes)
        VALUES (?, ?, ?)
        ''', (book_id, event_type, notes))
        
        conn.commit()
        logger.info(f"Событие '{event_type}' добавлено для книги ID {book_id}")
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка при добавлении события в лог: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def get_book_log(book_id):
    """Получает историю событий для книги"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        SELECT event_type, event_date, notes
        FROM book_log
        WHERE book_id = ?
        ORDER BY event_date DESC
        ''', (book_id,))
        
        events = cursor.fetchall()
        return events
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении лога книги: {e}")
        raise
    finally:
        conn.close()

def get_library_summary():
    """Получает статистику по библиотеке"""
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        summary = {}
        
        # Общее количество книг в библиотеке
        cursor.execute('SELECT COUNT(*) FROM books')
        total_books = cursor.fetchone()[0]
        summary['total_books'] = total_books
        
        # Количество прочитанных книг
        cursor.execute('SELECT COUNT(*) FROM books WHERE is_read = 1')
        read_books = cursor.fetchone()[0]
        summary['read_books'] = read_books
        
        # Процент прочитанных
        summary['read_percent'] = (read_books / total_books * 100) if total_books > 0 else 0
        
        # Статистика по форматам
        cursor.execute('''
        SELECT format, COUNT(*) as count
        FROM books
        GROUP BY format
        ORDER BY count DESC
        ''')
        formats = cursor.fetchall()
        summary['formats'] = {format_type: count for format_type, count in formats}
        
        # Статистика по жанрам (исключая NULL значения)
        cursor.execute('''
        SELECT genre, COUNT(distinct id) as count
        FROM books
        WHERE genre IS NOT NULL AND genre != ''
        GROUP BY genre
        ORDER BY count DESC
        ''')
        genres = cursor.fetchall()
        summary['genres'] = {genre: count for genre, count in genres}
        
        
        # Статистика по спискам
        cursor.execute('SELECT COUNT(*) FROM to_read_list')
        summary['to_read_count'] = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM to_buy_list')
        summary['to_buy_count'] = cursor.fetchone()[0]
        
        # Статистика активности по логам (последние 30 дней)
        cursor.execute('''
        SELECT event_type, COUNT(*) as count
        FROM book_log
        WHERE event_date >= datetime('now', '-30 days')
        GROUP BY event_type
        ORDER BY count DESC
        ''')
        recent_activity = cursor.fetchall()
        summary['recent_activity'] = {event: count for event, count in recent_activity}
        
        logger.info("Статистика библиотеки успешно получена")
        return summary
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка при получении статистики библиотеки: {e}")
        raise
    finally:
        conn.close()


def format_library_summary(summary):
    """Форматирует статистику библиотеки для красивого вывода"""
    if not summary:
        return "Библиотека пуста"
    
    formatted_text = []
    
    formatted_text.append("📚 **СТАТИСТИКА БИБЛИОТЕКИ**")
    formatted_text.append(f"Всего книг: {summary['total_books']}")
    formatted_text.append(f"Прочитано книг: {summary['read_books']} ({summary['read_percent']:.2f}%)")
    formatted_text.append("")
    
    if summary['formats']:
        formatted_text.append("📖 **По форматам:**")
        for format_type, count in summary['formats'].items():
            emoji = "📱" if format_type == "digital" else "📚"
            formatted_text.append(f"{emoji} {format_type.title()}: {count}")
        formatted_text.append("")
    
    if summary['genres']:
        formatted_text.append("🎭 **Топ жанров:**")
        for genre, count in list(summary['genres'].items())[:5]:  # Топ-5
            formatted_text.append(f"• {genre}: {count}")
        formatted_text.append("")

    if summary['recent_activity']:
        formatted_text.append("**Логи:**")
        for event in list(summary['recent_activity'].items())[:5]:
            formatted_text.append(f"• {event}")
        formatted_text.append("") 
    
    
    formatted_text.append("📝 **Списки:**")
    formatted_text.append(f"📖 К прочтению: {summary['to_read_count']}")
    formatted_text.append(f"🛒 К покупке: {summary['to_buy_count']}")
    
    return "\n".join(formatted_text)



if __name__ == "__main__":
    init_db()
    print("База данных инициализирована успешно!")