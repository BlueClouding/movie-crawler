from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends
from app.repositories.base_repository import BaseRepositoryAsync
from app.config.database import get_db_session
from common.db.entity.movie_info import MovieInfo, MovieTitle
from common.db.entity.movie import Movie


class MovieInfoRepository(BaseRepositoryAsync[MovieInfo, int]):
    """
    Repository for MovieInfo entity operations
    
    Handles CRUD operations for movie detailed information
    """
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        super().__init__(db)
        import logging
        self._logger = logging.getLogger(__name__)


    async def create_movie_info(self, movie_info_data: Dict[str, Any]) -> MovieInfo:
        """
        Create a new movie info record
        
        Args:
            movie_info_data: Dictionary with movie information data
            
        Returns:
            MovieInfo: Created movie info entity
        """
        try:
            movie_info = MovieInfo(**movie_info_data)
            self.db.add(movie_info)
            await self.db.flush()
            return movie_info
        except Exception as e:
            self._logger.error(f"Error creating movie info: {str(e)}")
            raise

    async def get_movie_info_by_code(self, code: str,   language: str = 'ja') -> Optional[MovieInfo]:
        """
        Get movie info by movie code and language
        
        Args:
            code: Movie code
            language: Language code (default: 'ja')
            
        Returns:
            Optional[MovieInfo]: Movie info entity if found, None otherwise
        """
        query = select(MovieInfo).where(
            MovieInfo.code == code,
            MovieInfo.language == language
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_movie_info(self, movie_info_code: str, update_data: Dict[str, Any]) -> Optional[MovieInfo]:
        """
        Update an existing movie info record
        
        Args:
            movie_info_code: Code of the movie info to update
            update_data: Dictionary with data to update
            
        Returns:
            Optional[MovieInfo]: Updated movie info entity if found, None otherwise
        """
        try:
            movie_info = await self.get_movie_info_by_code(movie_info_code)
            if not movie_info:
                return None
                
            for key, value in update_data.items():
                if hasattr(movie_info, key):
                    setattr(movie_info, key, value)
            
            await self.db.flush()
            return movie_info
        except Exception as e:
            self._logger.error(f"Error updating movie info for code {movie_info_code}: {str(e)}")
            raise

    async def update_movie_info_by_code(self, code: str, language: str, update_data: Dict[str, Any]) -> Optional[MovieInfo]:
        """
        Update movie info by movie code and language
        
        Args:
            code: Movie code
            language: Language code
            update_data: Dictionary with data to update
            
        Returns:
            Optional[MovieInfo]: Updated movie info if found, None otherwise
        """
        try:
            movie_info = await self.get_movie_info_by_code(code, language)
            if not movie_info:
                return None
                
            for key, value in update_data.items():
                if hasattr(movie_info, key):
                    setattr(movie_info, key, value)
            
            await self.db.flush()
            return movie_info
        except Exception as e:
            self._logger.error(f"Error updating movie info for code {code}: {str(e)}")
            raise

    async def create_or_update_movie_info(self, code: str, language: str, movie_data: Dict[str, Any]) -> MovieInfo:
        """
        Create a new movie info record or update if it already exists
        
        Args:
            code: Movie code
            language: Language code
            movie_data: Dictionary with movie information
            
        Returns:
            MovieInfo: Created or updated movie info entity
        """
        try:
            # Check if movie info exists
            movie_info = await self.get_movie_info_by_code(code, language)
            
            # If exists, update it
            if movie_info:
                for key, value in movie_data.items():
                    if hasattr(movie_info, key):
                        setattr(movie_info, key, value)
            # Otherwise create new
            else:
                # Ensure code and language are in the data
                movie_data['code'] = code
                movie_data['language'] = language
                
                # Create movie_uuid if not provided
                if 'movie_uuid' not in movie_data:
                    movie_data['movie_uuid'] = uuid.uuid4()
                    
                movie_info = MovieInfo(**movie_data)
                self.db.add(movie_info)
                
            await self.db.flush()
            return movie_info
        except Exception as e:
            self._logger.error(f"Error creating/updating movie info for code {code}: {str(e)}")
            raise

    async def save_movie_title(self, movie_uuid, language, title) -> MovieTitle:
        """
        Save a movie title in a specific language
        
        Args:
            movie_uuid: UUID of the movie
            language: Language enum value or code
            title: Movie title text
            
        Returns:
            MovieTitle: Created or updated movie title entity
        """
        try:
            # Check if title already exists
            query = select(MovieTitle).where(
                MovieTitle.movie_uuid == movie_uuid,
                MovieTitle.language == language
            )
            result = await self.db.execute(query)
            movie_title = result.scalar_one_or_none()
            
            # If exists, update
            if movie_title:
                movie_title.title = title
            # Otherwise create new
            else:
                movie_title = MovieTitle(
                    movie_uuid=movie_uuid,
                    language=language,
                    title=title
                )
                self.db.add(movie_title)
                
            await self.db.flush()
            return movie_title
        except Exception as e:
            self._logger.error(f"Error saving movie title for {movie_uuid}, language: {language}: {str(e)}")
            raise


    #get_by_id
    def get_by_id(self, id: int) -> Optional[MovieInfo]:
        """
        Get movie info by ID
        
        Args:
            id: ID of the movie info to retrieve
            
        Returns:
            Optional[MovieInfo]: Movie info entity if found, None otherwise
        """
        query = select(MovieInfo).where(MovieInfo.id == id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()