"""Database operations module."""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, update, delete, insert
from app.db.entity.crawler import CrawlerProgress, PagesProgress, VideoProgress
from app.db.entity.movie import Movie
from app.db.entity.genre import Genre
from app.db.entity.movie_actress import MovieActress
from app.db.entity.movie_genres import MovieGenre

class DBOperations:
    """Database operations for crawler."""
    
    def __init__(self, session: AsyncSession):
        """Initialize database operations.
        
        Args:
            session: SQLAlchemy async session
        """
        self._session = session
        self._logger = logging.getLogger(__name__)
    
    async def create_crawler_progress(self, task_type: str) -> Optional[CrawlerProgress]:
        """Create a new crawler progress record.
        
        Args:
            task_type: Type of crawler task
            
        Returns:
            Optional[CrawlerProgress]: Created crawler progress record
        """
        try:
            crawler_progress = CrawlerProgress(
                task_type=task_type,
                status='running'
            )
            self._session.add(crawler_progress)
            await self._session.commit()
            await self._session.refresh(crawler_progress)
            return crawler_progress
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error creating crawler progress: {str(e)}")
            return None
    
    async def update_crawler_progress(self, task_id: int, status: str) -> bool:
        """Update crawler progress status.
        
        Args:
            task_id: ID of the crawler task
            status: New status
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            await self._session.execute(
                update(CrawlerProgress)
                .where(CrawlerProgress.id == task_id)
                .values(status=status)
            )
            await self._session.commit()
            return True
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error updating crawler progress: {str(e)}")
            return False
    
    async def get_genre_progress(self, task_id: int, genre_id: int) -> int:
        """Get the last processed page for a genre.
        
        Args:
            task_id: ID of the crawler task
            genre_id: ID of the genre
            
        Returns:
            int: Last processed page number
        """
        try:
            result = await self._session.execute(
                select(PagesProgress.page_number)
                .where(
                    PagesProgress.crawler_progress_id == task_id,
                    PagesProgress.genre_id == genre_id
                )
            )
            page = result.scalar_one_or_none()
            return page or 0
        except Exception as e:
            self._logger.error(f"Error getting genre progress: {str(e)}")
            return 0
    
    async def update_genre_progress(self, task_id: int, genre_id: int, page: int) -> bool:
        """Update genre processing progress.
        
        Args:
            task_id: ID of the crawler task
            genre_id: ID of the genre
            page: Current page number
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if progress record exists
            result = await self._session.execute(
                select(PagesProgress)
                .where(
                    PagesProgress.crawler_progress_id == task_id,
                    PagesProgress.genre_id == genre_id
                )
            )
            progress = result.scalar_one_or_none()
            
            if progress:
                # Update existing record
                await self._session.execute(
                    update(PagesProgress)
                    .where(
                        PagesProgress.crawler_progress_id == task_id,
                        PagesProgress.genre_id == genre_id
                    )
                    .values(page_number=page)
                )
            else:
                # Create new record
                await self._session.execute(
                    insert(PagesProgress).values(
                        crawler_progress_id=task_id,
                        genre_id=genre_id,
                        page_number=page
                    )
                )
                
            await self._session.commit()
            return True
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error updating genre progress: {str(e)}")
            return False
    
    async def save_movie(self, task_id: int, movie_data: Dict[str, Any]) -> bool:
        """Save movie data to the database.
        
        Args:
            task_id: ID of the crawler task
            movie_data: Movie data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not movie_data:
            return False
            
        try:
            # Insert movie data into VideoProgress table
            await self._session.execute(
                insert(VideoProgress).values(
                    crawler_progress_id=task_id,
                    genre_id=movie_data.get('genre_id'),
                    page_number=movie_data.get('page_number'),
                    title=movie_data.get('title'),
                    url=movie_data.get('url'),
                    code=movie_data.get('code'),
                    thumbnail=movie_data.get('thumbnail'),
                    release_date=movie_data.get('release_date'),
                    page_progress_id=movie_data.get('page_progress_id'),
                    status='pending'
                )
            )
            await self._session.commit()
            return True
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error saving movie: {str(e)}")
            return False
    
    
    async def _save_movie_genres(self, movie_id: int, genres: List[str]) -> bool:
        """Save movie genres.
        
        Args:
            movie_id: ID of the movie
            genres: List of genre names
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete existing movie genres
            await self._session.execute(
                delete(MovieGenre).where(MovieGenre.movie_id == movie_id)
            )
            
            # Save new genres
            for genre_name in genres:
                # Find or create genre
                result = await self._session.execute(
                    select(Genre).where(Genre.name == genre_name)
                )
                genre = result.scalar_one_or_none()
                
                if not genre:
                    genre = Genre(name=genre_name)
                    self._session.add(genre)
                    await self._session.commit()
                    await self._session.refresh(genre)
                
                # Create movie-genre association
                movie_genre = MovieGenre(
                    movie_id=movie_id,
                    genre_id=genre.id
                )
                self._session.add(movie_genre)
            
            await self._session.commit()
            return True
            
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error saving movie genres: {str(e)}")
            return False
    
    async def _save_movie_actresses(self, movie_id: int, actresses: List[str]) -> bool:
        """Save movie actresses.
        
        Args:
            movie_id: ID of the movie
            actresses: List of actress names
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete existing movie actresses
            await self._session.execute(
                delete(MovieActress).where(MovieActress.movie_id == movie_id)
            )
            
            # Save new actresses
            for actress_name in actresses:
                # Find or create actress
                result = await self._session.execute(
                    select(Actress).where(Actress.name == actress_name)
                )
                actress = result.scalar_one_or_none()
                
                if not actress:
                    actress = Actress(name=actress_name)
                    self._session.add(actress)
                    await self._session.commit()
                    await self._session.refresh(actress)
                
                # Create movie-actress association
                movie_actress = MovieActress(
                    movie_id=movie_id,
                    actress_id=actress.id
                )
                self._session.add(movie_actress)
            
            await self._session.commit()
            return True
            
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error saving movie actresses: {str(e)}")
            return False


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
                        status=movie_details.get('status', existing_movie.status),
                        code=movie_details.get('code', existing_movie.code),
                        release_date=movie_details.get('release_date', existing_movie.release_date),
                        duration=movie_details.get('duration', existing_movie.duration),
                        description=movie_details.get('description', existing_movie.description),
                        updated_at=func.current_timestamp()
                    )
                )
                success = True
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
                    status=movie_details.get('status', 'new'),
                    release_date=movie_details.get('release_date', ''),
                    duration=movie_details.get('duration', ''),
                    description=movie_details.get('description', ''),
                    updated_at=func.current_timestamp()
                )
                self._session.add(movie)
                success = True
                
            if success:
                await self._session.commit()
                return True
                
        except Exception as e:
            self._logger.error(f"Error saving or updating movie: {str(e)}")
            try:
                await self._session.rollback()
            except Exception as rollback_error:
                self._logger.error(f"Error during rollback: {str(rollback_error)}")
            return False