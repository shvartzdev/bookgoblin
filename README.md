# 📚 BookGoblin - Telegram Bot for Personal Library Management

A comprehensive Telegram bot for managing your personal book collection, reading lists, and purchase lists. Built with Python, aiogram, and SQLite.

## 🚀 Features

### 📖 Library Management
- **Add Books Manually**: Complete book entry with detailed metadata
- **Search Library**: Find books by title, author, or series
- **Library Summary**: Get statistics and overview of your collection
- **Activity Logs**: Track all actions and changes in your library

### 📋 Reading Lists
- **To-Read List**: Add books from your library to reading queue
- **Priority Management**: Set reading priorities (1-5)
- **Mark as Read**: Track completed books
- **Reading Progress**: Log reading start/finish events

### 🛒 Purchase Management
- **To-Buy List**: Track books you want to purchase
- **Priority System**: Organize purchases by priority
- **Move to Library**: Transfer purchased books to main library
- **Purchase Tracking**: Log all purchase-related activities

### 📊 Reports & Analytics
- **Monthly Reports**: Automatic monthly reading and purchase summaries
- **Reading Statistics**: Track books read and pages completed
- **Purchase Analytics**: Monitor buying patterns
- **Activity History**: Detailed logs of all library activities

### 🔄 Automation
- **Automatic Reports**: Monthly reports sent automatically
- **Scheduled Tasks**: Configurable report timing
- **Event Logging**: Comprehensive activity tracking

## 📱 Commands

### Core Commands
- `/start` - Welcome message and command overview
- `/summary` - Library statistics and overview
- `/addmanual` - Add a book manually with guided setup
- `/search` - Search books by title, author, or series

### Reading Lists
- `/gettrl` - View your to-read list
- `/addtoread` - Add a book to reading list
- `/markread` - Mark a book as finished reading
- `/changerpriority` - Change reading priority

### Purchase Lists
- `/gettbr` - View your to-buy list
- `/addtobuy` - Add a book to purchase list
- `/movetolib` - Move purchased book to library
- `/deletebuy` - Remove book from purchase list

### Reports & Analytics
- `/last_read` - Get current month's reading and purchase report
- `/setup_auto_reports` - Enable automatic monthly reports
- `/stop_auto_reports` - Disable automatic reports
- `/test_auto_report` - Send a test report immediately
- `/log` - View recent activity logs

## 🗄️ Database Structure

### Books Table
- Complete book metadata (title, authors, format, pages, etc.)
- Support for physical and digital books
- Series information and numbering
- Reading status tracking

### To-Read List
- Books from library marked for reading
- Priority levels (1-5)
- Notes and reading progress
- Completion tracking

### To-Buy List
- Books planned for purchase
- Priority management
- Author/title tracking
- Purchase status

### Book Log
- Comprehensive activity logging
- Event types: added, started_reading, finished_reading, etc.
- Timestamp tracking
- Detailed notes and metadata

## 🛠️ Technical Details

### Architecture
- **Framework**: aiogram 3.x (async)
- **Database**: SQLite with foreign key constraints
- **Scheduler**: APScheduler for automatic reports
- **State Management**: FSM for multi-step interactions

### Data Formats
- **Physical Books**: Title, authors, pages, year, publisher, ISBN
- **Digital Books**: Title, authors, character count, source
- **Fan Fiction**: Support for Author.Today, Ficbook, AO3 sources

### Search Capabilities
- Full-text search across titles, authors, and series
- Fuzzy matching for partial queries
- Results limited to 10 items for performance

### Report Features
- Monthly reading summaries
- Purchase tracking
- Page count statistics
- Formatted HTML output with emojis
- Automatic message splitting for long reports

## 🚀 Setup & Installation

### Prerequisites
- Python 3.8+
- Telegram Bot Token
- Docker (optional)

### Environment Variables
```bash
TG_BOT_TOKEN=your_telegram_bot_token
DB_PATH=/app/data/library.db  # Optional, defaults to /app/data/library.db
```

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables
4. Run the bot: `python bookbot/main.py`

### Docker Setup
```bash
docker-compose up -d
```

## 📊 Usage Examples

### Adding a Book
```
/addmanual
→ Enter title: "The Hobbit"
→ Enter authors: "J.R.R. Tolkien"
→ Choose format: Physical
→ Enter year: 1937
→ Enter pages: 310
→ Add to series: Yes
→ Series name: "The Lord of the Rings"
→ Series number: 0
→ Mark as read: Yes
```

### Searching Books
```
/search
→ Enter query: "tolkien hobbit"
→ Results: The Hobbit (ID: 123)
```

### Managing Reading List
```
/gettrl
→ View current reading list
→ Use inline buttons to manage priorities
→ Mark books as finished
```

### Automatic Reports
```
/setup_auto_reports
→ Automatic monthly reports enabled
→ Reports sent on last day of month at 9:00 AM
```

## 🔧 Configuration

### Report Scheduling
- **Default**: Last day of month at 9:00 AM
- **Configurable**: Modify `setup_scheduler()` in reports.py
- **Grace Period**: 1 hour misfire handling

### Message Limits
- **Max Length**: 4000 characters per message
- **Auto-splitting**: Long reports split automatically
- **HTML Formatting**: Rich text with emojis

### Database
- **Location**: `/app/data/library.db` (Docker) or local path
- **Backup**: SQLite file can be backed up directly
- **Indexes**: Optimized for search performance

## 🐛 Troubleshooting

### Common Issues
1. **Bot not responding**: Check TG_BOT_TOKEN environment variable
2. **Database errors**: Ensure write permissions for DB_PATH
3. **Reports not sending**: Verify scheduler setup with `/setup_auto_reports`
4. **Search not working**: Check database initialization

### Logs
- All activities logged to console
- Database errors logged with stack traces
- Scheduler events logged for debugging

## 📈 Future Enhancements

- [ ] Export functionality (CSV, JSON)
- [ ] Reading goals and challenges
- [ ] Book recommendations
- [ ] Integration with external book APIs
- [ ] Reading time tracking
- [ ] Book cover image support
- [ ] Multi-language support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**BookGoblin** - Your personal library assistant in Telegram! 📚✨

