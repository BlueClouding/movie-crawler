"""Detail crawler module for fetching movie details."""

import logging
import os
import time
import random
import asyncio
from typing import Optional, List, Dict, Any
from ..utils.http import create_session
from ..parsers.movie_parser import MovieParser
from ..parsers.actress_parser import ActressParser
from crawler.service.crawler_progress_service import CrawlerProgressService
from fastapi import Depends

class MovieDetailCrawlerService:
    """Crawler for fetching movie details."""
    
    def __init__(self,
        crawler_progress_service: CrawlerProgressService = Depends(CrawlerProgressService)):
        """Initialize DetailCrawler.

        Args:
            crawler_progress_service: CrawlerProgressService instance for progress tracking
        """
        self._logger = logging.getLogger(__name__)
        
        # Create session with retry mechanism
        self._session = create_session(use_proxy=True)
        
        # Initialize parsers
        self._movie_parser = MovieParser()
        self._actress_parser = ActressParser()
        
        # Initialize retry counts
        self._retry_counts = {}
        
        # Initialize image downloader
        self._image_downloader = None

        self._crawler_progress_service = CrawlerProgressService()

    async def process_pending_movies(self, task_id:int) -> bool:
        """Process pending movies.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get pending movies from database
            pending_movies = await self._crawler_progress_service.get_pending_movies(task_id)
            if not pending_movies:
                self._logger.info("No pending movies to process")
                return True
                
            self._logger.info(f"Found {len(pending_movies)} pending movies to process")
            
            # Process movies in batches to avoid memory issues
            batch_size = 10
            for i in range(0, len(pending_movies), batch_size):
                batch = pending_movies[i:i+batch_size]
                tasks = []
                
                for movie in batch:
                    tasks.append(self._process_movie(movie))
                    
                # Wait a short time between starting tasks to avoid overwhelming the server
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Process batch
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log results
                success_count = sum(1 for r in results if r is True)
                error_count = sum(1 for r in results if isinstance(r, Exception))
                logging.info(f"Processed batch {i//batch_size + 1}/{(len(pending_movies) + batch_size - 1)//batch_size}: {success_count} succeeded, {error_count} failed")
                
                # Add delay between batches
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
            logging.info("Successfully processed all pending movies")
            return True
            
        except Exception as e:
            logging.error(f"Error processing pending movies: {str(e)}")
            return False

    async def _process_movie(self, movie_data: Dict[str, Any]) -> bool:
        """Process a single movie.
        
        Args:
            movie_data: Movie data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not movie_data.get('url'):
            self._logger.error("Movie data missing URL")
            return False
            
        url = movie_data['url']
        movie_id = movie_data.get('id')
        
        try:
            # Fetch movie details
            self._logger.info(f"Processing movie: {movie_data.get('title', url)}")
            
            # Get movie HTML
            response = self._session.get(url, timeout=30)
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch movie details: HTTP {response.status_code}")
                await self._crawler_progress_service.update_movie_status(movie_id, 'error')
                return False
                
            # Parse movie details
            movie_details = self._movie_parser.parse_movie_page(response.text, url)
            
            # Ensure movie_details is a dictionary
            if not isinstance(movie_details, dict):
                self._logger.error(f"Invalid movie details returned: {type(movie_details)}")
                movie_details = {}
                
            # Add original movie data
            for key, value in movie_data.items():
                if key not in movie_details:
                    movie_details[key] = value
            
            # Save movie details to database
            # Ensure self._db_operations is a proper object with saveOrUpdate method
            if not hasattr(self._db_operations, 'saveOrUpdate'):
                self._logger.error(f"Invalid db_operations object: {type(self._db_operations)}")
                # Re-initialize db_operations if needed
                self._db_operations = DBOperations(self._progress_manager._session)
                
            success = await self._db_operations.saveOrUpdate(movie_details)
            
            if success:
                # Update movie status
                await self._crawler_progress_service.update_movie_status(movie_id, 'completed')
                self._logger.info(f"Successfully processed movie: {movie_details.get('title', url)}")
                return True
            else:
                await self._crawler_progress_service.update_movie_status(movie_id, 'error')
                self._logger.error(f"Failed to save movie details: {movie_details.get('title', url)}")
                return False
                
        except Exception as e:
            self._logger.error(f"Error processing movie {url}: {str(e)}")
            await self._crawler_progress_service.update_movie_status(movie_id, 'error')
            return False
            
    async def process_actresses(self) -> bool:
        """Process actresses from movies.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get actresses from database
            actresses = await self._crawler_progress_service.get_actresses_to_process()
            if not actresses:
                self._logger.info("No actresses to process")
                return True
                
            self._logger.info(f"Found {len(actresses)} actresses to process")
            
            # Process actresses in batches
            batch_size = 5
            for i in range(0, len(actresses), batch_size):
                batch = actresses[i:i+batch_size]
                tasks = []
                
                for actress in batch:
                    tasks.append(self._process_actress(actress))
                    
                # Wait a short time between starting tasks
                await asyncio.sleep(random.uniform(1.0, 2.0))
                
                # Process batch
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Log results
                success_count = sum(1 for r in results if r is True)
                error_count = sum(1 for r in results if isinstance(r, Exception))
                self._logger.info(f"Processed actress batch {i//batch_size + 1}/{(len(actresses) + batch_size - 1)//batch_size}: {success_count} succeeded, {error_count} failed")
                
                # Add delay between batches
                await asyncio.sleep(random.uniform(2.0, 5.0))
                
            self._logger.info("Successfully processed all actresses")
            return True
            
        except Exception as e:
            self._logger.error(f"Error processing actresses: {str(e)}")
            return False
            
    async def _process_actress(self, actress_data: Dict[str, Any]) -> bool:
        """Process a single actress.
        
        Args:
            actress_data: Actress data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not actress_data.get('url'):
            self._logger.error("Actress data missing URL")
            return False
            
        url = actress_data['url']
        actress_id = actress_data.get('id')
        
        try:
            # Fetch actress details
            self._logger.info(f"Processing actress: {actress_data.get('name', url)}")
            
            # Get actress HTML
            response = self._session.get(url, timeout=30)
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch actress details: HTTP {response.status_code}")
                return False
                
            # Parse actress details
            actress_details = self._actress_parser.parse_actress_page(response.text, url)
            
            # Add original actress data
            for key, value in actress_data.items():
                if key not in actress_details:
                    actress_details[key] = value
            
            # Download profile image if downloader is available
            if self._image_downloader and actress_details.get('id') and actress_details.get('profile_image'):
                await self._image_downloader.download_image(
                    actress_details['profile_image'],
                    f"actresses/{actress_details['id']}.jpg"
                )
            
            # Save actress details to database
            success = await self._crawler_progress_service.save_actress_details(actress_details)
            
            if success:
                self._logger.info(f"Successfully processed actress: {actress_details.get('name', url)}")
                return True
            else:
                self._logger.error(f"Failed to save actress details: {actress_details.get('name', url)}")
                return False
                
        except Exception as e:
            self._logger.error(f"Error processing actress {url}: {str(e)}")
            return False

