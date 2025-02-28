from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any

from db.entity.download import DownloadUrl
from db.entity.movie import Movie
from .base_service import BaseService

class DownloadUrlService(BaseService[DownloadUrl]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, DownloadUrl)
    
    async def get_by_movie_id(self, movie_id: int) -> List[DownloadUrl]:
        result = await self.db.execute(
            select(DownloadUrl)
            .filter(DownloadUrl.movie_id == movie_id)
            .order_by(DownloadUrl.index)
        )
        return result.scalars().all()
    
    async def add_to_movie(self, movie_id: int, url: str, name: str = None, host: str = None, index: int = 0) -> Optional[DownloadUrl]:
        # 检查电影是否存在
        result = await self.db.execute(
            select(Movie).filter(Movie.id == movie_id)
        )
        movie = result.scalars().first()
        if not movie:
            return None
        
        download_url = DownloadUrl(
            movie_id=movie_id,
            url=url,
            name=name,
            host=host,
            index=index
        )
        
        self.db.add(download_url)
        await self.db.commit()
        await self.db.refresh(download_url)
        return download_url