from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database import get_db_session
from common.db.entity.crawler import VideoProgress
from app.repositories.base_repository import BaseRepositoryAsync
from common.db.entity.movie import Movie
from typing import List

class MovieCrawlerRepository(BaseRepositoryAsync[VideoProgress, int]):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)


    async def save_movies(self, movies: List[Movie]) -> int:
        self.db.add_all(movies)
        await self.db.commit()
        return len(movies)