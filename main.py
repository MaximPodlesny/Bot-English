import logging
import os
import subprocess
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
# import psutil
from bot import bot
from db.create_tables import get_db, init_db
from handlers import start_router, handlers_router
from handlers.utils import check_if_words_need_review, load_words_from_file
from middlewares.logging import LoggingMiddleware
# from db.create_tables import create_tables
from config import BOT_TOKEN


# Настройка логирования
logging.basicConfig(level=logging.INFO)

# create_tables()

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Подключение мидлвара
dp.message.middleware(LoggingMiddleware())

# Регистрация роутеров
dp.include_router(start_router)
dp.include_router(handlers_router)
# dp.include_router(questionnaire_router)

async def check_active_vacancies():
    var = ''
    try:
        if var:
            asyncio.create_task()
    except:
        pass
        # current_pid = os.getpid()
        # subprocess.run([r'I:\Projects Python\HR_bot\venv\Scripts\python', 'main.py']) 
        # # Находим процесс по PID
        # process = psutil.Process(current_pid)

        # # Завершаем процесс
        # process.terminate()
            # await collect_responses()
    # asyncio.run(check_active_vacancies())

# async def main():
#     await dp.start_polling(bot)
    
# --- Запуск бота ---
async def on_startup():
  await init_db()

async def main():
    dp.startup.register(on_startup)
    # Загрузка слов из файла при запуске бота
    async for session in get_db():
        await load_words_from_file('words.txt', session)

    await dp.start_polling(bot)

    while True: #Периодическая проверка необходимости опроса
        await check_if_words_need_review()
        await asyncio.sleep(60*60) # Проверка каждый час


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())

