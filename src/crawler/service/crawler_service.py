"""Crawler manager module for coordinating crawlers."""

import logging
import os
import asyncio
from typing import Optional, Dict, Any

from crawler.service.genre_service import GenreService
from crawler.service.movie_detail_crawler_service import MovieDetailCrawlerService
from crawler.service.crawler_progress_service import CrawlerProgressService
from fastapi import Depends
from common.db.entity.crawler import CrawlerProgress

class CrawlerService:
    """Manager for coordinating different crawlers."""
    
    def __init__(self,
                 genre_service: GenreService = Depends(GenreService),
                 crawler_progress_service: CrawlerProgressService = Depends(CrawlerProgressService),
                 movie_detail_crawler_service: MovieDetailCrawlerService = Depends(MovieDetailCrawlerService)):
        """Initialize CrawlerService.

        Args:
            genre_service: Genre service instance
            crawler_progress_service: Crawler progress service instance
            movie_detail_crawler_service: Movie detail crawler service instance
        """
        self._logger = logging.getLogger(__name__)
        self._stop_flag = False
        
        # These will be initialized later
        self._crawler_progress_service = crawler_progress_service
        self._genre_service = genre_service
        self._movie_detail_crawler_service = movie_detail_crawler_service
        
    async def create_crawler_progress(self, crawler_progress: CrawlerProgress):
        self._logger.info(f"Creating crawler progress: {crawler_progress}")
        return await self._crawler_progress_service.create_crawler_progress(crawler_progress)
        
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
            if not await self._genre_service.process_genres():
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
            if not await self._genre_service.process_genres_pages():
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
            if not await self._movie_detail_crawler_service.process_pending_movies():
                await self._update_status("failed", "Failed to process movie details")
                return False

            if self._stop_flag:
                await self._update_status("stopped")
                return False

            # Step 3: Process actress details
            self._logger.info("Successfully processed movie details, starting actress processing")
            await self._update_status("processing_actresses")
            if not await self._movie_detail_crawler_service.process_actresses():
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
        await self._crawler_progress_service.update_task_status(
            self._task_id,
            status,
            message
        )
        self._logger.info(f"Updated task status to: {status}")
            
    async def _clear_data(self):
        """Clear existing data from database."""
        if not self._clear_existing or not self._crawler_progress_service:
            return
            
        try:
            self._logger.info("Clearing existing data from database...")
            await self._crawler_progress_service.clear_progress()
            self._logger.info("Successfully cleared existing data from database")
        except Exception as e:
            self._logger.error(f"Error clearing database: {str(e)}")
