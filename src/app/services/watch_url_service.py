from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from sqlalchemy import select, asc

from app.db.entity.download import WatchUrl
from app.db.entity.movie import Movie # Import select and asc
from .base_service import BaseService

class WatchUrlService(BaseService[WatchUrl]):
    def __init__(self, db: AsyncSession): # Corrected to AsyncSession
        super().__init__(db, WatchUrl)

    async def get_by_movie_id(self, movie_id: int) -> List[WatchUrl]:
        query = select(WatchUrl).where(WatchUrl.movie_id == movie_id).order_by(asc(WatchUrl.index)) # Use select, where, and order_by asc
        result = await self.db.execute(query) # Use session.execute() and await
        return result.scalars().all() # Use .scalars().all() for async results

    async def add_to_movie(self, movie_id: int, url: str, name: str = None, index: int = 0) -> Optional[WatchUrl]:
        # 检查电影是否存在
        movie_result = await self.db.execute(select(Movie).where(Movie.id == movie_id)) # Use session.execute() and select
        movie = movie_result.scalar_one_or_none() # Use scalar_one_or_none (async equivalent of first())
        if not movie:
            return None

        watch_url = WatchUrl(
            movie_id=movie_id,
            url=url,
            name=name,
            index=index
        )

        self.db.add(watch_url)
        await self.db.commit() # Await commit
        await self.db.refresh(watch_url) # Await refresh
        return watch_url