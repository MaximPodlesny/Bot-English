from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from alembic import context
from config import DATABASE_URL


engine = create_engine(DATABASE_URL.replace("'", "") , echo=True)  # Echo=True для вывода SQL-запросов

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    words_per_day = Column(Integer, default=10)  # Новое поле: количество слов в день
    days_between_lessons = Column(Integer, default=1)  # Новое поле: интервал между уроками
    user_words = relationship("UserWord", back_populates="user")


class Word(Base):
    __tablename__ = "words"
    id = Column(Integer, primary_key=True)
    english = Column(String)
    russian = Column(String)
    category = Column(String, default="new")
    audio_path = Column(String, nullable=True)  # Добавляем поле для пути к аудиофайлу
    user_words = relationship("UserWord", back_populates="word")


class UserWord(Base):
    __tablename__ = "user_words"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    word_id = Column(Integer, ForeignKey("words.id"))
    last_repeat_time = Column(DateTime)
    correct_answers = Column(Integer, default=0)
    incorrect_answers = Column(Integer, default=0)
    current_step = Column(Integer, default=0)  # Новый столбец: текущий шаг повторения
    user = relationship("User", back_populates="user_words")
    word = relationship("Word", back_populates="user_words")

async_engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

async def init_db():
    async with async_engine.begin() as conn:
      await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
       yield session

if __name__ == "__main__":
    pass