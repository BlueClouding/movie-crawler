import logging
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from sqlalchemy import and_, select, desc

from app.db.entity.enums import SupportedLanguage
from app.db.entity.genre import Genre, GenreName
from app.db.entity.movie import Movie
from app.db.entity.movie_actress import MovieActress
from app.db.entity.movie_genres import MovieGenre
from app.db.entity.movie_info import MovieTitle
from app.models.response.movie_response import MovieDetailResponse

from .base_service import BaseService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm import contains_eager

class MovieService(BaseService[Movie]):
    def __init__(self, db: AsyncSession): # Corrected to AsyncSession
        super().__init__(db, Movie)

    async def get_by_code(self, code: str, language: str) -> Optional[MovieDetailResponse]:
        stmt = (
            select(Movie)
            .outerjoin(
                MovieTitle,  # 标题表
                and_(MovieTitle.movie_id == Movie.id, MovieTitle.language == language)
            )
            .outerjoin(
                Movie.genre_associations  # 使用ORM关系（中间表）
            )
            .outerjoin(
                MovieGenre.genre  # 中间表 -> Genre表
            )
            .outerjoin(
                GenreName,        # Genre名称表
                and_(GenreName.genre_id == Genre.id, GenreName.language == language)
            )
            .where(Movie.code == code)
            .options(
                contains_eager(Movie.titles),
                contains_eager(Movie.genre_associations).contains_eager(MovieGenre.genre),
                selectinload(Movie.actress_associations).joinedload(MovieActress.actress),
                selectinload(Movie.download_urls),
                selectinload(Movie.magnets),
            )
        )
        
        result = await self.db.execute(stmt)
        movie = result.unique().scalar_one_or_none()
        return MovieDetailResponse.model_validate(movie) if movie else None  

    async def get_by_id(self, id: int) -> Optional[Movie]:
        result = await self.db.execute(select(Movie).where(Movie.id == id)) # Use session.execute() and select
        return result.scalar_one_or_none() # Use scalar_one_or_none (async equivalent of first())

    async def search_by_title(
        self,
        title: str,
        language: Optional[SupportedLanguage] = None,  # 参数类型为枚举成员
        skip: int = 0,
        limit: int = 20
    ) -> List[Movie]:
        query = select(Movie).join(MovieTitle)
        query = query.where(MovieTitle.title.ilike(f"%{title}%"))

        if language:
            # 直接使用枚举成员，SQLAlchemy 会自动转换为对应的值（如 'ja'）
            query = query.where(MovieTitle.language == language)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

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