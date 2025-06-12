from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from common.db.entity.download_url import DownloadUrl
from common.db.entity.movie import Movie
from .base_service import BaseService


class DownloadUrlService(BaseService[DownloadUrl]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, DownloadUrl)

    async def get_by_movie_code(self, movie_code: str) -> List[DownloadUrl]:
        result = await self.db.execute(
            select(DownloadUrl)
            .filter(DownloadUrl.code == movie_code)
            .order_by(DownloadUrl.id)
        )
        return result.scalars().all()

    async def add_to_movie(self, movie_code: str, magnet: str) -> Optional[DownloadUrl]:
        # 检查电影是否存在
        result = await self.db.execute(select(Movie).filter(Movie.code == movie_code))
        movie = result.scalars().first()
        if not movie:
            return None

        download_url = DownloadUrl(code=movie_code, magnet=magnet)

        self.db.add(download_url)
        await self.db.commit()
        await self.db.refresh(download_url)
        return download_url
