import asyncio
import codecs
from urllib.parse import quote
from datetime import datetime, timedelta
import json
from random import shuffle
from aiogram import Router, types
from aiogram import F
from aiogram.filters import StateFilter, CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup

from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from db.create_tables import UserWord, get_db
# from sqlalchemy import select
from handlers.utils import create_user_word, get_new_words_for_user, get_repeat_time, get_user_by_telegram_id, get_user_settings, get_words_for_repeat, mark_words_as_learned, update_user_settings, update_user_word
# from openai import AsyncOpenAI

# from config import WEB_APP_URL

WEB_APP_URL = 'https://127.0.0.1:8000'
router = Router()


@router.callback_query(F.data == "settings")
async def settings_words_count_command(callback: types.CallbackQuery):
     """Запускает процесс настройки количества новых слов."""
     builder = InlineKeyboardBuilder()
     for count in [10, 20, 30, 50, 100]:
         builder.button(text=str(count), callback_data=f"set_words_count:{count}")
     await callback.message.answer(
            "Выберите количество слов для изучения:",
            reply_markup=builder.as_markup()
        )
     await callback.answer()

@router.callback_query(F.data.startswith("set_words_count:"))
async def set_words_count_handler(callback: types.CallbackQuery):
    """Обрабатывает выбор количества новых слов."""
    count = int(callback.data.split(":")[1])
    async for session in get_db():
        user = await get_user_by_telegram_id(callback.from_user.id, session)
        await update_user_settings(user.id, words_per_day=count, days_between_lessons=user.days_between_lessons, session=session)
        await callback.message.answer(
             f"Установлено {count} слов для изучения",
         )
    await callback.answer()
    await settings_days_between_command(callback)

@router.callback_query(F.data == "settings_days_between")
async def settings_days_between_command(callback: types.CallbackQuery):
     """Запускает процесс настройки количества дней между занятиями."""
     builder = InlineKeyboardBuilder()
     for days in [1, 2, 3]:
          builder.button(text=str(days), callback_data=f"set_days_between:{days}")
     await callback.message.answer(
            "Выберите интервал между уроками:",
            reply_markup=builder.as_markup()
         )
     await callback.answer()

@router.callback_query(F.data.startswith("set_days_between:"))
async def set_days_between_handler(callback: types.CallbackQuery):
   """Обрабатывает выбор интервала между уроками."""
   days = int(callback.data.split(":")[1])
   async for session in get_db():
      user = await get_user_by_telegram_id(callback.from_user.id, session)
      await update_user_settings(user.id, words_per_day=user.words_per_day, days_between_lessons=days, session=session)
      await callback.message.answer(
         f"Установлен интервал {days} дней между занятиями.",
      )
      await asyncio.sleep(1)
      builder = InlineKeyboardBuilder()
      builder.button(text="Новые слова", callback_data="new_words")
      builder.button(text="Не сейчас", callback_data="cancel")
      await callback.message.answer(
         "Готов присиупить к изучению?",
         reply_markup=builder.as_markup()
      )
   await callback.answer()

# @router.callback_query(F.data == "new_words")
# async def new_words_command(callback: types.CallbackQuery):
#    """Запускает процесс получения новых слов."""
#    async for session in get_db():
#       user = await get_user_by_telegram_id(callback.from_user.id, session)
#       words_per_day, _ = await get_user_settings(user.id, session)
#       words = await get_new_words_for_user(user.id, words_per_day, session)
#       print(words)
#       if not words:
#             await callback.message.answer(
#                "Нет слов для изучения. Добавьте слова в базу данных"
#             )
#             await callback.answer()
#             return
#       user_words = []
#       for word in words:
#             user_word = await create_user_word(user.id, word, session)
#             if user_word:  # Проверяем, что user_word создан.
#                user_words.append(user_word)


#       words_data_for_web_app = [{'english': word.word.english, 'russian': word.word.russian, 'user_word_id': word.id, 'audio_path': word.word.audio_path if word.word.audio_path else '' } for word in user_words]
#    #   words_data_for_web_app = [{'english':word.word.english, 'russian':word.word.russian, 'user_word_id': word.id} for word in user_words]
#       url = f"{WEB_APP_URL}/?words={quote(json.dumps(words_data_for_web_app, ensure_ascii=False))}"
#       print(f"!!\n\n url: {url}\n\n")
#       button = types.InlineKeyboardButton(text="Начать изучение", web_app=types.WebAppInfo(url=url))
#       keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])

#       await callback.message.answer(
#          f"Выбрано {words_per_day} новых слов. Начните изучение в мини-приложении",
#          reply_markup=keyboard
#       )
#       await callback.answer()
@router.callback_query(F.data == "new_words")
async def new_words_command(callback: types.CallbackQuery):
   """Запускает процесс изучения новых слов."""
   async for session in get_db():
      user = await get_user_by_telegram_id(callback.from_user.id, session)
      
      url = f"{WEB_APP_URL}/?telegram_id={user.telegram_id}&type=new"  # Передаем telegram_id и type=new в URL
      button = types.InlineKeyboardButton(text="Начать изучение новых слов", web_app=types.WebAppInfo(url=url))
      keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])

      await callback.message.answer(
         "Начните изучение новых слов в мини-приложении",
         reply_markup=keyboard
      )
      await callback.answer()
# @router.callback_query(F.data == "repeat_words")
# async def repeat_words_command(callback: types.CallbackQuery):
#    """Запускает процесс повторения слов."""
#    async for session in get_db():
#        user = await get_user_by_telegram_id(callback.from_user.id, session)
#        user_words = await get_words_for_repeat(user.id, session)
#        if not user_words:
#           await callback.message.answer("Нет слов для повторения. Изучите новые слова")
#           await callback.answer()
#           return
#        shuffle(user_words) # перемешиваем список слов
#        words_data_for_web_app = [{'english':word.word.english, 'russian':word.word.russian, 'user_word_id': word.id} for word in user_words]
#        url = f"{WEB_APP_URL}?words={quote(json.dumps(words_data_for_web_app, ensure_ascii=False))}"
#        web_app = types.WebAppInfo(url=url)
#        keyboard = InlineKeyboardBuilder().button(text="Начать повторение", web_app=web_app).as_markup()

#        await callback.message.answer(
#               "Начните повторение в мини-приложении",
#               reply_markup=keyboard
#         )
#        await callback.answer()
# @router.callback_query(F.data == "repeat_words")
# async def repeat_words_command(callback: types.CallbackQuery):
#    """Запускает процесс повторения слов."""
#    async for session in get_db():
#       user = await get_user_by_telegram_id(callback.from_user.id, session)
#       user_words = await get_words_for_repeat(user.id, session)
#       print(user_words[0].word)
#       if not user_words:
#          await callback.message.answer("Нет слов для повторения. Изучите новые слова")
#          await callback.answer()
#          return
#       shuffle(user_words)  # перемешиваем список слов
      
#       words_data_for_web_app = [{'english': word.word.english, 'russian': word.word.russian, 'user_word_id': word.id, 'audio_path': word.word.audio_path if word.word.audio_path else ''} for word in user_words]
#       url = f"{WEB_APP_URL}/?words={quote(json.dumps(words_data_for_web_app, ensure_ascii=False))}"
#       print(url)
#       button = types.InlineKeyboardButton(text="Начать повторение", web_app=types.WebAppInfo(url=url))
#       keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])

#       await callback.message.answer(
#          "Начните повторение в мини-приложении",
#          reply_markup=keyboard
#       )
#       await callback.answer()
@router.callback_query(F.data == "repeat_words")
async def repeat_words_command(callback: types.CallbackQuery):
   """Запускает процесс повторения слов."""
   async for session in get_db():
      user = await get_user_by_telegram_id(callback.from_user.id, session)
      
      url = f"{WEB_APP_URL}/?telegram_id={user.telegram_id}"  # Передаем telegram_id в URL
      button = types.InlineKeyboardButton(text="Начать повторение", web_app=types.WebAppInfo(url=url))
      keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])

      await callback.message.answer(
         "Начните повторение в мини-приложении",
         reply_markup=keyboard
      )
      await callback.answer()

@router.message(F.web_app_data)
async def web_app_handler(message: types.Message):
    """Обрабатывает данные из мини-приложения."""
    web_app_data = json.loads(message.web_app_data.data)
    if web_app_data.get('type') == 'repeat':
        user_word_id = web_app_data.get('user_word_id')
        correct_answer = web_app_data.get('correct_answer')
        async for session in get_db():
            user_word = await session.get(UserWord, user_word_id)
            if user_word:
              current_step = user_word.current_step
              repeat_interval = get_repeat_time(current_step)
              new_repeat_time = datetime.now() + repeat_interval
              if correct_answer:
                 await update_user_word(user_word_id, session, correct_answer, new_repeat_time, current_step=current_step + 1 if current_step < 6 else 6)
              else:
                 await update_user_word(user_word_id, session, correct_answer, datetime.now(), current_step=0)

              await message.answer("Результат записан", show_alert=True)

    elif web_app_data.get('type') == 'survey':
        user_word_ids = web_app_data.get('user_word_ids')  # Список id user_word
        async for session in get_db():
            user_words_to_update = []
            for user_word_id in user_word_ids:
                user_word = await session.get(UserWord, user_word_id)
                if user_word:
                    user_words_to_update.append(user_word)
            await mark_words_as_learned(user_words_to_update, session)
            await message.answer("Слова обновлены", show_alert=True)


