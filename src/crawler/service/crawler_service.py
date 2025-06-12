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
from common.enums.enums import CrawlerStatus
import asyncio

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
        
    async def initialize_and_startGenres(self, crawler_progress_id: int):
        """Initialize and start the crawler in background."""
        try:
            await self.startGenres(crawler_progress_id, "https://www.123av.com", "ja")
        except Exception as e:
            self._logger.error(f"Error in crawler background task: {str(e)}")
            await self._update_status(crawler_progress_id, CrawlerStatus.FAILED.value)
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
    async def initialize_and_startGenresPages(self, crawler_progress_id: int):
        """Initialize and start the crawler in background."""
        await self._update_status(crawler_progress_id, CrawlerStatus.PROCESSING.value)
        self._logger.info("Starting genre pages processing...")
        await self.startGenresPages(crawler_progress_id)
        self._logger.info(f"已在后台启动类型页面爬取任务，任务ID: {crawler_progress_id}")
        return True
        
    async def startGenres(self, crawler_progress_id: int, base_url: str, language: str):
        """Start the crawling process."""
        try:
            self._logger.info("Starting crawler manager...")
            
            # Step 1: Process genres
            await self._update_status(crawler_progress_id, CrawlerStatus.PROCESSING.value)
            if not await self._genre_service.process_genres(base_url, language):
                await self._update_status(crawler_progress_id, CrawlerStatus.FAILED.value)
                return False

            if self._stop_flag:
                await self._update_status(crawler_progress_id, CrawlerStatus.STOPPED.value)
                return False
            self._logger.info("Successfully completed all crawling tasks")
            await self._update_status(crawler_progress_id, CrawlerStatus.COMPLETED.value)
            return True

        except Exception as e:
            error_msg = f"Error in crawler manager: {str(e)}"
            self._logger.error(error_msg)
            await self._update_status(crawler_progress_id, CrawlerStatus.FAILED.value)
            return False

    async def startGenresPages(self, crawler_progress_id: int):
        try:
            if not await self._genre_service.process_genres_pages(crawler_progress_id):
                await self._update_status(crawler_progress_id, CrawlerStatus.FAILED.value)
                return False
            return True
        except Exception as e:
            error_msg = f"Error processing genre pages: {str(e)}"
            self._logger.error(error_msg)
            await self._update_status(crawler_progress_id, CrawlerStatus.FAILED.value)
            return False


    async def stop(self, crawler_progress_id: int):
        """Stop the crawling process."""
        self._stop_flag = True
        await self._update_status(crawler_progress_id, CrawlerStatus.STOPPED.value)
        return True

    async def _update_status(self, crawler_progress_id: int, status: str):
        """Update crawler progress status."""
        await self._crawler_progress_service.update_task_status(crawler_progress_id, status)
        self._logger.info(f"Updated task status to: {status}")
        
    async def get_by_id(self, crawler_id: int):
        """Get crawler progress by ID.
        
        Args:
            crawler_id: ID of the crawler progress
            
        Returns:
            CrawlerProgressResponse: Crawler progress data
        """
        self._logger.info(f"Getting crawler progress with ID: {crawler_id}")
        result = await self._crawler_progress_service._crawler_progress_repository.get_by_id(crawler_id)
        if result is None:
            return None
        # Convert SQLAlchemy model to dict to avoid serialization issues
        if hasattr(result, '__dict__'):
            # Exclude SQLAlchemy internal attributes
            return {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
        return result
    
    async def get_pages_progress(self, crawler_id: int):
        """Get all pages progress for a crawler.
        
        Args:
            crawler_id: ID of the crawler progress
            
        Returns:
            List[PagesProgressResponse]: List of pages progress data
        """
        self._logger.info(f"Getting pages progress for crawler ID: {crawler_id}")
        results = await self._crawler_progress_service._page_crawler_repository.get_pages_by_crawler_id(crawler_id)
        # Convert SQLAlchemy models to dicts to avoid serialization issues
        return [{
            k: v for k, v in item.__dict__.items() 
            if not k.startswith('_')
        } for item in results] if results else []

    async def update_status(self, crawler_id: int, status: str):
        """Update crawler status.
        
        Args:
            crawler_id: ID of the crawler progress
            status: New status
            
        Returns:
            CrawlerProgressResponse: Updated crawler progress data
        """
        self._logger.info(f"Updating crawler status: {status} for ID: {crawler_id}")
        result = await self._crawler_progress_service.update_task_status(crawler_id, status)
        if result is None:
            return None
        # Convert SQLAlchemy model to dict to avoid serialization issues
        if hasattr(result, '__dict__'):
            # Exclude SQLAlchemy internal attributes
            return {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
        return result

    async def update_progress(self, page_id: int, processed_items: int, status: str = None):
        """Update page progress.
        
        Args:
            page_id: ID of the page progress
            processed_items: Number of processed items
            status: New status (optional)
            
        Returns:
            PagesProgressResponse: Updated page progress data
        """
        self._logger.info(f"Updating page progress: {processed_items} items for page ID: {page_id}")
        result = await self._crawler_progress_service.update_page_progress(
            page_progress_id=page_id, 
            status=status, 
            processed_items=processed_items
        )
        if result is None:
            return None
        # Convert SQLAlchemy model to dict to avoid serialization issues
        if hasattr(result, '__dict__'):
            # Exclude SQLAlchemy internal attributes
            return {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
        return result
        
    async def create_page_progress(self, page_data: dict):
        """Create a new page progress record.
        
        Args:
            page_data: Dictionary containing page progress information
            
        Returns:
            PagesProgress: Created page progress instance
        """
        self._logger.info(f"Creating page progress with data: {page_data}")
        try:
            result = await self._crawler_progress_service.create_genre_page_progress(
                genre_id=page_data.get('genre_id'),
                page=page_data.get('page_number', 1),
                total_pages=page_data.get('total_pages', 1),
                code=page_data.get('genre_code'),
                status=page_data.get('status'),
                total_items=page_data.get('total_items'),
                task_id=page_data.get('crawler_progress_id')
            )
            if result is None:
                return None
            # Convert SQLAlchemy model to dict to avoid serialization issues
            if hasattr(result, '__dict__'):
                # Exclude SQLAlchemy internal attributes
                return {k: v for k, v in result.__dict__.items() if not k.startswith('_')}
            return result
        except Exception as e:
            self._logger.error(f"Error creating page progress: {str(e)}")
            raise