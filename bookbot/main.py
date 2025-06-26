import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from handlers import register_all_handlers
import db

load_dotenv()  

async def main():
    db.init_db()

    TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
    if not TG_BOT_TOKEN:
        raise RuntimeError("TG_BOT_TOKEN is not set in environment variables")

    bot = Bot(token=TG_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    register_all_handlers(dp)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
