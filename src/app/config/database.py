from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.config.settings import settings
from typing import AsyncGenerator

# Use the DATABASE_URL from settings
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
    connect_args={
        "server_settings": {
            "search_path": "public"
        }
    }
)

async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()