import logging
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from sqlalchemy import select, desc # Import select and desc for async queries
from app.models import Movie, MovieTitle, SupportedLanguage
from .base_service import BaseService
from sqlalchemy.ext.asyncio import AsyncSession

class MovieService(BaseService[Movie]):
    def __init__(self, db: AsyncSession): # Corrected to AsyncSession
        super().__init__(db, Movie)

    async def get_by_code(self, code: str) -> Optional[Movie]:
        result = await self.db.execute(select(Movie).where(Movie.code == code)) # Use session.execute() and select
        logging.debug(f"计算结果: {result}")
        return result.scalar_one_or_none() # Use scalar_one_or_none (async equivalent of first())

    async def search_by_title(self, title: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 20) -> List[Movie]:
        query = select(Movie).join(MovieTitle) # Use select and join

        if language:
            query = query.where(MovieTitle.language == language) # Use where instead of filter

        query = query.where(MovieTitle.title.ilike(f"%{title}%")) # Use where instead of filter
        result = await self.db.execute(query.offset(skip).limit(limit)) # Use session.execute() and await
        return result.scalars().all() # Use .scalars().all() for async results

    async def get_recent_releases(self, days: int = 30, skip: int = 0, limit: int = 20) -> List[Movie]:
        cutoff_date = date.today() - timedelta(days=days)
        query = select(Movie).where(Movie.release_date >= cutoff_date).order_by(desc(Movie.release_date)) # Use select, where, and desc
        result = await self.db.execute(query.offset(skip).limit(limit)) # Use session.execute() and await
        return result.scalars().all() # Use .scalars().all() for async results

    async def get_popular_movies(self, skip: int = 0, limit: int = 20) -> List[Movie]:
        query = select(Movie).order_by(desc(Movie.likes)) # Use select and order_by desc
        result = await self.db.execute(query.offset(skip).limit(limit)) # Use session.execute() and await
        return result.scalars().all() # Use .scalars().all() for async results

    async def increment_likes(self, movie_id: int) -> Optional[Movie]:
        movie = await self.get_by_id(movie_id) # Use await for async get_by_id
        if not movie:
            return None

        movie.likes += 1
        await self.db.commit() # Await commit
        await self.db.refresh(movie) # Await refresh
        return movie

    async def add_title(self, movie_id: int, title: str, language: SupportedLanguage) -> Optional[MovieTitle]:
        movie = await self.get_by_id(movie_id) # Use await for async get_by_id
        if not movie:
            return None

        movie_title = MovieTitle(movie_id=movie_id, title=title, language=language)
        self.db.add(movie_title)
        await self.db.commit() # Await commit
        await self.db.refresh(movie_title) # Await refresh
        return movie_title