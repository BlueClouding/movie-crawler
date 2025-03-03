from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from sqlalchemy import select

from app.db.entity.download import Magnet
from app.db.entity.movie import Movie # Import select for async queries
from .base_service import BaseService

class MagnetService(BaseService[Magnet]):
    def __init__(self, db: AsyncSession): # Corrected to AsyncSession
        super().__init__(db, Magnet)

    async def get_by_movie_id(self, movie_id: int) -> List[Magnet]:
        query = select(Magnet).where(Magnet.movie_id == movie_id) # Use select and where
        result = await self.db.execute(query) # Use session.execute() and await
        return result.scalars().all() # Use .scalars().all() for async results

    async def add_to_movie(self, movie_id: int, url: str, name: str = None, size: str = None, created_date = None) -> Optional[Magnet]:
        # 检查电影是否存在
        movie = await self.db.execute(select(Movie).where(Movie.id == movie_id)) # Use session.execute() and select
        movie = movie.scalar_one_or_none() # Get single result or None using scalar_one_or_none (async equivalent of first())

        if not movie:
            return None

        magnet = Magnet(
            movie_id=movie_id,
            url=url,
            name=name,
            size=size,
            created_date=created_date
        )

        self.db.add(magnet)
        await self.db.commit() # Await commit
        await self.db.refresh(magnet) # Await refresh
        return magnet