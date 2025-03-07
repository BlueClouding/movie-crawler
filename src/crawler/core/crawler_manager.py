"""Crawler manager module for coordinating crawlers."""

import logging
import os
import asyncio
from typing import Optional, Dict, Any

from .genre_processor import GenreProcessor
from .detail_crawler import DetailCrawler
from ..utils.progress_manager import DBProgressManager
from ..db.connection import get_db_session

class CrawlerManager:
    """Manager for coordinating different crawlers."""
    
    def __init__(self, base_url: str, task_id: int, language: str = 'ja', threads: int = 1, clear_existing: bool = False, output_dir: Optional[str] = None):
        """Initialize CrawlerManager.

        Args:
            base_url: Base URL for the website
            task_id: Task ID for progress tracking
            language: Language code (en, ja, zh)
            threads: Number of threads to use
            clear_existing: Whether to clear existing data
            output_dir: Directory to save images
        """
        self._base_url = base_url
        self._language = language
        self._threads = threads
        self._clear_existing = clear_existing
        self._output_dir = output_dir
        self._task_id = task_id
        self._logger = logging.getLogger(__name__)
        self._stop_flag = False
        
        # These will be initialized later
        self._progress_manager = None
        self._genre_processor = None
        self._detail_crawler = None
        
    async def initialize(self):
        """Initialize database connections and progress manager."""
        try:
            # Get database session
            session = await get_db_session()
            if session is None:
                raise Exception("Failed to get database session")
                
            # Initialize progress manager
            self._progress_manager = DBProgressManager(language=self._language, task_id=self._task_id)
            await self._progress_manager.initialize(session)
            
            # Initialize genre processor
            self._genre_processor = GenreProcessor(self._base_url, self._language, db_session=session)
            
            # Initialize detail crawler
            self._detail_crawler = DetailCrawler(self._base_url, self._language, self._threads)
            await self._detail_crawler.initialize(self._progress_manager, self._output_dir)
            
            self._logger.info("Crawler manager initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Error initializing crawler manager: {str(e)}")
            return False
        
    async def initialize_and_start(self):
        """Initialize and start the crawler in background."""
        try:
            await self.initialize()
            await self.start()
        except Exception as e:
            self._logger.error(f"Error in crawler background task: {str(e)}")
        
    async def start(self):
        """Start the crawling process."""
        try:
            if not self._progress_manager:
                if not await self.initialize():
                    await self._update_status("failed", "Failed to initialize crawler")
                    return False
            
            self._logger.info("Starting crawler manager...")
            
            if self._clear_existing:
                await self._clear_data()

            # Step 1: Process genres
            await self._update_status("processing_genres")
            if not await self._genre_processor.process_genres(self._progress_manager):
                await self._update_status("failed", "Failed to process genres")
                return False

            if self._stop_flag:
                await self._update_status("stopped")
                return False

            # Step 2: Process movie details
            self._logger.info("Successfully processed genres, starting movie details processing")
            await self._update_status("processing_movies")
            
            if not await self._detail_crawler.process_pending_movies():
                await self._update_status("failed", "Failed to process movie details")
                return False

            if self._stop_flag:
                await self._update_status("stopped")
                return False

            # Step 3: Process actress details
            self._logger.info("Successfully processed movie details, starting actress processing")
            await self._update_status("processing_actresses")
            
            # if not await self._detail_crawler.process_actresses():
            #     await self._update_status("failed", "Failed to process actress details")
            #     return False

            # if self._stop_flag:
            #     await self._update_status("stopped")
            #     return False

            # All done!
            self._logger.info("Successfully completed all crawling tasks")
            await self._update_status("completed")
            return True

        except Exception as e:
            error_msg = f"Error in crawler manager: {str(e)}"
            self._logger.error(error_msg)
            await self._update_status("failed", error_msg)
            return False
            
    async def stop(self):
        """Stop the crawling process."""
        self._stop_flag = True
        await self._update_status("stopping")
            
    async def _update_status(self, status: str, message: Optional[str] = None):
        """Update crawler progress status."""
        if self._progress_manager and self._task_id:
            await self._progress_manager.update_task_status(
                self._task_id,
                status,
                message
            )
            self._logger.info(f"Updated task status to: {status}")
            
    async def _clear_data(self):
        """Clear existing data from database."""
        if not self._clear_existing or not self._progress_manager:
            return
            
        try:
            self._logger.info("Clearing existing data from database...")
            await self._progress_manager.clear_progress()
            self._logger.info("Successfully cleared existing data from database")
        except Exception as e:
            self._logger.error(f"Error clearing database: {str(e)}")
