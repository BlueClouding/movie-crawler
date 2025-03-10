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
        
        
    async def initialize_and_startGenres(self):
        """Initialize and start the crawler in background."""
        try:
            await self.startGenres()
        except Exception as e:
            self._logger.error(f"Error in crawler background task: {str(e)}")
            await self._update_status("failed", str(e))
            return False

    # async def initialize_and_startActresses(self):
    #     """Initialize and start the crawler in background."""
    #     try:
    #         await self.initialize()
    #         await self.startActresses()
    #     except Exception as e:
    #         self._logger.error(f"Error in crawler background task: {str(e)}")
    #         await self._update_status("failed", str(e))
    #         return False

    #startGenresPages
    async def initialize_and_startGenresPages(self):
        """Initialize and start the crawler in background."""
        try:
            await self.startGenresPages()
        except Exception as e:
            self._logger.error(f"Error in crawler background task: {str(e)}")
            await self._update_status("failed", str(e))
            return False

    async def initialize_and_startMovies(self):
        """Initialize and start the crawler in background."""
        try:
            await self.startMovies()
        except Exception as e:
            self._logger.error(f"Error in crawler background task: {str(e)}")
            await self._update_status("failed", str(e))
            return False
    
        
    async def startGenres(self):
        """Start the crawling process."""
        try:
            self._logger.info("Starting crawler manager...")
            
            # Step 1: Process genres
            await self._update_status("processing_genres")
            if not await self._genre_processor.process_genres(self._progress_manager):
                await self._update_status("failed", "Failed to process genres")
                return False

            if self._stop_flag:
                await self._update_status("stopped")
                return False
            self._logger.info("Successfully completed all crawling tasks")
            await self._update_status("completed")
            return True

        except Exception as e:
            error_msg = f"Error in crawler manager: {str(e)}"
            self._logger.error(error_msg)
            await self._update_status("failed", error_msg)
            return False

    async def startGenresPages(self):
        try:
            await self._update_status("processing_genre_pages")
            if not await self._genre_processor._process_genres_pages(self._progress_manager):
                await self._update_status("failed", "Failed to process genre pages")
                return False

            if self._stop_flag:
                await self._update_status("stopped")
                return False

            return True
        except Exception as e:
            error_msg = f"Error processing genre pages: {str(e)}"
            self._logger.error(error_msg)
            await self._update_status("failed", error_msg)
            return False

    async def startMovies(self):
        try:
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
            if not await self._detail_crawler.process_actresses():
                await self._update_status("failed", "Failed to process actress details")
                return False

            if self._stop_flag:
                await self._update_status("stopped")
                return False

            return True
        except Exception as e:
            error_msg = f"Error processing movie details: {str(e)}"
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
