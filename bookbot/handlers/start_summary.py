from aiogram import types, Dispatcher
from db import get_library_summary, format_library_summary
from aiogram.filters import Command


async def cmd_start(message: types.Message):
    welcome = ("📚 Добро пожаловать!\n"
               "Команды:\n"
               "/addmanual — добавить вручную\n"
               "/summary — сводка")
    await message.answer(welcome)

async def cmd_summary(message: types.Message):
    stats = get_library_summary()
    txt = format_library_summary(stats)
    await message.answer(txt, parse_mode="Markdown")

def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_summary, Command("summary"))
