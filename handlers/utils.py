# --- Функции работы с данными ---
import asyncio
from datetime import datetime, timedelta
import logging
import os
import re
from typing import List
from aiogram import Bot, Dispatcher, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from fastapi import Depends
from sqlalchemy import select, text, func
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import bot
from db.create_tables import User, UserWord, Word, get_db
from pydub import AudioSegment
from pydub.audio_segment import AudioSegment
from tempfile import NamedTemporaryFile
from PyDictionary import PyDictionary
# import nltk
# from nltk.corpus import cmudict
# from phonemizer import phonemize
# from phonemizer.backend.espeak.wrapper import EspeakWrapper
# _ESPEAK_LIBRARY = r'C:\Program Files\eSpeak NG\libespeak-ng.dll'
# EspeakWrapper.set_library(_ESPEAK_LIBRARY)
# from jamo import h2j, j2hcj
import eng_to_ipa as p 
import segments
# from google.cloud import texttospeech  # For Text-to-Speech API
from translatepy import Translate
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
    logging.info("Создаёт запись в таблице user_words")
    try:
        user = await session.get(User, user_id) # Получаем пользователя
        if not user:
           print(f"Пользователь с id {user_id} не найден")
           return None
        user_word = UserWord(user_id=user_id, word_id=word.id)
        user.last_repeat_time=datetime.now()
        user.current_step=0
        session.add(user)
        session.add(user_word)
        await session.commit()
        await session.refresh(user_word)
        await session.refresh(user)
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

# async def load_words_from_file(file_path, session, audio_dir=None):
#     """Загружает слова из файла и добавляет в базу данных."""
#     try:
#         with open(file_path, 'r', encoding='utf-8') as file:
#             for line in file:
#                 try:
#                     parts = line.strip().split('-')
#                     if len(parts) == 3:  # если есть аудиофайл
#                         english, russian, audio_file = parts
#                         english = english.strip()
#                         russian = russian.strip()
#                         audio_file = audio_file.strip()
#                         if audio_dir:
#                             audio_path = os.path.join(audio_dir, audio_file)  # Полный путь к аудиофайлу
#                         else:
#                             audio_path = audio_file

#                         word = Word(english=english, russian=russian, audio_path=audio_path)
#                     elif len(parts) == 2:
#                         english, russian = parts
#                         english = english.strip()
#                         russian = russian.strip()
#                         word = Word(english=english, russian=russian)
#                     else:
#                         logging.warning(f"Неправильная строка '{line}' в файле. Пропускаю.")
#                         continue
#                     session.add(word)
#                     await session.commit()
#                     await session.refresh(word)

#                 except ValueError as e:
#                     logging.warning(f"Неправильная строка '{line}' в файле: {e}. Пропускаю.")
#                     continue

#         logging.info("Слова успешно загружены в базу данных.")
#     except FileNotFoundError:
#         logging.error(f"Файл '{file_path}' не найден")
#     except Exception as e:
#         logging.error(f"Ошибка при загрузке слов: {e}")

def truncate_text(text: str, max_length: int = 21) -> str:
    """Ограничивает текст до заданной длины."""
    if len(text) > max_length:
        return text[:max_length - 3] + "..."  # Добавляем "..." для обозначения сокращения
    return text

# def get_repeat_time(current_step: int) -> timedelta:
#     """Возвращает интервал повторения по текущему шагу."""
#     if current_step == 0:
#         return timedelta(hours=1)
#     elif current_step == 1:
#         return timedelta(hours=5)
#     elif current_step == 2:
#         return timedelta(hours=24)
#     elif current_step == 3:
#         return timedelta(days=4)
#     elif current_step == 4:
#         return timedelta(days=14)
#     elif current_step == 5:
#         return timedelta(days=30)
#     else:
#         return timedelta(days=30)
def get_repeat_time(current_step: int) -> timedelta:
    """Возвращает интервал повторения по текущему шагу."""
    if current_step == 0:
        return timedelta(minutes=5)
    elif current_step == 1:
        return timedelta(minutes=8)
    elif current_step == 2:
        return timedelta(minutes=10)
    elif current_step == 3:
        return timedelta(minutes=15)
    elif current_step == 4:
        return timedelta(minutes=20)
    else:
        return timedelta(minutes=20) 
    
async def change_num_of_calls():
    async for session in get_db():
        all_users = await session.scalars(select(User))
        for user in all_users:
            user.num_of_calls = 0
        await session.commit()

async def check_if_words_need_review():
    """Проверяет, не нужно ли проводить опрос по словам, учитывая current_step и отправляет уведомления."""
    while True:
        try:
            logging.info('Проверяю, не нужно ли проводить опрос по словам, учитывая current_step')
            async for session in get_db():
                all_users = await session.scalars(select(User))
                for user in all_users:
                    if not user.num_of_calls:
                        # user_words_for_review = await session.scalars(
                        #     select(UserWord)
                        #     .where(UserWord.user_id == user.id)
                        # )
                        # user_words_for_review = user_words_for_review.all()
                        repeat_time = get_repeat_time(user.current_step)
                        # for user_word in user_words_for_review:
                        if user.last_repeat_time and user.last_repeat_time <= datetime.now() - repeat_time:
                            web_app = types.WebAppInfo(url=f'{WEB_APP_URL}?telegram_id={user.telegram_id}&type=repeat')
                            keyboard = InlineKeyboardBuilder().button(text="Повторить", web_app=web_app).as_markup()
                            # await bot.bot.
                            await bot.bot.send_message(
                                user.telegram_id,
                                f"Пришло время повторить слова. Пожалуйста, пройдите в приложение.",
                                reply_markup=keyboard
                            )
                            user.last_repeat_time = datetime.now()
                            user.num_of_calls = 1
                            if user.current_step < 4:
                                user.current_step += 1
                            await session.commit()
                            await call_for_repeat(user.id)
                            # break
        except Exception as e:
            logging.info(f'Ошибка проверки, не нужно ли проводить опрос по словам, учитывая current_step {str(e)}')
        await asyncio.sleep(55)  # Проверяем каждый час

async def check_if_words_need_review_by_user(user_id):
    logging.info(f'Запущена напоминалка для {user_id}')
    while True:
        async for session in get_db():
            user = (await session.scalars(select(User).where(User.id == user_id))).first()
            if user:
                if user.num_of_calls < 5:
                    web_app = types.WebAppInfo(url=f'{WEB_APP_URL}?telegram_id={user.telegram_id}&type=repeat')
                    keyboard = InlineKeyboardBuilder()
                    keyboard.button(text="Повторить", web_app=web_app)
                    keyboard.button(text="Отмена", callback_data=f"cancel_repeat")
                    await bot.bot.send_message(
                        user.telegram_id,
                        f"Вы пропустили повторение слов. Это сильно влияет на качество запоминания. Выделите время и повторите слова, это займет всего пару минут...",
                        reply_markup=keyboard.as_markup()
                    )
                    user.num_of_calls += 1
                    await session.commit()
                else:
                    user.num_of_calls = 0
                    await session.commit()
                    task = asyncio.current_task()
                    task.cancel()  # Отмена задачи
                    await task  # Ожидание завершения задачи
                    print("Задача отменена")
            else:
                print(f"Пользователь с ID {user_id} не найден.")
        await asyncio.sleep(60)
        
async def call_for_repeat(user_id):
    await asyncio.sleep(60)
    task = asyncio.create_task(check_if_words_need_review_by_user(user_id))
    return task
           
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

# Создание словаря
async def load_words_from_file(file_path, session, audio_dir='english_words_fastapi/static/pronounce'):
    """Loads words from a file, retrieves translations and transcriptions,
    and handles audio files with a 1-second pause.  Uses translatepy.
    """
    translator = Translate()  # Initialize the translator
    dictionary = PyDictionary()
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                try:
                    parts = line.strip().split('-')

                    if len(parts) == 3:
                        english_word, russian_word, audio_filename = parts
                        english_word = english_word.strip()
                        russian_word = russian_word.strip()
                        audio_filename = audio_filename.strip()
                    elif len(parts) == 2:
                        english_word, russian_word = parts
                        english_word = english_word.strip()
                        russian_word = russian_word.strip()
                    elif len(parts) == 1:
                        try:
                            word = parts
                            word = word.strip()
                            if translator.language(word) == 'Russian':
                                russian_word = word
                                english_word = translator.translate(russian_word, destination_language='en')
                            elif translator.language(word) == 'English':
                                russian_word = translator.translate(english_word, destination_language='ru')
                                english_word = word
                        except Exception as e:
                         logging.error(f"Error during translation: {e}. Skipping line: {line}")
                         continue

                    else:
                        logging.warning(f"Invalid line '{line}' in file. Skipping.")
                        continue

                    # Get transcription
                    # transcription = translator.transliterate(english_word)
                    transcription = p.convert(english_word)

                    # Fetch transcription (using translatepy)
                    audio_path = os.path.join(audio_dir, f"{english_word.replace(' ', '_')}.mp3") if audio_dir else f"{english_word.replace(' ', '_')}.mp3"
                    if not os.path.exists(audio_path):
                        try:
                            speech = translator.text_to_speech(english_word)       
                            speech.write_to_file(audio_path)
                        except Exception as e:
                            logging.error(f"Error getting transcription: {e}. Skipping line: {line}")
                            speech = None

                    # Handle audio generation
                    # audio_path = await generate_audio_with_pause(audio_dir, english_word)
                       

                    if english_word and russian_word:
                        if not await session.scalar(select(Word).where(Word.english == english_word)):
                            word = Word(english=english_word, russian=russian_word, transcription=f'[{transcription}]', audio_path=audio_path if audio_path else None)
                            session.add(word)
                            await session.commit()
                            await session.refresh(word)

                except ValueError as e:
                    logging.warning(f"Invalid line '{line}' in file: {e}. Skipping.")
                    continue

        logging.info("Words successfully loaded into the database.")

    except FileNotFoundError:
        logging.error(f"File '{file_path}' not found")
    except Exception as e:
        logging.error(f"Error loading words: {e}")

# def get_phonetic_transcription(word):
#     """Возвращает фонетическую транскрипцию английского слова."""
#     try:
#         pronouncing_dict = cmudict.dict()
#         if word.lower() in pronouncing_dict:
#             phonemes = pronouncing_dict[word.lower()][0]
#             transcription = f"[{' '.join(phonemes)}]"
#             logging.info(f"Транскрипция для '{word}': {transcription}")
#             return transcription
#         else:
#              logging.warning(f"Транскрипция для '{word}' не найдена")
#              return None
#     except Exception as e:
#         logging.error(f"Ошибка при получении транскрипции для '{word}': {e}")
#         return None


async def generate_audio_with_pause(text, audio_dir, filename):
    """Generates audio with a 1-second pause."""

    try:
        audio_file_path = os.path.join(audio_dir, f"{filename.replace(' ', '_')}.mp3") if audio_dir else f"{filename.replace(' ', '_')}.mp3"

        # Create 1 second of silence
        silence = AudioSegment.silent(duration=1000) # Corrected here!

        # This should be adjusted depending on the API response format
        audio_segment = AudioSegment.from_file(audio_file_path, format='mp3')

        # Combine the silence with the generated audio
        final_audio = silence + audio_segment

        final_audio.export(audio_file_path, format='mp3')
        return audio_file_path
    except Exception as e:
        logging.error(f"Error generating audio: {e}")
        return None

async def add_word(text, user_telegram_id, audio_dir='english_words_fastapi/static/pronounce'):
    """
    Gets or creates a word based on English or Russian text and associates it with a user.
    Uses deep_translator for language detection and translation.

    Args:
        session: SQLAlchemy session.
        text: English or Russian word to search for.
        user_telegram_id: Telegram ID of the user.

    Returns:
        The Word object.
    """
    async for session in get_db():
        translator = Translate()  # Initialize the translator
        
        # Get user from db or return None
        user = await session.scalar(select(User).filter_by(telegram_id=user_telegram_id))
        if not user:
            print(f"User with telegram_id {user_telegram_id} not found.")
            return None

        #First try to find the word from db, using lowercase for case insensitive search
        word = (
            await session.scalar(select(Word)
            .filter(
                (func.lower(Word.english) == func.lower(text))
                | (func.lower(Word.russian) == func.lower(text))
            ))
        )

        if word:
            # Check if user already has the word
            user_word = await session.scalar(select(UserWord).filter(UserWord.user_id == user.id, UserWord.word == word))

            if user_word:
                print(f"Word '{text}' already exists and is associated with user {user_telegram_id}.")
                # return True
            else:
                user_word = UserWord(user_id=user.id, word_id=word.id)
                session.add(user_word)
                session.commit()
                print(f"Word '{text}' already exists but is added to user {user_telegram_id}.")
            return True
        else:
            # Translate the word and create word entry
            word_text = text.strip()
            lang = translator.language(word_text)
            print(f'!!!\n\n\n', lang.__str__())
            if translator.language(word_text) == 'ru':
                russian_word = word_text
                english_word = translator.translate(russian_word, destination_language='en')
            elif translator.language(word_text) == 'en':
                russian_word = translator.translate(english_word, destination_language='ru')
                english_word = word_text
            else:
                print(f"Could not detect language for {text}")
                return None
            transcription = p.convert(english_word)

            # Fetch transcription (using translatepy)
            audio_path = os.path.join(audio_dir, f"{english_word.replace(' ', '_')}.mp3") if audio_dir else f"{english_word.replace(' ', '_')}.mp3"
            if not os.path.exists(audio_path):
                try:
                    speech = translator.text_to_speech(english_word)       
                    speech.write_to_file(audio_path)
                except Exception as e:
                    speech = None
            new_word = Word(english=english_word, russian=russian_word, transcription=f'[{transcription}]', audio_path=audio_path if audio_path else None)
            session.add(new_word)
            session.commit()

            user_word = UserWord(user_id=user.id, word_id=new_word.id)
            session.add(user_word)
            session.commit()

            print(f"Word '{text}' was created and associated with user {user_telegram_id}.")
            return new_word
        
# client = AsyncOpenAI(api_key=GPT_KEY)
async def process_commitment_gpt(message: types.Message, client):
    

    prompt = 'Ты  -  умный  и  дружелюбный  учитель английского языка с большим опытом.\
              **Твои  основные  задачи:**\
              *   **Помогаешь в изучении английских слов:**  используешь научный подход к обучению, основанный на системе Spaced Repetition (SR).  Это значит, что вы будете повторять слова в оптимальные моменты, чтобы закрепить их в памяти надолго. \
\
Вот как это работает:\
\
* Удобные порции:  Выбирайте, сколько слов вы хотите учить за раз (от 10 до 100). \
* Гибкий график:  Настраивайте интервалы между подачей новых порций слов (от 1 до 3 дней).\
* Оптимальные повторения:  Бот автоматически напомнит вам о повторении слов в нужное время: \
    * Первое повторение:  через час\
    * Второе повторение:  через 5 часов\
    * Третье повторение:  через 24 часа\
    * Четвертое повторение:  через 4 дня\
    * Пятое повторение:  через 14 дней\
    * Шестое повторение:  через 30 дней\
    * Далее:  раз в 30 дней\
\
Почему такой подход работает?\
\
* Научно доказано:  Система SR основана на принципах кривой забывания Эббингауза, которая показывает, как быстро мы забываем информацию.  \
* Эффективность:  Повторение слов в оптимальные моменты помогает закрепить их в долговременной памяти.\
* Экономия времени:  пользователь учит слова более эффективно, тратя меньше времени на зубрежку.\
              *   **Если ты получаешь слово: если слово русское, переводишь его на английский, если солово английское, переводишь его на русский, и добавляешь сононимы и антонимы и выводишь в структурированном виде.\
              *   **Если нужно добавить слово для изучения в базу данных: отвечаешь фразой: "add word {слово которое нужно добавить}".\
              *   **Если нужно добавить слова из конкретного предложения для изучения в базу данных: отвечаешь фразой: "add words from sentence {предложение без знаков препинания}".\
              ** Пиши на русском. **'


    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
            "role": "system",
            "content": prompt,
            },
            {
            "role": "user",
            "content": message.text
            }],
        web_search = False
    )
    result = response.choices[0].message.content
    if result:
        if "add word" in result:
            logging.info('\n\n!!!!\n\n in add word')
            await add_word(result.split()[-1], message.from_user.id)
        elif "add words from sentence" in result:
            logging.info('\n\n!!!!\n\n in add words from sentence')

            for word in (result.replace('in add words from sentence', '')).split():
                if word.len() > 2:
                    await add_word(word, message.from_user.id)
        else:
            await message.answer(response.choices[0].message.content)
        
        
    else:
        await message.answer(response.choices[0].message.content)
    
# async def load_words_from_file(file_path, session, audio_dir=None, google_credentials_path=None):
#     """
#     Loads words from a file, adds translations if missing, retrieves transcriptions, 
#     and handles audio files with a 1-second pause.
#     """
#     dictionary = PyDictionary()
#     if google_credentials_path:
#       os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = google_credentials_path
#       tts_client = texttospeech.TextToSpeechClient()
#     else:
#       tts_client = None

#     try:
#         with open(file_path, 'r', encoding='utf-8') as file:
#             for line in file:
#                 try:
#                     parts = line.strip().split('-')
#                     english = None
#                     russian = None
#                     audio_file = None

#                     if len(parts) == 3:
#                         english, russian, audio_file = parts
#                         english = english.strip()
#                         russian = russian.strip()
#                         audio_file = audio_file.strip()
#                     elif len(parts) == 2:
#                         english, russian = parts
#                         english = english.strip()
#                         russian = russian.strip()
#                     else:
#                         logging.warning(f"Неправильная строка '{line}' в файле. Пропускаю.")
#                         continue

#                     # Fetch missing translations
#                     if not english:
#                        if russian:
#                            english = await fetch_translation(russian,'ru','en', session)

#                        else:
#                           logging.warning(f"Нет английского или русского перевода в строке'{line}'. Пропускаю")
#                           continue
#                     elif not russian:
#                         russian = await fetch_translation(english,'en','ru', session)

#                     # Get transcription
#                     transcription = await fetch_transcription(english, dictionary)

#                     # Handle audio file (add pause and generate if needed)
#                     audio_path = None
#                     if audio_file:
#                        if audio_dir:
#                             audio_path = os.path.join(audio_dir, audio_file)
#                        else:
#                             audio_path = audio_file
#                     elif tts_client:
#                        audio_path = await generate_audio_with_pause(english, tts_client, audio_dir)

#                     if english and russian:
#                        word = Word(english=english, russian=russian, transcription=transcription, audio_path=audio_path)
#                        session.add(word)
#                        await session.commit()
#                        await session.refresh(word)

#                 except ValueError as e:
#                    logging.warning(f"Неправильная строка '{line}' в файле: {e}. Пропускаю.")
#                    continue
#         logging.info("Слова успешно загружены в базу данных.")

#     except FileNotFoundError:
#         logging.error(f"Файл '{file_path}' не найден")
#     except Exception as e:
#         logging.error(f"Ошибка при загрузке слов: {e}")

# async def fetch_translation(word, source_lang, target_lang, session):
#     """Fetches a translation using a direct database query."""
#     try:
#         translation = await session.execute(
#             text(f"SELECT translation FROM translations WHERE source_word = '{word}' AND source_lang = '{source_lang}' AND target_lang = '{target_lang}'")
#         )
#         translation = translation.scalar_one_or_none()
#         if translation:
#             return translation

#         logging.warning(f"Не удалось найти перевод '{word}' из языка '{source_lang}' в '{target_lang}'.")
#         return None

#     except Exception as e:
#         logging.error(f"Ошибка во время запроса перевода '{word}' из '{source_lang}' в '{target_lang}': {e}")
#         return None

# async def fetch_transcription(english, dictionary):
#     """Fetches the transcription for an English word."""
#     try:
#         ipa_data = dictionary.get_pronunciation(english)
#         if ipa_data:
#           return ipa_data[0]
#         else:
#           logging.warning(f"Транскрипция не найдена для слова: {english}")
#           return None
#     except Exception as e:
#        logging.error(f"Ошибка при получении транскрипции: {e}")
#        return None

# async def generate_audio_with_pause(text, tts_client, audio_dir):
#     """Generates audio for the given text with a 1-second pause at the start."""
#     try:
#         synthesis_input = texttospeech.SynthesisInput(text=text)
#         voice = texttospeech.VoiceSelectionParams(
#            language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
#         )
#         audio_config = texttospeech.AudioConfig(
#           audio_encoding=texttospeech.AudioEncoding.MP3
#         )
#         response = await asyncio.to_thread(tts_client.synthesize_speech,
#             input=synthesis_input, voice=voice, audio_config=audio_config)

#         # Create 1 second of silence
#         silence = Silent(duration=1000).to_audio_segment()
#         audio_segment = AudioSegment.from_file(NamedTemporaryFile().name, format='mp3')
#         audio_segment = audio_segment.from_bytes(response.audio_content, format='mp3')

#         # Combine the silence with the generated audio
#         final_audio = silence + audio_segment

#         if audio_dir:
#             audio_file = f"{text.replace(' ', '_')}.mp3"  # use original word as a filename
#             audio_path = os.path.join(audio_dir, audio_file)
#         else:
#             audio_file = f"{text.replace(' ', '_')}.mp3"
#             audio_path = audio_file

#         # Export the final combined audio
#         final_audio.export(audio_path, format="mp3")
#         return audio_path

#     except Exception as e:
#         logging.error(f"Ошибка при генерации аудио: {e}")
#         return None