from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_session
from .base_repository import BaseRepository
from app.db.entity.crawler import PagesProgress

class PageCrawlerRepository(BaseRepository[PagesProgress, int]):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)