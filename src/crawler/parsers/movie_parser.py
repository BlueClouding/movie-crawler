"""Movie parser module for extracting movie data from HTML."""

import logging
import re
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup

class MovieParser:
    """Parser for movie detail pages."""
    
    def __init__(self, language: str = 'ja'):
        """Initialize MovieParser.
        
        Args:
            language: Language code
        """
        self._language = language
        self._logger = logging.getLogger(__name__)
    
    def parse_movie_page(self, html_content: str, url: str) -> Dict[str, Any]:
        """Parse movie detail page.
        
        Args:
            html_content: HTML content of the movie page
            url: URL of the movie page
            
        Returns:
            dict: Movie data
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            movie_data = {
                'url': url
            }
            
            # Extract movie code from URL
            code_match = re.search(r'/([A-Z]+-\d+)', url)
            if code_match:
                movie_data['code'] = code_match.group(1)
            
            # Extract title
            title_elem = (
                soup.select_one('h3.title') or 
                soup.select_one('h1.title') or 
                soup.select_one('.movie-title') or
                soup.select_one('title')
            )
            if title_elem:
                movie_data['title'] = title_elem.get_text(strip=True)
            
            # Extract cover image
            cover_img = (
                soup.select_one('.movie-cover img') or 
                soup.select_one('.cover img') or
                soup.select_one('.movie-img img') or
                soup.select_one('.bigImage')
            )
            if cover_img:
                movie_data['cover_image'] = cover_img.get('src', '')
            
            # Extract thumbnails
            thumbnails = []
            thumb_containers = (
                soup.select('.sample-box img') or 
                soup.select('.sample-img img') or
                soup.select('.preview-images img')
            )
            for img in thumb_containers:
                src = img.get('src', '')
                if src:
                    thumbnails.append(src)
            
            if thumbnails:
                movie_data['thumbnails'] = thumbnails
            
            # Extract release date
            date_elem = (
                soup.select_one('.movie-info .date') or 
                soup.select_one('.info .date') or
                soup.select_one('[itemprop="dateCreated"]')
            )
            if date_elem:
                movie_data['release_date'] = date_elem.get_text(strip=True)
            
            # Extract actress names
            actress_elems = (
                soup.select('.movie-info .actress a') or 
                soup.select('.info .actress a') or
                soup.select('.cast a')
            )
            if actress_elems:
                movie_data['actresses'] = [a.get_text(strip=True) for a in actress_elems]
            
            # Extract genres
            genre_elems = (
                soup.select('.movie-info .genre a') or 
                soup.select('.info .genre a') or
                soup.select('.categories a')
            )
            if genre_elems:
                movie_data['genres'] = [g.get_text(strip=True) for g in genre_elems]
            
            # Extract duration
            duration_elem = (
                soup.select_one('.movie-info .duration') or 
                soup.select_one('.info .duration') or
                soup.select_one('[itemprop="duration"]')
            )
            if duration_elem:
                movie_data['duration'] = duration_elem.get_text(strip=True)
            
            # Extract description
            desc_elem = (
                soup.select_one('.movie-info .description') or 
                soup.select_one('.info .description') or
                soup.select_one('[itemprop="description"]')
            )
            if desc_elem:
                movie_data['description'] = desc_elem.get_text(strip=True)
            
            return movie_data
            
        except Exception as e:
            self._logger.error(f"Error parsing movie page: {str(e)}")
            return {'url': url, 'error': str(e)}
    
    def extract_movie_links(self, html_content: str, base_url: str) -> List[Dict[str, str]]:
        """Extract movie links from a page.
        
        Args:
            html_content: HTML content
            base_url: Base URL for the website
            
        Returns:
            list: List of movie data dictionaries
        """
        try:
            self._logger.info(f"Extracting movie links from HTML content (length: {len(html_content)})")
            soup = BeautifulSoup(html_content, 'html.parser')
            movies = []
            
            # Try different selectors for movie items
            selectors = [
                '.movie-item',
                '.video-item',
                '.item',
                'article',
                '.content-item',
                '.box-item',  # 根据测试脚本发现的选择器
                '.movie-box',
                '.video-box',
                '.thumbnail',
                '.movie',
                '.video'
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    self._logger.info(f"Found {len(items)} items using selector: {selector}")
                    for item in items:
                        try:
                            movie = {}
                            
                            # Get title
                            # 尝试多种选择器获取标题
                            title_selectors = [
                                'h3', '.title', '.name', '.movie-title', '.video-title',
                                '.movie-box-title', '.box-title', '.item-title'
                            ]
                            
                            title_elem = None
                            for selector in title_selectors:
                                title_elem = item.select_one(selector)
                                if title_elem:
                                    break
                                    
                            # 如果没有找到标题元素，尝试使用链接的文本
                            if not title_elem:
                                title_elem = item.select_one('a')
                                
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                if title:
                                    movie['title'] = title
                                elif 'alt' in title_elem.attrs:
                                    # 如果文本为空，尝试使用alt属性
                                    movie['title'] = title_elem.get('alt', '')
                            
                            # Get URL
                            link = item.select_one('a')
                            if link:
                                url = link.get('href', '')
                                if url:
                                    # 处理URL格式
                                    if not url.startswith('http'):
                                        # 如果是相对路径，添加域名
                                        if url.startswith('/'):
                                            url = f'{base_url}/{url}'
                                        else:
                                            url = f'{base_url}/{url}'
                                    else:
                                        # 修复URL中的comv问题
                                        url = url.replace('123av.comv/', '123av.com/v/')
                                    movie['url'] = url
                                    
                                    # Extract code from URL
                                    code_match = re.search(r'/([A-Z]+-\d+)', url)
                                    if code_match:
                                        movie['code'] = code_match.group(1)
                            
                            # Get thumbnail
                            img = item.select_one('img')
                            if img:
                                thumbnail = img.get('src', '')
                                if not thumbnail:
                                    # 如果没有src属性，尝试使用data-src属性
                                    thumbnail = img.get('data-src', '')
                                    
                                if thumbnail:
                                    # 处理缓存图片URL
                                    if not thumbnail.startswith('http'):
                                        if thumbnail.startswith('/'):
                                            thumbnail = f'{base_url}/{thumbnail}'
                                        else:
                                            thumbnail = f'{base_url}/{thumbnail}'
                                            
                                    movie['thumbnail'] = thumbnail     
                            
                            # Get release date
                            date_elem = item.select_one('.date') or item.select_one('.time')
                            if date_elem:
                                movie['release_date'] = date_elem.get_text(strip=True)
                            
                            # 如果有URL就添加，不必要求有code
                            if movie.get('url'):
                                self._logger.info(f"Found movie: {movie}")
                                movies.append(movie)
                            else:
                                self._logger.warning(f"Skipping movie without URL: {movie}")
                                
                        except Exception as e:
                            self._logger.error(f"Error processing movie item: {str(e)}")
                            continue
                            
                    # 如果找到了电影，就不再尝试其他选择器
                    if movies:
                        self._logger.info(f"Successfully extracted {len(movies)} movies using selector: {selector}")
                        break
            
            self._logger.info(f"Extracted {len(movies)} movies in total")
            return movies
            
        except Exception as e:
            self._logger.error(f"Error extracting movie links: {str(e)}")
            return []
