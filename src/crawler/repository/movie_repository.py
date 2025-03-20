from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_

from common.db.entity.movie import Movie
from common.db.entity.download import Magnet, DownloadUrl, WatchUrl
from app.repositories.base_repository import BaseRepositoryAsync
from app.config.database import get_db_session
from fastapi import Depends
from common.db.entity.movie import MovieStatus
from sqlalchemy import update
from typing import List

class MovieRepository(BaseRepositoryAsync[Movie, int]):
    # if insert session use it
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)
        # 添加logger属性
        import logging
        self._logger = logging.getLogger(__name__)


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

    async def saveOrUpdate(self, movie_details: List[Movie], session: AsyncSession = None) -> bool:
        """Save or update movie details to the database.
        
        Args:       
            movie_details: Movie details dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """ 
        # for each movie detail
        for movie_detail in movie_details:
            try:    
                # 使用OR连接多个条件
                result = await session.execute(
                    select(Movie).where(Movie.code == movie_detail.code)
                )
                existing_movie = result.scalar_one_or_none()

                if existing_movie:
                    # Update existing movie
                    # 根据查询到的电影的ID来更新，而不是仅仅通过code
                    await session.execute(
                        update(Movie)
                        .where(Movie.id == existing_movie.id)
                        .values(**movie_detail.dict())
                    )
                    await session.commit()
                else:
                    session.add(movie_detail)
                    await session.commit()
                return True
            except Exception as e:
                self._logger.error(f"Error saving or updating movie: {str(e)}")
                return False