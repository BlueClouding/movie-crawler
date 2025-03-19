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
        saved_count = 0
        for movie in movies:
            try:
                self.db.add(movie)
                await self.db.flush()  # 使用 flush 可以在提交前捕获异常
                saved_count += 1
            except Exception as e:
                self._logger.error(f"保存电影数据失败 (唯一约束冲突): {e}")
                continue
        await self.db.commit()  # 提交所有成功保存的电影
        return saved_count