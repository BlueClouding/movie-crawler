"""Genre processor module for crawling movie genres."""

import logging
import time
from typing import Optional, List, Dict, Any
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from common.db.entity.movie import Movie
from ..utils.http import create_session
from ..service.crawler_progress_service import CrawlerProgressService
from ..parsers.genre_parser import GenreParser
from ..parsers.movie_parser import MovieParser
from app.repositories.genre_repository import GenreRepository
from common.db.entity.genre import Genre
from common.enums.enums import SupportedLanguage, SupportedLanguageEnum
import requests
from ..service.crawler_progress_service import CrawlerProgressService
from ..models.genre_info import GenreInfo
from ..repository.movie_crawler_repository import MovieCrawlerRepository

class GenreService:
    """Processor for genre data."""
    
    def __init__(self,
                 genre_repository: GenreRepository = Depends(GenreRepository),
                 crawler_progress_service: CrawlerProgressService = Depends(CrawlerProgressService),
                 movie_crawler_repository: MovieCrawlerRepository = Depends(MovieCrawlerRepository),
                 genre_parser: GenreParser = Depends(GenreParser),
                 movie_parser: MovieParser = Depends(MovieParser)
    ):
        """Initialize GenreProcessor.

        Args:
            genre_repository: GenreRepository instance for genre operations
            crawler_progress_service: CrawlerProgressService instance for progress tracking
            genre_parser: GenreParser instance for parsing genre data
            movie_parser: MovieParser instance for parsing movie data
        """
        self._logger : logging.Logger = logging.getLogger(__name__)
        self._session : requests.Session = create_session(use_proxy=True)
        self._genre_parser : GenreParser = genre_parser
        self._movie_parser : MovieParser = movie_parser
        self._genre_repository : GenreRepository = genre_repository
        self._crawler_progress_service : CrawlerProgressService = crawler_progress_service
        self._movie_crawler_repository : MovieCrawlerRepository = movie_crawler_repository
        
        # 限制爬取的类型数量和页数
        self._max_genres : Optional[int] = None  # 默认不限制
        self._max_pages : Optional[int] = None   # 默认不限制
        
    # 拆分 genres 处理和 page 处理
    async def process_genres(self, base_url: str, language: str) -> bool:
        """Process and save genres.
        
        Returns:
            bool: True if successful, False otherwise
        """
            
        try:
            # Fetch genres
            self._logger.info("Processing genres...")
            genres : List[GenreInfo] = await self._fetch_genres(base_url, language)
            if not genres:
                self._logger.error("Failed to fetch genres")
                return False

            self._logger.info(f"Found {len(genres)} genres")
            self._logger.info("Processing genre pages...")
            
            # Process each genre
            # 如果设置了最大类型数量限制，则只处理指定数量的类型
            max_genres = self._max_genres if self._max_genres is not None else len(genres)
            self._logger.info(f"Processing up to {max_genres} genres")

            # 先把所有genres保存到数据库
            await self.save_genres_to_db(genres, language)
            
            self._logger.info("Successfully processed all genres")
            return True

        except Exception as e:
            self._logger.error(f"Error processing genres: {str(e)}")
            return False


    async def process_genres_pages(self, task_id: int) -> bool:
        # Process each genre
        all_genres : List[Genre] = await self._genre_repository.get_all()
        max_genres : int = self._max_genres if self._max_genres is not None else len(all_genres)
        self._logger.info(f"Processing up to {max_genres} genres")

        for i, genre in enumerate(all_genres[:max_genres]):
            try:
                # 提前获取所有需要的属性，避免懒加载问题
                genre_id = genre.id
                genre_code = genre.code
                genre_urls = genre.urls.copy() if hasattr(genre, 'urls') and genre.urls else []
                
                if not genre_urls:
                    self._logger.warning(f"No URLs found for genre ID {genre_id}, skipping")
                    continue
                    
                self._logger.info(f"Processing genre {i+1}/{max_genres}: {genre_code}")
                
                # Get current progress
                current_page : int = await self._crawler_progress_service.get_genre_progress(genre_id, code=genre_code, task_id=task_id)
                
                # Process genre pages
                total_pages : int = await self._get_total_pages(genre_urls[0])
                if not total_pages:
                    self._logger.warning(f"Could not determine total pages for genre {genre_code}, skipping")
                    continue
                    
                self._logger.info(f"Genre {genre_code} has {total_pages} pages, current progress: {current_page}")

                # Process each page
                await self._process_genre_pages(genre_id, genre_code, genre_urls, total_pages, current_page, task_id)
            except Exception as genre_error:
                self._logger.error(f"Error processing genre {genre_code}: {str(genre_error)}")
                continue
                
        self._logger.info("Successfully processed all genres")
        return True

    async def _process_genre_pages(self, genre_id: int, genre_code: str, genre_urls: list, total_pages: int, current_page: int, task_id: int) -> bool:
        # Create a new progress manager for each page to avoid session conflicts        
        for page in range(current_page + 1, total_pages + 1):
            try:
                # Process page and get movie data
                self._logger.info(f"Processing page {page}/{total_pages} for genre {genre_code}")

                # Create progress record for this page
                page_progress_id : int = await self._crawler_progress_service.create_genre_page_progress(
                    genre_id=genre_id,
                    page=page,
                    total_pages=total_pages,
                    code=genre_code,
                    status='processing',
                    total_items=0,
                    task_id=task_id
                )
                
                if not page_progress_id:
                    self._logger.error(f"Failed to create progress record for page {page} of genre {genre_code}")
                    continue


                movies : List[Movie] = await self._process_page_get_movies(genre_urls[0], page)
                
                if not movies:
                    self._logger.warning(f"No movies found on page {page} for genre {genre_code}")
                    # Create progress record anyway to mark this page as processed
                    await self._crawler_progress_service.create_genre_page_progress(
                        genre_id=genre_id,
                        page=page,
                        total_pages=total_pages,    
                        code=genre_code,
                        status='completed',
                        total_items=len(movies),
                        task_id=task_id
                    )
                    continue
                        
                # Save movies
                saved_count : int = await self._movie_crawler_repository.save_movies(movies)
                    
                # Update progress status to completed if movies were saved
                if saved_count > 0:
                    await self._crawler_progress_service.update_page_progress(
                        page_progress_id=page_progress_id,
                        status='completed',
                        processed_items=saved_count
                    )
                    
            except Exception as page_error:
                self._logger.error(f"Error processing page {page} for genre {genre_code}: {str(page_error)}", exc_info=True)
                continue
        
        return True
            
    async def _fetch_genres(self, base_url: str, language: str) -> list:
        """Fetch all available genres from the website.
        
        Returns:
            list: List of genre dictionaries
        """
        try:
            url = f"{base_url}/{language}/genres"
            self._logger.info(f"Fetching genres from: {url}")
            response = self._session.get(url, timeout=10)
            
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch genres: HTTP {response.status_code}")
                return []
            
            genres : List[GenreInfo] = self._genre_parser.parse_genres_page(response.text, base_url)
            self._logger.info(f"Found {len(genres)} genres")
            return genres
            
        except Exception as e:
            # 使用exc_info=True参数记录完整的堆栈跟踪信息，包括文件名和行号
            self._logger.error(f"Error fetching genres: {str(e)}", exc_info=True)
            return []
            
    async def _get_total_pages(self, url: str) -> Optional[int]:
        """Get total number of pages for a genre.
        
        Args:
            url: Genre URL
            
        Returns:
            Optional[int]: Total number of pages, None if failed
        """
        try:
            response = self._session.get(url, timeout=10)
            if response.status_code != 200:
                self._logger.error(f"Failed to get total pages: HTTP {response.status_code}")
                return None
            
            total_pages = self._genre_parser.get_pagination_info(response.text)
            if total_pages:
                self._logger.info(f"Found {total_pages} pages")
            else:
                self._logger.warning("Could not determine total pages")
                
            return total_pages
            
        except Exception as e:
            self._logger.error(f"Error getting total pages: {str(e)}")
            return None
            
    async def _process_page_get_movies(self, base_url: str, page: int) -> List[Movie]:
        """Process a single page of a genre.
        
        Args:
            base_url: Base URL of the genre
            page: Page number to process
            
        Returns:
            list: List of movie data dictionaries
        """
        try:
            # 确保 URL 包含语言代码
            import re
            
            # 构建带页码的URL
            url = f"{base_url}?page={page}"
            response = self._session.get(url, timeout=10)
            if response.status_code != 200:
                self._logger.error(f"Failed to process page {page}: HTTP {response.status_code}")
                return []
            
            movies = self._movie_parser.extract_movie_links(response.text, "https://www.123av.com/ja")
            return movies
            
        except Exception as e:
            self._logger.error(f"Error processing page {page}: {str(e)}")
            return []

    async def save_genres_to_db(self, genre_infos: List[GenreInfo], language: str):
        """Save genres to database.
        
        Args:
            genre_infos: List of genre dictionaries
            
        Returns:
            List of saved Genre objects
        """
        # Process genres one by one with proper transaction handling
        for genre_info in genre_infos:
            try:
                # First check if genre already exists by code in its own transaction
                existing_genre = await self._genre_repository.get_by_code(
                    code=genre_info.code
                )
                
                if existing_genre:
                    self._logger.info(f"Genre with code {genre_info.code} already exists, skipping creation")
                    continue
                    
                # Create new genre if it doesn't exist in a separate transaction
                await self._genre_repository.create_with_names(
                    urls=[genre_info.url],
                    language=language,
                    name=genre_info.name,
                    code=genre_info.code
                )
                self._logger.info(f"Created new genre: {genre_info.name} with code {genre_info.code}")
            except Exception as genre_error:
                self._logger.error(f"Error processing genre {genre_info.name}: {str(genre_error)}", exc_info=True)
                # No need to manually rollback with async with begin()
                # Continue with next genre instead of failing the entire batch
                continue
       
            
    async def _get_genre_name(self, genre_id: int) -> str:
        """Get genre name by genre id.
        
        Args:
            genre_id: Genre ID
            
        Returns:
            Genre name string
        """
        try:
            # 获取genre及其名称
            genre_result = await self._genre_repository.get_with_names(genre_id=genre_id)
            if genre_result and len(genre_result) == 2:
                genre, names = genre_result
                if names:
                    # 尝试获取当前语言的名称
                    for name_data in names:
                        if name_data.language == self._language:
                            return name_data.name
                    # 如果没有当前语言的名称，返回第一个名称
                    return names[0].name
            # 如果没有找到名称，尝试直接获取genre
            genre = await self._genre_repository.get(genre_id)
            if genre:
                return f"Genre {genre.code or genre_id}"
            return f"Genre {genre_id}"
        except Exception as e:
            self._logger.error(f"Error getting genre name: {str(e)}")
            return f"Genre {genre_id}"

    async def _get_all_genres(self) -> List[Genre]:
        """Get all genres from the database.
        
        Returns:
            List of genre dictionaries
        """
        try:
            # Get all genres from the database
            genres = await self._genre_repository.get_all()
            if not genres:
                self._logger.warning("No genres found in the database")
                return []
            
            return genres
        except Exception as e:
            self._logger.error(f"Error getting all genres: {str(e)}")
            return []

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Genre processor')
    
    parser.add_argument('--language',
                       type=str,
                       default='ja',
                       choices=['en', 'ja', 'zh'],
                       help='Language code')
                       
    parser.add_argument('--base-url',
                       type=str,
                       default='http://123av.com',
                       help='Base URL for the website')
    
    args = parser.parse_args()
    
    # This is just a placeholder for command-line usage
    # In practice, this would be integrated with the crawler manager
    print(f"Genre processor would start with language: {args.language}")
    print(f"Base URL: {args.base_url}")
    print("This is a library module and should be used through the crawler manager.")

if __name__ == '__main__':
    main()