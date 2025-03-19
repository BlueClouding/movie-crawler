from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.config.settings import settings
from typing import AsyncGenerator, Optional
from contextvars import ContextVar

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

# 创建上下文变量来存储当前会话
_session_context: ContextVar[Optional[AsyncSession]] = ContextVar('_session_context', default=None)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    # 尝试从上下文中获取会话
    session = _session_context.get()
    if session is not None:
        yield session
        return
        
    # 如果上下文中没有会话，则创建新会话
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()