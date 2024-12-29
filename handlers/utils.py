# --- Функции работы с данными ---
from datetime import datetime, timedelta
import logging
from typing import List
from aiogram import Bot, Dispatcher, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from sqlalchemy import select
import bot
from db.create_tables import User, UserWord, Word, get_db


async def get_user_by_telegram_id(telegram_id, session):
    """Получает пользователя по его telegram_id или создает нового, если нет."""
    user = await session.scalar(select(User).filter_by(telegram_id=telegram_id))
    if not user:
       user = User(telegram_id=telegram_id)
       session.add(user)
       await session.commit()
       await session.refresh(user)
    return user
async def create_user_word(user_id, word_id, session):
      """Создаёт запись в таблице user_words"""
      user_word = UserWord(user_id = user_id, word_id = word_id, last_repeat_time = datetime.now())
      session.add(user_word)
      await session.commit()
      await session.refresh(user_word)
      return user_word

async def get_new_words_for_user(user_id, count, session):
    """Получает новые слова для изучения."""
    words = await session.scalars(select(Word).filter(Word.category == "new").limit(count))
    return words.all()

async def get_words_for_repeat(user_id, session):
    """Возвращает слова, которые нужно повторить."""
    now = datetime.now()
    user_words = await session.scalars(select(UserWord).where(
      UserWord.user_id == user_id,
      UserWord.last_repeat_time <= now
    ))
    return user_words.all()

async def update_user_word(user_word_id, session, correct_answer=True, last_repeat_time=None):
    """Обновляет запись в таблице UserWord."""
    user_word = await session.get(UserWord, user_word_id)
    if user_word:
      if correct_answer:
        user_word.correct_answers +=1
      else:
        user_word.incorrect_answers +=1

      if last_repeat_time:
        user_word.last_repeat_time = last_repeat_time
      await session.commit()

async def mark_words_as_learned(user_words: List[UserWord], session):
    """Переводит слова в категорию 'освоенные'"""
    for user_word in user_words:
        if (user_word.correct_answers / (user_word.correct_answers + user_word.incorrect_answers) >= 0.8): #если больше 80% слов освоены
            word = await session.get(Word, user_word.word_id)
            if word:
               word.category = "learned"
               user_word.last_repeat_time = datetime.now() + timedelta(days=30)
        else:
             user_word.last_repeat_time =  datetime.now() + timedelta(days=7) # Возвращаем на повторение через неделю
    await session.commit()

async def load_words_from_file(file_path, session):
    """Загружает слова из файла и добавляет в базу данных."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                try:
                    english, russian = line.strip().split('-')
                    english = english.strip()
                    russian = russian.strip()
                    word = Word(english=english, russian=russian)
                    session.add(word)
                    await session.commit()
                    await session.refresh(word)
                except ValueError:
                   logging.warning(f"Неправильная строка '{line}' в файле. Пропускаю.")
        logging.info("Слова успешно загружены в базу данных.")
    except FileNotFoundError:
        logging.error(f"Файл '{file_path}' не найден")
    except Exception as e:
        logging.error(f"Ошибка при загрузке слов: {e}")

async def check_if_words_need_review():
  """Проверяет, не нужно ли проводить опрос по словам."""
  logging.info('Проверяю, не нужно ли проводить опрос по словам')
  async for session in get_db():
       all_users = await session.scalars(select(User))
       for user in all_users:
          user_words_for_review = await session.scalars(select(UserWord).where(
             UserWord.user_id == user.id,
             UserWord.last_repeat_time <= datetime.now() - timedelta(days=7)
         ))
          user_words_for_review = user_words_for_review.all()
          if user_words_for_review:
             user_word_ids = [word.id for word in user_words_for_review]
             web_app = types.WebAppInfo(url=WEB_APP_URL)
             keyboard = InlineKeyboardBuilder().button(text="Пройти опрос", web_app=web_app).as_markup()
             await bot.send_message(
                 user.telegram_id,
                  f"Прошла неделя после повторения слов. Пожалуйста, пройдите опрос.",
                   reply_markup=keyboard
              )