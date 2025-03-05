"""Genre processor module for crawling movie genres."""

import logging
import time
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from ..utils.http import create_session
from ..utils.progress_manager import DBProgressManager
from ..parsers.genre_parser import GenreParser
from ..parsers.movie_parser import MovieParser
from app.repositories.genre_repository import GenreRepository
from app.db.entity.genre import Genre
from app.db.entity.enums import SupportedLanguage

class GenreProcessor:
    """Processor for genre data."""
    
    def __init__(self, base_url: str, language: str, db_session: Optional[AsyncSession] = None):
        """Initialize GenreProcessor.

        Args:
            base_url: Base URL for the website
            language: Language code
            db_session: Optional database session for genre operations
        """
        self._base_url = base_url
        self._language = language
        self._logger = logging.getLogger(__name__)
        self._session = create_session(use_proxy=True)
        self._genre_parser = GenreParser(language)
        self._movie_parser = MovieParser(language)
        self._db_session = db_session
        self._genre_repository = GenreRepository()
        
        # 限制爬取的类型数量和页数
        self._max_genres = None  # 默认不限制
        self._max_pages = None   # 默认不限制
        
    async def process_genres(self, progress_manager: DBProgressManager) -> bool:
        """Process and save genres.
        
        Args:
            progress_manager: DBProgressManager instance for tracking progress
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Fetch genres
            self._logger.info("Processing genres...")
            genres = await self._fetch_genres()
            if not genres:
                self._logger.error("Failed to fetch genres")
                return False

            self._logger.info(f"Found {len(genres)} genres")
            self._logger.info("Processing genre pages...")
            
            # Process each genre
            # 如果设置了最大类型数量限制，则只处理指定数量的类型
            max_genres = self._max_genres if self._max_genres is not None else len(genres)
            self._logger.info(f"Processing up to {max_genres} genres")
            
            for i, genre in enumerate(genres[:max_genres]):
                try:
                    # 使用 genre 中的 code 字段
                    genre_code = genre.get('code')
                    
                    self._logger.info(f"Processing genre: {genre['name']}, code: {genre_code}")
                    
                    # 使用 code 查询数据库中的 genre
                    # 如果没有找到，则使用索引作为 genre_id
                    genre_id = i  # 默认使用索引
                    
                    # 如果提供了数据库会话，则尝试根据 code 查询或创建 genre
                    if self._db_session and genre_code:
                        try:
                            # 尝试根据 code 查询或创建 genre
                            db_genre_id = await self._get_or_create_genre_by_code(genre_code, genre)
                            if db_genre_id is not None:
                                genre_id = db_genre_id
                        except Exception as e:
                            self._logger.error(f"Error querying/creating genre: {str(e)}")
                            # 如果发生错误，继续使用默认的索引作为 genre_id
                    
                    # Get current progress
                    current_page = await progress_manager.get_genre_progress(genre_id, code=genre_code)
                    if current_page > 0:
                        self._logger.info(f"Resuming genre {genre['name']} from page {current_page}")
                    
                    # Process genre pages
                    total_pages = await self._get_total_pages(genre['url'])
                    if total_pages is None:
                        self._logger.error(f"Failed to get total pages for genre: {genre['name']}")
                        continue
                        
                    # 如果设置了最大页数限制，则只处理指定数量的页面
                    if self._max_pages is not None and self._max_pages < total_pages:
                        self._logger.info(f"Limiting to {self._max_pages} pages for genre: {genre['name']}")
                        total_pages = self._max_pages
                    
                    # Update progress
                    await progress_manager.update_genre_progress(
                        genre_id=genre_id,
                        page=current_page,
                        total_pages=total_pages,
                        code=genre_code
                    )
                    
                    # Process each page
                    for page in range(current_page + 1, total_pages + 1):
                        try:
                            # Process page and save data immediately
                            movies = await self._process_page(genre['url'], page)
                            if movies:
                                # Save each movie individually
                                for movie in movies:
                                    try:
                                        movie['genre_id'] = genre_id
                                        movie['page_number'] = page
                                        await progress_manager.save_movie(movie)
                                    except Exception as e:
                                        self._logger.error(f"Error saving movie: {str(e)}")
                                        continue
                            
                            # Update progress after each page
                            await progress_manager.update_genre_progress(
                                genre_id=genre_id,
                                page=page,
                                total_pages=total_pages,
                                code=genre_code
                            )
                        except Exception as e:
                            self._logger.error(f"Error processing page {page} of genre {genre['name']}: {str(e)}")
                            continue
                    
                except Exception as e:
                    self._logger.error(f"Error processing genre {genre['name']}: {str(e)}")
                    continue

            self._logger.info("Successfully processed all genres")
            return True

        except Exception as e:
            self._logger.error(f"Error processing genres: {str(e)}")
            return False
            
    async def _fetch_genres(self) -> list:
        """Fetch all available genres from the website.
        
        Returns:
            list: List of genre dictionaries
        """
        try:
            # 根据测试结果使用正确的URL路径
            if self._language:
                # 正确的URL是 base_url/language/genres
                url = f"{self._base_url}/{self._language}/genres"
            else:
                # 如果没有语言参数，则使用默认路径
                url = f"{self._base_url}/genres"
                
            self._logger.info(f"Fetching genres from: {url}")
            response = self._session.get(url, timeout=10)
            
            if response.status_code != 200:
                self._logger.error(f"Failed to fetch genres: HTTP {response.status_code}")
                return []
            
            genres = self._genre_parser.parse_genres_page(response.text, self._base_url)
            self._logger.info(f"Found {len(genres)} genres")
            return genres
            
        except Exception as e:
            self._logger.error(f"Error fetching genres: {str(e)}")
            return []
            
    async def _get_or_create_genre_by_code(self, code: str, genre: Dict[str, Any]) -> Optional[int]:
        """根据 code 查询或创建 genre
        
        Args:
            code: 类型代码
            genre: 类型信息字典
            
        Returns:
            Optional[int]: 类型 ID，如果发生错误则返回 None
        """
        try:
            # 查询数据库中是否存在匹配的 genre
            db_genre = await self._genre_repository.get_by_code(
                self._db_session, code=code
            )
            
            if db_genre:
                # 如果找到了匹配的 genre，则使用其 ID
                self._logger.info(f"Found existing genre with code {code}, id: {db_genre.id}")
                return db_genre.id
            else:
                # 如果没有找到匹配的 genre，则创建新的 genre
                # 准备多语言名称数据
                names = [
                    {
                        "name": genre['name'],
                        "language": SupportedLanguage(self._language) if self._language else SupportedLanguage.ja
                    }
                ]
                
                # 创建新的 genre，直接传入 code 参数
                new_genre = await self._genre_repository.create_with_names(
                    self._db_session,
                    names=names,
                    urls=[genre['url']] if 'url' in genre else [],
                    code=code
                )
                
                self._logger.info(f"Created new genre with code {code}, id: {new_genre.id}")
                return new_genre.id
        except Exception as e:
            self._logger.error(f"Error in _get_or_create_genre_by_code: {str(e)}")
            return None
            
    async def _get_total_pages(self, url: str) -> Optional[int]:
        """Get total number of pages for a genre.
        
        Args:
            url: Genre URL
            
        Returns:
            Optional[int]: Total number of pages, None if failed
        """
        try:
            # 确保 URL 包含语言代码
            import re
            
            # 打印原始URL便于调试
            self._logger.info(f"Original URL: {url}")
            
            # 如果 URL 是 dm*/genres/* 格式，需要添加语言代码
            if re.search(r'dm\d+/genres/', url):
                # 提取域名部分
                domain_part = url.split('//')[-1].split('/')[0]
                # 提取路径部分
                path_part = '/'.join(url.split('//')[-1].split('/')[1:])
                
                # 构建新的URL，包含语言代码
                url = f"http://{domain_part}/{self._language}/{path_part}"
                self._logger.info(f"Adjusted URL with language code: {url}")
            
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
            
    async def _process_page(self, base_url: str, page: int) -> list:
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
            
            # 如果 URL 是 dm*/genres/* 格式，需要添加语言代码
            if re.search(r'dm\d+/genres/', url) and f"/{self._language}/" not in url:
                # 提取域名部分
                domain_part = url.split('//')[-1].split('/')[0]
                # 提取路径部分
                path_parts = url.split('//')[-1].split('/')
                # 提取查询参数部分
                query_part = ""
                if "?" in path_parts[-1]:
                    path_parts[-1], query_part = path_parts[-1].split("?", 1)
                    query_part = "?" + query_part
                
                # 重新构建路径
                path_part = '/'.join(path_parts[1:])
                
                # 构建新的URL，包含语言代码
                url = f"http://{domain_part}/{self._language}/{path_part}{query_part}"
                self._logger.info(f"Adjusted page URL with language code: {url}")
            
            response = self._session.get(url, timeout=10)
            if response.status_code != 200:
                self._logger.error(f"Failed to process page {page}: HTTP {response.status_code}")
                return []
            
            movies = self._movie_parser.extract_movie_links(response.text, self._base_url + '/' + self._language)
            return movies
            
        except Exception as e:
            self._logger.error(f"Error processing page {page}: {str(e)}")
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