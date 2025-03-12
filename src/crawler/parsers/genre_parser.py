"""Genre parser module for extracting genre data from HTML."""

import logging
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from ..models.genre_info import GenreInfo
from common.enums.enums import SupportedLanguage

class GenreParser:
    """Parser for genre pages."""
    
    def __init__(self):
        """Initialize GenreParser."""
        self._logger : logging.Logger = logging.getLogger(__name__)
    
    def parse_genres_page(self, html_content: str, base_url: str) -> List[GenreInfo]:
        """Parse genres from the genres page.
        
        Args:
            html_content: HTML content of the genres page
            base_url: Base URL for the website
            
        Returns:
            list: List of genre dictionaries
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            genres = []   
            
            # 根据测试结果使用正确的选择器
            selectors = [
                'a[href*="/genres/"]',  # 这是最佳选择器，根据测试可以找到690个类型
                # 备用选择器
                '.genre-list a',
                '.category-list a',
                '.genres a',
                '.tags a',
                '.genre-item a',
                '.genre-box a',
                '.genre-section a',
                '.category a',
                '.tag-cloud a',
                'ul.genres li a',
                'div.genres a',
                '.genre-tag a',
                '.genre-link',
                'a[href*="/genre/"]',
                'a[href*="/category/"]'
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    self._logger.debug(f"Found {len(items)} genres using selector: {selector}")
                    for item in items:
                        try:
                            genre_name = item.get_text(strip=True)
                            url = item.get('href', '')
                            
                            # 处理URL格式，根据测试结果调整
                            if not url.startswith('http'):
                                # 如果是相对路径，添加基础URL
                                if not url.startswith('/'):
                                    url = f'/{url}'
                                
                                # 添加语言代码
                                url = f'/{SupportedLanguage.JAPANESE.value}/{url.lstrip("/")}'
                                url = f'{base_url}{url}'
                                
                            if genre_name and url:
                                # Extract genre ID if available
                                genre_id = None
                                id_match = re.search(r'/genre/(\d+)', url)
                                if id_match:
                                    genre_id = id_match.group(1)
                                
                                # 清理类型名称，去除数字和"動画"字样
                                clean_name = re.search(r'^(.*?)\d', genre_name).group(1).strip()
                                if not clean_name:
                                    clean_name = genre_name  # 如果清理后为空，保留原始名称
                                
                                # 从 URL 中提取 code
                                code = None
                                url_parts = url.rstrip('/').split('/')
                                if url_parts:
                                    code = url_parts[-1]
                                    # 如果最后一部分包含查询参数，则去除
                                    if '?' in code:
                                        code = code.split('?')[0]
                                
                                genres.append(GenreInfo(
                                    name=clean_name,
                                    url=url,
                                    id=genre_id,
                                    code=code,
                                    original_name=genre_name
                                ))
                                
                        except Exception as e:
                            self._logger.error(f"Error processing genre item: {str(e)}")
                            continue
                            
                    break
            
            return genres
            
        except Exception as e:
            self._logger.error(f"Error parsing genres page: {str(e)}")
            return []
    
    def get_pagination_info(self, html_content: str) -> Optional[int]:
        """Extract pagination information from a genre page.
        
        Args:
            html_content: HTML content of the genre page
            
        Returns:
            Optional[int]: Total number of pages, None if not found
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Try different selectors for pagination
            pagination_selectors = [
                '.pagination',
                '.pages',
                '.page-numbers',
                '.pager'
            ]
            
            for selector in pagination_selectors:
                pagination = soup.select_one(selector)
                if pagination:
                    # Try to find the last page number
                    page_links = pagination.select('a')
                    if page_links:
                        page_numbers = []
                        for link in page_links:
                            text = link.get_text(strip=True)
                            if text.isdigit():
                                page_numbers.append(int(text))
                            else:
                                # Check for href with page parameter
                                href = link.get('href', '')
                                page_match = re.search(r'[?&]page=(\d+)', href)
                                if page_match:
                                    page_numbers.append(int(page_match.group(1)))
                        
                        if page_numbers:
                            return max(page_numbers)
            
            # If no pagination found, check for a single page indicator
            items_count = len(soup.select('.movie-item') or soup.select('.video-item') or soup.select('.item'))
            if items_count > 0:
                return 1
            
            return None
            
        except Exception as e:
            self._logger.error(f"Error getting pagination info: {str(e)}")
            return None
