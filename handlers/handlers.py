import asyncio
from datetime import datetime, timedelta
import json
from random import shuffle
from aiogram import Router, types
from aiogram import F
from aiogram.filters import StateFilter, CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from db.create_tables import UserWord, get_db
# from sqlalchemy import select
from handlers.utils import create_user_word, get_new_words_for_user, get_user_by_telegram_id, get_words_for_repeat, mark_words_as_learned, update_user_word
from openai import AsyncOpenAI

router = Router()

# --- Функции для работы с ботом ---
@dp.message(CommandStart())
async def start_command(message: types.Message):
    """Обработчик команды /start."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Новые слова", callback_data="new_words")
    builder.button(text="Повторение", callback_data="repeat_words")
    await message.answer(
        "Привет! Выбери действие:",
        reply_markup=builder.as_markup()
    )
@dp.callback_query(F.data == "new_words")
async def new_words_command(callback: types.CallbackQuery):
  """Запускает процесс выбора количества новых слов."""
  builder = InlineKeyboardBuilder()
  for count in [10, 20, 30, 50, 100]:
        builder.button(text=str(count), callback_data=f"new_words_count:{count}")
  await callback.message.answer(
        "Выберите количество слов для изучения:",
        reply_markup=builder.as_markup()
    )
  await callback.answer()

@dp.callback_query(F.data.startswith("new_words_count:"))
async def new_words_count_handler(callback: types.CallbackQuery):
  """Обрабатывает выбор количества новых слов."""
  count = int(callback.data.split(":")[1])
  async for session in get_db():
      user = await get_user_by_telegram_id(callback.from_user.id, session)
      words = await get_new_words_for_user(user.id, count, session)
      if not words:
         await callback.message.answer(
                "Нет слов для изучения. Добавьте слова в базу данных"
             )
         await callback.answer()
         return
      user_words = []
      for word in words:
         user_word = await create_user_word(user.id, word.id, session)
         user_words.append(user_word)

      words_data_for_web_app = [{'english':word.word.english, 'russian':word.word.russian} for word in user_words]
      web_app = types.WebAppInfo(url=WEB_APP_URL)
      keyboard = InlineKeyboardBuilder().button(text="Начать изучение", web_app=web_app).as_markup()
      await callback.message.answer(
                f"Выбрано {count} новых слов. Начните изучение в мини-приложении",
                reply_markup=keyboard
                )
      await callback.answer()

@dp.callback_query(F.data == "repeat_words")
async def repeat_words_command(callback: types.CallbackQuery):
   """Запускает процесс повторения слов."""
   async for session in get_db():
       user = await get_user_by_telegram_id(callback.from_user.id, session)
       user_words = await get_words_for_repeat(user.id, session)
       if not user_words:
          await callback.message.answer("Нет слов для повторения. Изучите новые слова")
          await callback.answer()
          return
       shuffle(user_words) # перемешиваем список слов
       words_data_for_web_app = [{'english':word.word.english, 'russian':word.word.russian, 'user_word_id': word.id} for word in user_words]

       web_app = types.WebAppInfo(url=WEB_APP_URL)
       keyboard = InlineKeyboardBuilder().button(text="Начать повторение", web_app=web_app).as_markup()

       await callback.message.answer(
              "Начните повторение в мини-приложении",
              reply_markup=keyboard
        )
       await callback.answer()

@dp.message(F.web_app_data)
async def web_app_handler(message: types.Message):
    """Обрабатывает данные из мини-приложения."""
    web_app_data = json.loads(message.web_app_data.data)
    if web_app_data.get('type') == 'repeat':
       user_word_id = web_app_data.get('user_word_id')
       correct_answer = web_app_data.get('correct_answer')
       async for session in get_db():
           new_repeat_time = None
           if correct_answer:
                new_repeat_time = datetime.now() + timedelta(days=1) # Увеличиваем интервал
           else:
               new_repeat_time = datetime.now() # Возвращаем повторение сразу
           await update_user_word(user_word_id, session, correct_answer, new_repeat_time)
           await message.answer("Результат записан", show_alert=True)

    elif web_app_data.get('type') == 'survey':
       user_word_ids = web_app_data.get('user_word_ids') #Список id user_word
       async for session in get_db():
          user_words_to_update = []
          for user_word_id in user_word_ids:
            user_word = await session.get(UserWord, user_word_id)
            if user_word:
               user_words_to_update.append(user_word)
          await mark_words_as_learned(user_words_to_update, session)
          await message.answer("Слова обновлены", show_alert=True)

# @router.message((F.text == "admin @"))
# async def process_add_admin(message: types.Message, state: FSMContext):
#     await add_admin_id(message.from_user.id)

# @router.message(CreateVacancyInfoStates.create_vacancy)
# async def create_v(message: types.Message, state: FSMContext):
#     await state.clear()

# @router.message((F.text == "Нет портрета") & (F.from_user.id.in_(ADMINS)))
# async def find_candidate(message: types.Message, state: FSMContext):
#     print('in Нет портрета admin')

# @router.message((F.text.in_(["Поиск кандидата","К поиску кандидата", "Создать портрет"])) & (F.from_user.id.in_(ADMINS)))
# async def list_vacancies(message: types.Message, state: FSMContext, data=None):
#     await state.set_state(DocumentInfoStates)

# @router.message(CandidateInfoStates.waiting_for_data_of_candidate)
# @router.message((F.text == "Искать") & (F.from_user.id.in_(ADMINS)))
# async def search_vacancies(message: types.Message, state: FSMContext, data=None):
#     pass

# @router.message((F.document) & (F.from_user.id.in_(ADMINS)))
# async def handle_file(message: types.Message, state: FSMContext):
#     if message.document:
#         pass

# @router.message((F.text == "Получить тестовое задание") & (~F.from_user.id.in_(ADMINS)))
# async def give_test_task(message: types.Message, state: FSMContext):
#     pass

