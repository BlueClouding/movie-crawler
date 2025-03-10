from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_session
from .base_repository import BaseRepository
from app.db.entity.crawler import PagesProgress

class GenrePageCrawlerRepository(BaseRepository[PagesProgress, int]):
    