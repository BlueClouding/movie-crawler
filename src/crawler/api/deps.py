from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import async_session
from app.services import ServiceFactory

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting DB session
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_services(db: AsyncSession = Depends(get_db)) -> ServiceFactory:
    """
    Dependency for getting services factory
    """
    return ServiceFactory(db)
