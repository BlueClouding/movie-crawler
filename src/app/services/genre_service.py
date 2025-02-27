from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from sqlalchemy import select  # Import select for async queries
from app.models import Genre, GenreName, SupportedLanguage, Movie
from .base_service import BaseService

class GenreService(BaseService[Genre]):
    def __init__(self, db: AsyncSession): # Corrected to AsyncSession
        super().__init__(db, Genre)

    async def search_by_name(self, name: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 20) -> List[Genre]:
        query = select(Genre).join(GenreName) # Use select instead of db.query

        if language:
            query = query.where(GenreName.language == language) # Use where instead of filter in SQLAlchemy 2.0+

        query = query.where(GenreName.name.ilike(f"%{name}%")) # Use where instead of filter in SQLAlchemy 2.0+
        result = await self.db.execute(query.offset(skip).limit(limit)) # Use session.execute() and await
        return result.scalars().all() # Use .scalars().all() for async results

    async def add_name(self, genre_id: int, name: str, language: SupportedLanguage) -> Optional[GenreName]:
        genre = await self.get_by_id(genre_id) # Use await for async get_by_id
        if not genre:
            return None

        genre_name = GenreName(genre_id=genre_id, name=name, language=language)
        self.db.add(genre_name)
        await self.db.commit() # Await commit
        await self.db.refresh(genre_name) # Await refresh
        return genre_name

    async def get_movies_by_genre(self, genre_id: int, skip: int = 0, limit: int = 20) -> List[Movie]:
        genre = await self.get_by_id(genre_id) # Use await for async get_by_id
        if not genre:
            return []

        query = select(Movie).join(Movie.genres).where(Genre.id == genre_id) # Use select and where
        result = await self.db.execute(query.offset(skip).limit(limit)) # Use session.execute() and await
        return result.scalars().all() # Use .scalars().all() for async results