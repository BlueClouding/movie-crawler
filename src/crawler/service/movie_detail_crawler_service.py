"""Detail crawler module for fetching movie details."""

from ctypes import Array
import logging
import os
import time
import asyncio
import random
from typing import Optional, List, Dict, Any
from ..utils.http import create_session
from ..parsers.movie_parser import MovieParser
from ..parsers.actress_parser import ActressParser
from crawler.service.crawler_progress_service import CrawlerProgressService
from fastapi import Depends
from crawler.repository.movie_repository import MovieRepository
from common.db.entity.movie import Movie, MovieStatus
from urllib.parse import urlparse, urlunparse

class MovieDetailCrawlerService:
    """Crawler for fetching movie details."""
    
    def __init__(self,
        crawler_progress_service: CrawlerProgressService = Depends(CrawlerProgressService),
        movie_repository: MovieRepository = Depends(MovieRepository)
        ):
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

        self._crawler_progress_service = crawler_progress_service
        self._movie_repository = movie_repository

    # 单次执行的方法
    async def process_movies_details_once(self) -> List[Movie]:
        """Process one batch of pending movies."""
        # Get pending movies from database
        new_movies: List[Movie] = await self._movie_repository.get_new_movies(100)
        if not new_movies:
            self._logger.info(f"No pending movies to process.")
            return

        self._logger.info(f"Found {len(new_movies)} pending movies to process")
        

        # 处理每个电影
        processed_count = 0
        movies_details: List[Movie] = []
        
        # 每个电影单独处理，并且每个电影使用单独的数据库事务
        for movie in new_movies:
            try:
                movie_detail = await self._process_movie(movie)
                if movie_detail:
                    movies_details.append(movie_detail)
                    processed_count += 1
            except Exception as e:
                self._logger.error(f"Error processing movie {movie.code}: {str(e)}")

        self._logger.info(f"Successfully processed {processed_count} out of {len(new_movies)} pending movies in this cycle.")
        return movies_details

    async def _process_movie(self, movie: Movie) -> Movie:
        """Process a single movie.
        
        Args:
            movie: Movie object to process
            
        Returns:
            Movie: Complete movie details or None if extraction fails
        """
        url = movie.link
        url = self.modify_url(url)
        movie.link = url
        
        try:
            # Get movie HTML
            response = self._session.get(url, timeout=30)
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch movie details: HTTP {response.status_code}")
                return None
                
            # Parse movie details
            movie_detail = self._movie_parser.parse_movie_page(movie, response.text, url)
            return movie_detail
        except Exception as e:
            self._logger.error(f"Error processing movie {url}: {str(e)}")
            return None

    def modify_url(self, url: str) -> str:
        parsed = urlparse(url)
        path_parts = parsed.path.split('/')  # 拆解路径
        
        # 查找最后一个 "v" 的位置
        try:
            v_index = path_parts.index("v", 2)  # 从第3个元素开始查找（跳过空字符串和 "ja"）
        except ValueError:
            return url  # 若未找到 "v"，返回原链接
    
        # 重组路径：保留 "ja" 和 "v" 之后的部分
        new_path = f"/{path_parts[1]}/v/{path_parts[v_index+1]}"
        new_parsed = parsed._replace(path=new_path)
        return urlunparse(new_parsed)
            
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

