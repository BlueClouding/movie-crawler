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
    # if insert session use it
    def __init__(self, db: AsyncSession = Depends(get_db_session), session: AsyncSession = Depends(get_db_session)):
        super().__init__(db)
        if session:
            self._session = session


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
        result = await self._session.execute(query)
        return result.scalars().all()

    async def saveOrUpdate(self, movie_details: Dict[str, Any]) -> bool:
        """Save or update movie details to the database.
        
        Args:   
            movie_details: Movie details dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """ 
        try:    
            # Check if movie already exists
            result = await self._session.execute(
                select(Movie).where(Movie.code == movie_details['code']))
            existing_movie = result.scalar_one_or_none()
            
            if existing_movie:
                # Update existing movie                
                await self._session.execute(
                    update(Movie)
                    .where(Movie.code == movie_details['code'])
                    .values(
                        title=movie_details.get('title', existing_movie.title),
                        link=movie_details.get('url', existing_movie.link),
                        cover_image_url=movie_details.get('cover_image', existing_movie.cover_image_url),
                        preview_video_url=movie_details.get('preview_video', existing_movie.preview_video_url),
                        thumbnail=movie_details.get('thumbnail', existing_movie.thumbnail),
                        likes=movie_details.get('likes', existing_movie.likes),
                        original_id=movie_details.get('original_id', existing_movie.original_id),
                        status=movie_details.get('status', MovieStatus.ONLINE.value),
                        code=movie_details.get('code', existing_movie.code),
                        release_date=movie_details.get('release_date', existing_movie.release_date),
                        duration=movie_details.get('duration', existing_movie.duration),
                        description=movie_details.get('description', existing_movie.description),
                        updated_at=func.current_timestamp(),
                        tags=movie_details.get('tags', existing_movie.tags),
                        genres=movie_details.get('genres', existing_movie.genres),
                        director=movie_details.get('director', existing_movie.director),
                        maker=movie_details.get('maker', existing_movie.maker),
                        actresses=movie_details.get('actresses', existing_movie.actresses)
                    )
                )
                await self._session.commit()
                return True
            else:
                # Create new movie
                movie = Movie(
                    code=movie_details['code'],
                    title=movie_details.get('title', ''),
                    link=movie_details.get('url', ''),
                    cover_image_url=movie_details.get('cover_image', ''),
                    preview_video_url=movie_details.get('preview_video', ''),
                    thumbnail=movie_details.get('thumbnail', ''),
                    likes=movie_details.get('likes', 0),
                    original_id=movie_details.get('original_id', 0),
                    status=movie_details.get('status', MovieStatus.NEW.value),
                    release_date=movie_details.get('release_date', ''),
                    duration=movie_details.get('duration', ''),
                    description=movie_details.get('description', ''),
                    updated_at=func.current_timestamp(),
                    tags=movie_details.get('tags', ''),
                    genres=movie_details.get('genres', ''),
                    director=movie_details.get('director', ''),
                    maker=movie_details.get('maker', ''),
                    actresses=movie_details.get('actresses', '')
                )
                await self._session.add(movie)
                await self._session.commit()
                return True
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error saving or updating movie: {str(e)}")
            return False