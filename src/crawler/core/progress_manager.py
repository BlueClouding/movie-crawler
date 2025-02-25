"""Progress manager module for tracking crawler progress."""

import logging
import threading
from datetime import datetime
from typing import Optional
from ...database.operations import CrawlerDB, CrawlerProgress

class ProgressManagerDB:
    """Manages crawler progress using database."""

    def __init__(self, language: str, crawler_db: CrawlerDB):
        """Initialize ProgressManagerDB.

        Args:
            language (str): Language code
            crawler_db (CrawlerDB): Database operations instance
        """
        self._language = language
        self._logger = logging.getLogger(__name__)
        self._crawler_db = crawler_db
        self._crawler_progress: Optional[CrawlerProgress] = None

    async def initialize(self):
        """Initialize crawler progress record."""
        self._crawler_progress = await self._crawler_db.create_crawler_progress(
            task_type=f"crawler_{self._language}"
        )

    async def get_genre_progress(self, genre_name: str) -> int:
        """Get the last processed page for a genre.

        Args:
            genre_name (str): Name of the genre

        Returns:
            int: Last processed page number, 0 if not started
        """
        if not self._crawler_progress:
            return 0
            
        page_progress = await self._crawler_db.get_page_progress(
            page_type="genre",
            relation_id=self._crawler_progress.id
        )
        return page_progress.page_number if page_progress else 0

    async def update_genre_progress(self, genre_name: str, page: int):
        """Update progress for a genre.

        Args:
            genre_name (str): Name of the genre
            page (int): Last processed page number
        """
        if not self._crawler_progress:
            return

        page_progress = await self._crawler_db.get_page_progress(
            page_type="genre",
            relation_id=self._crawler_progress.id
        )
        
        if page_progress:
            await self._crawler_db.update_pages_progress(
                id=page_progress.id,
                page_number=page
            )
        else:
            await self._crawler_db.create_pages_progress(
                crawler_progress_id=self._crawler_progress.id,
                relation_id=self._crawler_progress.id,
                page_type="genre",
                page_number=page,
                total_pages=-1  # Unknown total pages
            )

    async def get_detail_progress(self, genre_name: str) -> int:
        """Get the number of processed movies for a genre.

        Args:
            genre_name (str): Name of the genre

        Returns:
            int: Number of processed movies
        """
        if not self._crawler_progress:
            return 0

        page_progress = await self._crawler_db.get_page_progress(
            page_type="detail",
            relation_id=self._crawler_progress.id
        )
        return page_progress.processed_items if page_progress else 0

    async def update_detail_progress(self, genre_name: str, count: int):
        """Update the number of processed movies for a genre.

        Args:
            genre_name (str): Name of the genre
            count (int): Number of processed movies
        """
        if not self._crawler_progress:
            return

        page_progress = await self._crawler_db.get_page_progress(
            page_type="detail",
            relation_id=self._crawler_progress.id
        )
        
        if page_progress:
            await self._crawler_db.update_pages_progress(
                id=page_progress.id,
                processed_items=page_progress.processed_items + count
            )
        else:
            await self._crawler_db.create_pages_progress(
                crawler_progress_id=self._crawler_progress.id,
                relation_id=self._crawler_progress.id,
                page_type="detail",
                page_number=0,
                total_pages=-1,
                processed_items=count
            )

    async def is_genre_completed(self, genre_name: str) -> bool:
        """Check if a genre is completed.

        Args:
            genre_name (str): Name of the genre

        Returns:
            bool: True if genre is completed
        """
        if not self._crawler_progress:
            return False

        page_progress = await self._crawler_db.get_page_progress(
            page_type="genre",
            relation_id=self._crawler_progress.id
        )
        return page_progress.status == "completed" if page_progress else False

class ProgressManager:
    """Manager for tracking progress of all crawler tasks."""
    
    def __init__(self, language='en', crawler_db: CrawlerDB = None):
        """Initialize the progress manager.
        
        Args:
            language (str): Language code (e.g., 'en', 'ja')
            crawler_db (CrawlerDB): Database operations instance
        """
        if not crawler_db:
            raise ValueError("CrawlerDB instance is required")
            
        self.language = language
        self.crawler_db = crawler_db
        self.db_progress_manager = ProgressManagerDB(language, crawler_db)
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize the progress manager."""
        await self.db_progress_manager.initialize()
    
    async def update_genre_progress(self, genre_name: str, page: int):
        """Update genre processing progress.
        
        Args:
            genre_name (str): Name of the genre
            page (int): Current page number
        """
        with self.lock:
            await self.db_progress_manager.update_genre_progress(genre_name, page)
            self.logger.info(f"Updated genre progress for {genre_name} to page {page}")
    
    async def get_genre_progress(self, genre_name: str) -> int:
        """Get progress for a genre.
        
        Args:
            genre_name (str): Name of the genre
            
        Returns:
            int: Last processed page number
        """
        return await self.db_progress_manager.get_genre_progress(genre_name)
    
    async def update_detail_progress(self, genre_name: str, count: int):
        """Update detail crawler progress.
        
        Args:
            genre_name (str): Name of the genre
            count (int): Number of processed movies
        """
        with self.lock:
            await self.db_progress_manager.update_detail_progress(genre_name, count)
            self.logger.info(f"Updated detail progress for {genre_name}: {count} movies processed")
    
    async def get_detail_progress(self, genre_name: str) -> int:
        """Get progress for detail crawler.
        
        Args:
            genre_name (str): Name of the genre
            
        Returns:
            int: Number of processed movies
        """
        return await self.db_progress_manager.get_detail_progress(genre_name)
    
    async def is_genre_completed(self, genre_name: str) -> bool:
        """Check if a genre is completed.
        
        Args:
            genre_name (str): Name of the genre
            
        Returns:
            bool: True if genre is completed
        """
        return await self.db_progress_manager.is_genre_completed(genre_name)
    
    async def clear_progress(self):
        """Clear all progress data."""
        with self.lock:
            await self.db_progress_manager.clear_progress()
            self.logger.info("Cleared all progress data")
