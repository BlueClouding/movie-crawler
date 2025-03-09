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
        if not self._db_session:
            self._logger.error("Database session is not initialized")
            return False
            
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

            # 先把所有genres保存到数据库
            saved_genres = await self._save_genres_to_db(genres)
            if not saved_genres:
                self._logger.error("Failed to save genres to database")
                return False
            
            # Process each genre
            for i, genre in enumerate(saved_genres[:max_genres]):
                try:
                    # 使用 genre 中的 code 字段
                    genre_code = genre.code
                    self._logger.info(f"Processing genre {i+1}/{max_genres}: {genre_code}")
                    
                    # Get current progress
                    current_page = await progress_manager.get_genre_progress(genre.id, code=genre_code)
                    
                    # Process genre pages
                    total_pages = await self._get_total_pages(genre.urls[0])
                    if not total_pages:
                        self._logger.warning(f"Could not determine total pages for genre {genre_code}, skipping")
                        continue
                        
                    self._logger.info(f"Genre {genre_code} has {total_pages} pages, current progress: {current_page}")

                    # Process each page
                    for page in range(current_page + 1, total_pages + 1):
                        try:
                            # Process page and get movie data
                            self._logger.info(f"Processing page {page}/{total_pages} for genre {genre_code}")
                            movies = await self._process_page(genre.urls[0], page)
                            
                            if not movies:
                                self._logger.warning(f"No movies found on page {page} for genre {genre_code}")
                                # Create progress record anyway to mark this page as processed
                                await progress_manager.create_genre_progress(
                                    genre_id=genre.id,
                                    page=page,
                                    total_pages=total_pages,
                                    code=genre_code,
                                    status='completed',
                                    total_items=0
                                )
                                # Commit to save progress even when no movies found
                                await self._db_session.commit()
                                continue
                                
                            # Create progress record for this page
                            page_progress_id = await progress_manager.create_genre_progress(
                                genre_id=genre.id,
                                page=page,
                                total_pages=total_pages,
                                code=genre_code,
                                status='processing',
                                total_items=len(movies)
                            )
                            
                            # Commit progress record
                            await self._db_session.commit()
                            
                            # Prepare all movies with required data
                            prepared_movies = []
                            for movie in movies:
                                try:
                                    # Create a copy of the movie dictionary to avoid modifying the original
                                    movie_data = dict(movie)
                                    movie_data['genre_id'] = genre.id
                                    movie_data['page_number'] = page
                                    movie_data['page_progress_id'] = page_progress_id
                                    prepared_movies.append(movie_data)
                                except Exception as prep_error:
                                    self._logger.error(f"Error preparing movie data: {str(prep_error)}")
                            
                            # Save movies one by one with proper async handling
                            saved_count = 0
                            for movie_data in prepared_movies:
                                try:
                                    # Save movie to database - each save operation creates its own transaction
                                    movie_id = await progress_manager.save_movie(movie_data)
                                    if movie_id:
                                        saved_count += 1
                                    # Commit after each successful save to avoid transaction conflicts
                                    await self._db_session.commit()
                                except Exception as movie_error:
                                    self._logger.error(f"Error saving movie: {str(movie_error)}")
                                    try:
                                        await self._db_session.rollback()
                                    except Exception as rollback_error:
                                        self._logger.error(f"Error rolling back transaction: {str(rollback_error)}")
                                    # Continue with next movie
                                    continue
                            
                            self._logger.info(f"Saved {saved_count}/{len(movies)} movies from page {page}")
                            
                            # Update progress status to completed
                            if saved_count > 0:
                                await progress_manager.update_page_progress(
                                    page_progress_id=page_progress_id,
                                    status='completed',
                                    processed_items=saved_count
                                )
                                await self._db_session.commit()
                        except Exception as page_error:
                            self._logger.error(f"Error processing page {page} for genre {genre_code}: {str(page_error)}")
                            try:
                                await self._db_session.rollback()
                            except Exception as rollback_error:
                                self._logger.error(f"Error rolling back transaction: {str(rollback_error)}")
                            continue
                except Exception as genre_error:
                    self._logger.error(f"Error processing genre {genre_code}: {str(genre_error)}")
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
                url = f"{self._base_url}/{self._language.value}/genres"
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
            # 使用exc_info=True参数记录完整的堆栈跟踪信息，包括文件名和行号
            self._logger.error(f"Error fetching genres: {str(e)}", exc_info=True)
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
            # 使用独立的事务来防止事务中止问题
            async with self._db_session.begin_nested() as nested:
                # 查询数据库中是否存在匹配的 genre
                db_genre = await self._genre_repository.get_by_code(
                    self._db_session, code=code
                )
                
                if db_genre:
                    # 如果找到了匹配的 genre，则使用其 ID
                    self._logger.info(f"Found existing genre with code {code}, id: {db_genre.id}")
                    return db_genre.id
            
            # 如果没有找到匹配的 genre，则在新的事务中创建
            async with self._db_session.begin_nested() as nested:
                # 准备多语言名称数据
                name = {
                    "name": genre['name'],
                    "language": SupportedLanguage(self._language) if self._language else SupportedLanguage.ja
                }
                
                # 创建新的 genre，直接传入 code 参数
                new_genre = await self._genre_repository.create_with_names(
                    self._db_session,
                    name=name,
                    urls=[genre['url']] if 'url' in genre else [],
                    code=code
                )
                
                self._logger.info(f"Created new genre with code {code}, id: {new_genre.id}")
                return new_genre.id
        except Exception as e:
            # 使用exc_info=True记录完整的堆栈跟踪信息
            self._logger.error(f"Error in _get_or_create_genre_by_code: {str(e)}", exc_info=True)
            # 确保事务被回滚
            try:
                await self._db_session.rollback()
            except Exception as rollback_error:
                self._logger.error(f"Error rolling back transaction: {str(rollback_error)}", exc_info=True)
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
            
            # 改进的URL处理逻辑，确保所有URL都添加语言代码
            if self._language and self._language.value:
                # 确保我们使用语言的value属性
                language_code = self._language.value
                
                # 分析URL结构
                if '://' in url:
                    protocol, rest = url.split('://', 1)
                else:
                    protocol = 'http'
                    rest = url
                    
                if '/' in rest:
                    domain, path = rest.split('/', 1)
                else:
                    domain = rest
                    path = ''
                
                # 始终添加语言代码，即使是 dm*/genres/* 格式
                if not path.startswith(f"{language_code}/"):
                    path = f"{language_code}/{path.lstrip('/')}"
                
                # 构建新的URL
                url = f"{protocol}://{domain}/{path}"
                    
                print(f"DEBUG - Adjusted URL with language code: {url}")
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
                url = f"http://{domain_part}/{path_part}{query_part}"
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

    async def _save_genres_to_db(self, genres: List[Dict[str, Any]]):
        """Save genres to database.
        
        Args:
            genres: List of genre dictionaries
            
        Returns:
            List of saved Genre objects
        """
        if not self._db_session:
            self._logger.error("Database session is not initialized")
            return []
            
        saved_genres = []
        
        try:
            # Process genres one by one without nested transactions
            for genre in genres:
                try:
                    # First check if genre already exists by code
                    existing_genre = await self._genre_repository.get_by_code(
                        self._db_session, 
                        code=genre['code']
                    )
                    
                    if existing_genre:
                        self._logger.info(f"Genre with code {genre['code']} already exists, skipping creation")
                        saved_genres.append(existing_genre)
                        # Commit after each successful check to avoid transaction conflicts
                        await self._db_session.commit()
                        continue
                        
                    # Create new genre if it doesn't exist
                    db_genre = await self._genre_repository.create_with_names(
                        self._db_session,
                        urls=[genre['url']],
                        name = {
                            'language': SupportedLanguage(self._language) if self._language else SupportedLanguage.ja,
                            'name': genre['name']
                        },
                        code=genre['code']
                    )
                    
                    # Commit after each successful creation to avoid transaction conflicts
                    await self._db_session.commit()
                    
                    saved_genres.append(db_genre)
                    self._logger.info(f"Created new genre: {genre['name']} with code {genre['code']}")
                except Exception as genre_error:
                    self._logger.error(f"Error processing genre {genre.get('name', 'unknown')}: {str(genre_error)}")
                    try:
                        await self._db_session.rollback()
                    except Exception as rollback_error:
                        self._logger.error(f"Error rolling back transaction: {str(rollback_error)}")
                    # Continue with next genre instead of failing the entire batch
                    continue
            
            self._logger.info(f"Successfully saved {len(saved_genres)} genres to database")
            return saved_genres
        except Exception as e:
            self._logger.error(f"Error saving genres to database: {str(e)}")
            try:
                await self._db_session.rollback()
            except Exception as rollback_error:
                self._logger.error(f"Error rolling back transaction: {str(rollback_error)}")
            return []
            
    async def _get_genre_name(self, genre_id: int) -> str:
        """Get genre name by genre id.
        
        Args:
            genre_id: Genre ID
            
        Returns:
            Genre name string
        """
        try:
            # 获取genre及其名称
            genre_result = await self._genre_repository.get_with_names(self._db_session, genre_id=genre_id)
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
            genre = await self._genre_repository.get(self._db_session, genre_id)
            if genre:
                return f"Genre {genre.code or genre_id}"
            return f"Genre {genre_id}"
        except Exception as e:
            self._logger.error(f"Error getting genre name: {str(e)}")
            return f"Genre {genre_id}"

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