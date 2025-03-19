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
from sqlalchemy import update

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

    async def saveOrUpdate(self, movie_details: Dict[str, Any]) -> bool:
        """Save or update movie details to the database.
        
        Args:   
            movie_details: Movie details dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """ 
        try:    
            # Check if movie already exists
            result = await self.db.execute(
                select(Movie).where(Movie.code == movie_details['code']))
            existing_movie = result.scalar_one_or_none()

            existing_title = existing_movie.title if hasattr(existing_movie, 'title') else ''
            existing_link = existing_movie.link if hasattr(existing_movie, 'link') else ''
            existing_cover_image_url = existing_movie.cover_image_url if hasattr(existing_movie, 'cover_image_url') else ''
            existing_preview_video_url = existing_movie.preview_video_url if hasattr(existing_movie, 'preview_video_url') else ''
            existing_thumbnail = existing_movie.thumbnail if hasattr(existing_movie, 'thumbnail') else ''
            existing_likes = existing_movie.likes if hasattr(existing_movie, 'likes') else 0
            existing_original_id = existing_movie.original_id if hasattr(existing_movie, 'original_id') else ''
            existing_code = existing_movie.code if hasattr(existing_movie, 'code') else ''
            existing_release_date = existing_movie.release_date if hasattr(existing_movie, 'release_date') else ''
            existing_duration = existing_movie.duration if hasattr(existing_movie, 'duration') else ''
            existing_description = existing_movie.description if hasattr(existing_movie, 'description') else ''
            existing_tags = existing_movie.tags if hasattr(existing_movie, 'tags') else ''
            existing_genres = existing_movie.genres if hasattr(existing_movie, 'genres') else ''
            existing_director = existing_movie.director if hasattr(existing_movie, 'director') else ''
            existing_maker = existing_movie.maker if hasattr(existing_movie, 'maker') else ''
            existing_actresses = existing_movie.actresses if hasattr(existing_movie, 'actresses') else ''
            
            if existing_movie:
                # Update existing movie                
                await self.db.execute(
                    update(Movie)
                    .where(Movie.code == movie_details['code'])
                    .values(
                        title=movie_details.get('title', existing_title),
                        link=movie_details.get('url', existing_link),
                        cover_image_url=movie_details.get('cover_image', existing_cover_image_url),
                        preview_video_url=movie_details.get('preview_video', existing_preview_video_url),
                        thumbnail=movie_details.get('thumbnail', existing_thumbnail),
                        likes=movie_details.get('likes', existing_likes),
                        original_id=movie_details.get('original_id', existing_original_id),
                        status=movie_details.get('status', MovieStatus.ONLINE.value),
                        code=movie_details.get('code', existing_code),
                        release_date=movie_details.get('release_date', existing_release_date),
                        duration=movie_details.get('duration', existing_duration),
                        description=movie_details.get('description', existing_description),
                        updated_at=func.current_timestamp(),
                        tags=movie_details.get('tags', existing_tags),
                        genres=movie_details.get('genres', existing_genres),
                        director=movie_details.get('director', existing_director),
                        maker=movie_details.get('maker', existing_maker),
                        actresses=movie_details.get('actresses', existing_actresses)
                    )
                )
                await self.db.commit()
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
                    status=movie_details.get('status', MovieStatus.ONLINE.value),
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
                # 修正: SQLAlchemy 2.0中，add方法不是异步的
                self.db.add(movie)
                await self.db.commit()
                return True
        except Exception as e:
            await self.db.rollback()
            self._logger.error(f"Error saving or updating movie: {str(e)}")
            return False