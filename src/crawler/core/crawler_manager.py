"""Crawler manager module for coordinating crawlers."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from .genre_processor import GenreProcessor
from .detail_crawler import DetailCrawler
from ..utils.progress import ProgressManager

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
        
        # 创建进度管理器
        self._progress_manager = ProgressManager(language)
        
    def start(self):
        """Start the crawling process."""
        try:
            self._logger.info("Starting crawler manager...")
            self._logger.info("Clear existing data flag is not set.")

            # Process genres first
            genre_processor = GenreProcessor(self._base_url, self._language)
            if not genre_processor.process_genres():
                self._logger.error("Failed to process genres")
                return False

            self._logger.info("Successfully processed genres")

            # Start detail crawler
            detail_crawler = DetailCrawler(
                base_url=self._base_url,
                language=self._language,
                threads=self._threads
            )
            if not detail_crawler.start():
                self._logger.error("Failed to process movie details")
                return False

            self._logger.info("Successfully processed movie details")
            return True

        except Exception as e:
            self._logger.error(f"Error in crawler manager: {str(e)}")
            return False
            
    def _clear_data(self):
        """Clear existing data directories."""
        dirs_to_clear = [
            os.path.join('genres', self._language),
            os.path.join('genre_movie', self._language),
            os.path.join('movie_details', self._language),
            os.path.join('failed_movies', self._language)
        ]
        
        for dir_path in dirs_to_clear:
            if os.path.exists(dir_path):
                for file_name in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file_name)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        self._logger.error(f"Error deleting file {file_path}: {str(e)}")
                        
        self._logger.info("Cleared existing data directories")
