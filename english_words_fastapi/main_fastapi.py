from datetime import datetime
import uvicorn
import logging
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from handlers.utils import create_user_word
from db.create_tables import User, UserWord, Word, get_db

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    cache_buster = int(time.time())
    return templates.TemplateResponse("index.html", {"request": request, "cache_buster": cache_buster})

@app.get("/word_data")
async def get_word_data(user_word_id: int, request: Request):
   async for session in get_db():
      user_word = await session.get(UserWord, user_word_id)
      if user_word and user_word.word:
        return {
            "english": user_word.word.english,
            "russian": user_word.word.russian,
            "audio_path": user_word.word.audio_path
        }
      else:
         raise HTTPException(status_code=404, detail="Word not found")


@app.get("/repeat_words/{telegram_id}", response_class=JSONResponse)
async def get_repeat_words_for_user(telegram_id: int):
    """Возвращает слова, которые нужно повторить для конкретного пользователя."""
    async for session in get_db():
        user = await session.scalar(select(User).filter_by(telegram_id=telegram_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_words = await session.scalars(
            select(UserWord)
            .where(UserWord.user_id == user.id)
            .options(selectinload(UserWord.word))
        )

        user_words = user_words.all()
        if not user_words:
             return []
        words_data = [
            {
                "id": user_word.id,
                "english": user_word.word.english,
                "russian": user_word.word.russian,
                "audio_path": user_word.word.audio_path if user_word.word.audio_path else None,
                "transcription": user_word.word.transcription
            }
             for user_word in user_words
        ]
        user.num_of_calls = 5
        await session.commit()
        return words_data

@app.get("/new_words/{telegram_id}", response_class=JSONResponse)
async def get_new_words_for_user(telegram_id: int):
    """Возвращает новые слова для конкретного пользователя."""
    async for session in get_db():
        user = await session.scalar(select(User).filter_by(telegram_id=telegram_id))
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user_settings = await session.scalar(select(User).filter_by(telegram_id=telegram_id))
        if not user_settings:
           return []

        words_per_day = user_settings.words_per_day

        subquery = select(UserWord.word_id).where(UserWord.user_id == user.id).scalar_subquery()

        query = select(Word).where(~Word.id.in_(subquery)).limit(words_per_day)
        words = await session.scalars(query)
        words = words.all()
        if not words:
            return []
        for word in words:
            user_word = await create_user_word(user.id, word, session)
        words_data = [
            {
                "id": word.id,
                "english": word.english,
                "russian": word.russian,
                "audio_path": word.audio_path if word.audio_path else None,
                "transcription": word.transcription
            }
             for word in words
        ]
        return {"words": words_data, "total_words_today": words_per_day}



# app = FastAPI()
# templates = Jinja2Templates(directory="templates")  # папка с html файлами
# app.mount("/static", StaticFiles(directory="static"), name="static") # папка со статическими файлами (css, js, images)

# @app.get("/", response_class=HTMLResponse)
# async def read_root(request: Request):
#       return templates.TemplateResponse("index.html", {"request": request})

# @app.get("/word_data")
# async def get_word_data(user_word_id: int, request: Request):
#    async for session in get_db():
#       user_word = await session.get(UserWord, user_word_id)
#       if user_word and user_word.word:
#         return {
#             "english": user_word.word.english,
#             "russian": user_word.word.russian,
#             "audio_path": user_word.word.audio_path
#         }
#       else:
#          raise HTTPException(status_code=404, detail="Word not found")


# @app.get("/repeat_words/{telegram_id}", response_class=JSONResponse)
# async def get_repeat_words_for_user(telegram_id: int):
#     """Возвращает слова, которые нужно повторить для конкретного пользователя."""
#     async for session in get_db():
#         user = await session.scalar(select(User).filter_by(telegram_id=telegram_id))
#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")

#         # now = datetime.now()
#         user_words = await session.scalars(
#             select(UserWord)
#             .where(UserWord.user_id == user.id)
#             .options(selectinload(UserWord.word))
#         )

#         user_words = user_words.all()
#         if not user_words:
#              return []  # Возвращаем пустой список, если нет слов для повторения
#         # Преобразуем user_words в список словарей
#         words_data = [
#             {
#                 "id": user_word.id,
#                 "english": user_word.word.english,
#                 "russian": user_word.word.russian,
#                 "audio_path": user_word.word.audio_path if user_word.word.audio_path else None
#             }
#              for user_word in user_words
#         ]
#         user.num_of_calls = 5
#         await session.commit()
#         return words_data

# @app.get("/new_words/{telegram_id}", response_class=JSONResponse)
# async def get_new_words_for_user(telegram_id: int):
#     """Возвращает новые слова для конкретного пользователя."""
#     print(f"/new_words/{telegram_id}")
#     async for session in get_db():
#         user = await session.scalar(select(User).filter_by(telegram_id=telegram_id))
#         if not user:
#             raise HTTPException(status_code=404, detail="User not found")

#         user_settings = await session.scalar(select(User).filter_by(telegram_id=telegram_id))
#         if not user_settings:
#            return []

#         words_per_day = user_settings.words_per_day

#         subquery = select(UserWord.word_id).where(UserWord.user_id == user.id).scalar_subquery()

#         query = select(Word).where(~Word.id.in_(subquery)).limit(words_per_day)
#         words = await session.scalars(query)
#         words = words.all()
#         if not words:
#             return []
#         for word in words:
#             user_word = await create_user_word(user.id, word, session)
#          # Преобразуем user_words в список словарей
#         words_data = [
#             {
#                 "id": word.id,
#                 "english": word.english,
#                 "russian": word.russian,
#                 "audio_path": word.audio_path if word.audio_path else None
#             }
#              for word in words
#         ]
#         return {"words": words_data, "total_words_today": words_per_day}
    
if __name__ == "__main__":
      uvicorn.run(app, host="0.0.0.0", port=8000, ssl_certfile="localhost+2.pem", ssl_keyfile="localhost+2-key.pem")