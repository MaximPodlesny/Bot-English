# --- Функции работы с данными ---
from datetime import datetime, timedelta
import logging
import os
from typing import List
from aiogram import Bot, Dispatcher, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import bot
from db.create_tables import User, UserWord, Word, get_db
from config import WEB_APP_URL


async def get_user_by_telegram_id(telegram_id: int, session: Session):
    """Получает пользователя по его telegram_id или создает нового, если нет."""
    user = await session.scalar(select(User).filter_by(telegram_id=telegram_id))
    if not user:
       logging.info('Создаю нового пользователя')
       user = User(telegram_id=telegram_id)
       session.add(user)
       await session.commit()
       await session.refresh(user)
    return user
async def create_user_word(user_id: int, word: Word, session: AsyncSession):
    """Создаёт запись в таблице user_words"""
    try:
        user_word = UserWord(user_id=user_id, word_id=word.id, last_repeat_time=datetime.now())
        session.add(user_word)
        await session.commit()
        await session.refresh(user_word)
        return user_word
    except Exception as e:
        print(f"Ошибка при создании user_word:{e}")
        return None

# async def get_new_words_for_user(user_id, count, session):
#     """Получает новые слова для изучения."""
#     words = await session.scalars(select(Word).filter(Word.category == "new").limit(count))
#     return words.all()
async def get_new_words_for_user(user_id: int, count: int, session: AsyncSession):
    """
    Получает новые слова для пользователя, которые он еще не изучал.

    Args:
        user_id: ID пользователя в Telegram.
        count: Количество слов для получения.
        session: Объект асинхронной сессии SQLAlchemy.

    Returns:
        Список объектов Word.
    """
    logging.info("Собираю новые слова для изучения")
    try:
        # Подзапрос, который выбирает ID слов, которые уже есть у пользователя.
        subquery = select(UserWord.word_id).where(UserWord.user_id == user_id).scalar_subquery()

        # Запрос, который выбирает слова, которых нет в подзапросе.
        query = select(Word).where(~Word.id.in_(subquery)).limit(count)
        words = await session.scalars(query)
        return words.all()
    except Exception as e:
        print(f"Ошибка при получении новых слов: {e}")
        return []

async def get_words_for_repeat(user_id: int, session: AsyncSession):
    """Возвращает слова, которые нужно повторить."""
    now = datetime.now()
    user_words = await session.scalars(select(UserWord).where(
      UserWord.user_id == user_id,
      UserWord.last_repeat_time <= now
    ).options(selectinload(UserWord.word)))
    return user_words.all()

async def get_user_settings(user_id: int, session: AsyncSession):
    """Получает настройки пользователя"""
    user = await session.get(User, user_id)
    if user:
        return user.words_per_day, user.days_between_lessons
    return 10, 1

async def update_user_word(user_word_id: int, session: AsyncSession, correct_answer: bool = True, last_repeat_time: datetime = None, current_step: int = None):
    """Обновляет запись в таблице UserWord."""
    user_word = await session.get(UserWord, user_word_id)
    if user_word:
        if correct_answer:
            user_word.correct_answers += 1
        else:
            user_word.incorrect_answers += 1

        if last_repeat_time:
            user_word.last_repeat_time = last_repeat_time
        if current_step is not None:
            user_word.current_step = current_step

        await session.commit()

async def update_user_settings(user_id: int, words_per_day: int, days_between_lessons: int, session: AsyncSession):
    user = await session.get(User, user_id)
    if user:
        user.words_per_day = words_per_day
        user.days_between_lessons = days_between_lessons
        await session.commit()

async def mark_words_as_learned(user_words: List[UserWord], session: AsyncSession):
    """Переводит слова в категорию 'освоенные'"""
    for user_word in user_words:
        if (user_word.correct_answers / (user_word.correct_answers + user_word.incorrect_answers) >= 0.8):  # если больше 80% слов освоены
            word = await session.get(Word, user_word.word_id)
            if word:
                word.category = "learned"
                user_word.last_repeat_time = datetime.now() + timedelta(days=30)
        else:
            user_word.last_repeat_time = datetime.now() + timedelta(days=7)  # Возвращаем на повторение через неделю
    await session.commit()

async def load_words_from_file(file_path, session, audio_dir=None):
    """Загружает слова из файла и добавляет в базу данных."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                try:
                    parts = line.strip().split('-')
                    if len(parts) == 3:  # если есть аудиофайл
                        english, russian, audio_file = parts
                        english = english.strip()
                        russian = russian.strip()
                        audio_file = audio_file.strip()
                        if audio_dir:
                            audio_path = os.path.join(audio_dir, audio_file)  # Полный путь к аудиофайлу
                        else:
                            audio_path = audio_file

                        word = Word(english=english, russian=russian, audio_path=audio_path)
                    elif len(parts) == 2:
                        english, russian = parts
                        english = english.strip()
                        russian = russian.strip()
                        word = Word(english=english, russian=russian)
                    else:
                        logging.warning(f"Неправильная строка '{line}' в файле. Пропускаю.")
                        continue
                    session.add(word)
                    await session.commit()
                    await session.refresh(word)

                except ValueError as e:
                    logging.warning(f"Неправильная строка '{line}' в файле: {e}. Пропускаю.")
                    continue

        logging.info("Слова успешно загружены в базу данных.")
    except FileNotFoundError:
        logging.error(f"Файл '{file_path}' не найден")
    except Exception as e:
        logging.error(f"Ошибка при загрузке слов: {e}")

def truncate_text(text: str, max_length: int = 21) -> str:
    """Ограничивает текст до заданной длины."""
    if len(text) > max_length:
        return text[:max_length - 3] + "..."  # Добавляем "..." для обозначения сокращения
    return text

def get_repeat_time(current_step: int) -> timedelta:
    """Возвращает интервал повторения по текущему шагу."""
    if current_step == 0:
        return timedelta(hours=1)
    elif current_step == 1:
        return timedelta(hours=5)
    elif current_step == 2:
        return timedelta(hours=24)
    elif current_step == 3:
        return timedelta(days=4)
    elif current_step == 4:
        return timedelta(days=14)
    elif current_step == 5:
        return timedelta(days=30)
    else:
        return timedelta(days=30)
    

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
             web_app = types.WebAppInfo(url='http://127.0.0.1:8000/')
             keyboard = InlineKeyboardBuilder().button(text="Пройти опрос", web_app=web_app).as_markup()
             await bot.send_message(
                 user.telegram_id,
                  f"Прошла неделя после повторения слов. Пожалуйста, пройдите опрос.",
                   reply_markup=keyboard
              )
             
async def new_user(telegram_id) -> None:
    """
    Создает нового пользователя в базе данных.

    Args:
        telegram_id: ID пользователя в Telegram.
        session: Объект сессии SQLAlchemy.
    """
    logging.info('Создаю нового пользователя')
    async for session in get_db():
        try:
            # Проверяем, существует ли пользователь с таким telegram_id.
            # Если да, то ничего не делаем
            existing_user = await session.scalar(select(User).filter_by(telegram_id=telegram_id))
            if existing_user:
                return

            # Создаем нового пользователя и сохраняем в сессии.
            new_user = User(telegram_id=telegram_id)
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)  # Обновляем объект, чтобы получить id
            logging.info(f"Пользователь с ID {telegram_id} успешно создан.")

        except Exception as e:
            logging.error(f"Ошибка при создании пользователя: {e}")
            await session.rollback()  # Важно! Отменяем изменения при ошибке