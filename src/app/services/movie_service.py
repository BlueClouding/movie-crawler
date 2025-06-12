import logging
from typing import List, Optional, Dict, Any
from datetime import date, timedelta
from sqlalchemy import and_, select, desc, join

from common.enums.enums import SupportedLanguage
from common.db.entity.genre import Genre, GenreName
from common.db.entity.movie import Movie
from common.db.entity.movie_actress import MovieActress
from common.db.entity.movie_genres import MovieGenre
from common.db.entity.movie_info import MovieTitle
from common.db.entity.actress import Actress, ActressName
from common.db.entity.download import Magnet, WatchUrl
from common.db.entity.download_url import DownloadUrl
from app.models.response.movie_response import MovieDetailResponse

from .base_service import BaseService
from sqlalchemy.ext.asyncio import AsyncSession


class MovieService(BaseService[Movie]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, Movie)

    async def get_by_code(
        self, code: str, language: str
    ) -> Optional[MovieDetailResponse]:
        # 获取电影基本信息
        movie_query = select(Movie).where(Movie.code == code)
        movie_result = await self.db.execute(movie_query)
        movie = movie_result.scalar_one_or_none()

        if not movie:
            return None

        # 获取电影标题 - 明确指定要查询的列
        title_query = select(
            MovieTitle.id, MovieTitle.movie_id, MovieTitle.language, MovieTitle.title
        ).where(and_(MovieTitle.movie_id == movie.id, MovieTitle.language == language))
        title_result = await self.db.execute(title_query)
        titles = [
            dict(zip(["id", "movie_id", "language", "title"], row))
            for row in title_result.all()
        ]

        # 获取电影类型 - 明确指定要查询的列
        genre_query = (
            select(
                Genre.id.label("genre_id"),
                Genre.urls.label("urls"),
                GenreName.id.label("name_id"),
                GenreName.name.label("name"),
                GenreName.language.label("language"),
            )
            .join(MovieGenre, Genre.id == MovieGenre.genre_id)
            .join(GenreName, Genre.id == GenreName.genre_id)
            .where(
                and_(MovieGenre.movie_id == movie.id, GenreName.language == language)
            )
        )
        genre_result = await self.db.execute(genre_query)
        genres = [dict(row) for row in genre_result.all()]

        # 获取电影演员 - 明确指定要查询的列
        actress_query = (
            select(
                Actress.id.label("actress_id"),
                ActressName.id.label("name_id"),
                ActressName.name.label("name"),
                ActressName.language.label("language"),
            )
            .join(MovieActress, Actress.id == MovieActress.actress_id)
            .join(ActressName, Actress.id == ActressName.actress_id)
            .where(
                and_(
                    MovieActress.movie_id == movie.id, ActressName.language == language
                )
            )
        )
        actress_result = await self.db.execute(actress_query)
        actresses = [dict(row) for row in actress_result.all()]

        # 获取下载链接 - 明确指定要查询的列
        download_query = (
            select(DownloadUrl.id, DownloadUrl.code, DownloadUrl.magnets)
            .where(DownloadUrl.code == movie.code)
            .order_by(DownloadUrl.id)
        )
        download_result = await self.db.execute(download_query)
        download_urls = [
            dict(zip(["id", "code", "magnets"], row)) for row in download_result.all()
        ]

        # 获取磁力链接 - 明确指定要查询的列
        magnet_query = select(
            Magnet.id,
            Magnet.code,
            Magnet.url,
            Magnet.name,
            Magnet.size,
            Magnet.created_date,
        ).where(Magnet.code == movie.code)
        magnet_result = await self.db.execute(magnet_query)
        magnets = [
            dict(zip(["id", "code", "url", "name", "size", "created_date"], row))
            for row in magnet_result.all()
        ]

        # 获取观看链接 - 明确指定要查询的列
        watch_query = (
            select(
                WatchUrl.id, WatchUrl.code, WatchUrl.url, WatchUrl.name, WatchUrl.index
            )
            .where(WatchUrl.code == movie.code)
            .order_by(WatchUrl.index)
        )
        watch_result = await self.db.execute(watch_query)
        watch_urls = [
            dict(zip(["id", "code", "url", "name", "index"], row))
            for row in watch_result.all()
        ]

        # 构建响应对象
        movie_detail = {
            "movie": movie,
            "titles": titles,
            "genres": genres,
            "actresses": actresses,
            "download_urls": download_urls,
            "magnets": magnets,
            "watch_urls": watch_urls,
        }

        return MovieDetailResponse.model_validate(movie_detail)

    async def get_by_id(self, id: int) -> Optional[Movie]:
        result = await self.db.execute(select(Movie).where(Movie.id == id))
        return result.scalar_one_or_none()

    async def search_by_title(
        self,
        title: str,
        language: Optional[SupportedLanguage] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Movie]:
        query = select(Movie).join(MovieTitle, Movie.id == MovieTitle.movie_id)
        query = query.where(MovieTitle.title.ilike(f"%{title}%"))

        if language:
            query = query.where(MovieTitle.language == language)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_recent_releases(
        self, days: int = 30, skip: int = 0, limit: int = 20
    ) -> List[Movie]:
        cutoff_date = date.today() - timedelta(days=days)
        query = (
            select(Movie)
            .where(Movie.release_date >= cutoff_date)
            .order_by(desc(Movie.release_date))
        )
        result = await self.db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def get_popular_movies(self, skip: int = 0, limit: int = 20) -> List[Movie]:
        query = select(Movie).order_by(desc(Movie.likes))
        result = await self.db.execute(query.offset(skip).limit(limit))
        return result.scalars().all()

    async def increment_likes(self, movie_id: int) -> Optional[Movie]:
        movie = await self.get_by_id(movie_id)
        if not movie:
            return None

        movie.likes += 1
        await self.db.commit()
        await self.db.refresh(movie)
        return movie

    async def add_title(
        self, movie_id: int, title: str, language: SupportedLanguage
    ) -> Optional[MovieTitle]:
        movie = await self.get_by_id(movie_id)
        if not movie:
            return None

        movie_title = MovieTitle(movie_id=movie_id, title=title, language=language)
        self.db.add(movie_title)
        await self.db.commit()
        await self.db.refresh(movie_title)
        return movie_title

    async def save_movies(self, movies: List[Movie]) -> int:
        self.db.add_all(movies)
        await self.db.commit()
        return len(movies)
