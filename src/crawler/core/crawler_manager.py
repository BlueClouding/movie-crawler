"""Crawler manager module for coordinating crawlers."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from .genre_processor import GenreProcessor
from .detail_crawler import DetailCrawler
from ..utils.progress_manager import DBProgressManager
from src.database.operations import CrawlerDB,CrawlerProgress
from config.database import get_db,get_session_from_generator

class CrawlerManager:
    """Manager for coordinating different crawlers."""
    
    def __init__(self, language='jp', threads=1, clear_existing=False):
        """Initialize CrawlerManager.

        Args:
            language (str): Language code
            threads (int): Number of threads to use
            clear_existing (bool): Whether to clear existing data
        """
        self._language = language
        self._threads = threads
        self._clear_existing = clear_existing
        self._logger = logging.getLogger(__name__)
        self._base_url = f'http://123av.com/{language}'
        
        # Initialize database and progress manager
        self._progress_manager = DBProgressManager(language)
        
    async def start(self):
        """Start the crawling process."""
        try:
            self._logger.info("Starting crawler manager...")
            self._logger.info("Clear existing data flag is not set.")

            # Initialize progress manager
            await self._progress_manager.initialize()

            # Process genres first
            genre_processor = GenreProcessor(self._base_url, self._language)
            if not await genre_processor.process_genres(self._progress_manager):
                self._logger.error("Failed to process genres")
                return False

            self._logger.info("Successfully processed genres")

            # Start detail crawler
            detail_crawler = DetailCrawler(
                base_url=self._base_url,
                language=self._language,
                threads=self._threads,
                progress_manager=self._progress_manager
            )
            if not await detail_crawler.start():
                self._logger.error("Failed to process movie details")
                return False

            self._logger.info("Successfully processed movie details")
            return True

        except Exception as e:
            self._logger.error(f"Error in crawler manager: {str(e)}")
            return False
            
    async def _clear_data(self):
        """Clear existing data from database."""
        if not self._clear_existing:
            return
            
        session = await get_session_from_generator()
        if session is None:
            self._logger.error("Failed to get database session")
            return
            
        try:
            crawler_db = CrawlerDB(session)
            await crawler_db.clear_progress(self._language)
            self._logger.info("Cleared existing progress data from database")
        except Exception as e:
            self._logger.error(f"Error clearing database: {str(e)}")
