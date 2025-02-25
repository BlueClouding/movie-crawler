import logging
from typing import Optional
from src.database.operations import CrawlerDB,CrawlerProgress
from config.database import get_db,get_session_from_generator

class DBProgressManager:
    """Manages crawler progress using database."""

    async def __init__(self, language: str): # Make __init__ async
        """Initialize CrawlerManager."""
        self._language = language
        self._progress_manager = None
        self._crawler_db = None

        
        session = await get_session_from_generator()
        if session is None:
            raise Exception("Failed to get database session from async generator")

        self._crawler_db = CrawlerDB(session) # Pass the session, not the generator
        self._progress_manager = DBProgressManager(language, self._crawler_db)
        await self._progress_manager.initialize()

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
