import asyncio
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import text
from sqlalchemy.sql import delete

from create_tables import UserWord, Word, get_db

async def clear_words_table(session):
    """
    Clears the 'words' table and associated UserWord entries using SQLAlchemy.
    It also resets the id sequence.
    """
    try:
        # 1. Delete all UserWord entries that relate to Words
        await session.execute(delete(UserWord).where(UserWord.word_id.in_(select(Word.id).scalar_subquery())))
        # 2. Delete all Word entries
        await session.execute(delete(Word))
        await session.commit()
            # 3. Reset the sequence.
        await session.execute(text("ALTER SEQUENCE words_id_seq RESTART WITH 1;"))
        await session.commit()

        print("Table 'words' cleared and sequence reset successfully.")

    except Exception as e:
        print(f"An error occurred while clearing the table and resetting sequence: {e}")


async def main():
  async for session in get_db():
    await clear_words_table(session)

if __name__ == "__main__":
  asyncio.run(main())