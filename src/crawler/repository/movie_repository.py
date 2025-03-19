from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, join, outerjoin

from common.enums.enums import SupportedLanguage
from common.db.entity.movie import Movie
from common.db.entity.movie_actress import MovieActress
from common.db.entity.movie_genres import MovieGenre
from common.db.entity.movie_info import MovieTitle
from common.db.entity.actress import Actress, ActressName
from common.db.entity.genre import Genre, GenreName
from common.db.entity.download import Magnet, DownloadUrl, WatchUrl
from app.repositories.base_repository import BaseRepositoryAsync
from app.config.database import get_db_session
from fastapi import Depends
from common.db.entity.movie import MovieStatus

class MovieRepository(BaseRepositoryAsync[Movie, int]):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)


    # get status new movie with limit
    async def get_new_movies(self, limit: int = 100):
        """
        Get new movies with limit.
        
        Args:
            limit: Number of movies to retrieve
        
        Returns:
            List[Movie]: List of new movies
        """
        query = select(Movie).where(Movie.status == MovieStatus.NEW.value).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()