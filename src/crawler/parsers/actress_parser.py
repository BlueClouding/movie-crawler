"""Actress parser module for extracting actress data from HTML."""

import logging
import re
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from ..models.actress import Actress

class ActressParser:
    """Parser for actress pages."""
    
    def __init__(self, language: str = 'ja'):
        """Initialize ActressParser.
        
        Args:
            language: Language code
        """
        self._language = language
        self._logger = logging.getLogger(__name__)
    
    def parse_actress_page(self, html_content: str, url: str) -> Dict[str, Any]:
        """Parse actress detail page.
        
        Args:
            html_content: HTML content of the actress page
            url: URL of the actress page
            
        Returns:
            dict: Actress data
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            actress_data = {
                'url': url
            }
            
            # Extract actress ID from URL
            id_match = re.search(r'/actress/(\d+)', url)
            if id_match:
                actress_data['id'] = id_match.group(1)
            
            # Extract name
            name_elem = (
                soup.select_one('h3.name') or 
                soup.select_one('h1.name') or 
                soup.select_one('.actress-name') or
                soup.select_one('title')
            )
            if name_elem:
                actress_data['name'] = name_elem.get_text(strip=True)
            
            # Extract profile image
            profile_img = (
                soup.select_one('.actress-profile img') or 
                soup.select_one('.profile img') or
                soup.select_one('.actress-img img')
            )
            if profile_img:
                actress_data['profile_image'] = profile_img.get('src', '')
            
            # Extract info
            info_items = soup.select('.actress-info .info-item') or soup.select('.profile .info-item')
            for item in info_items:
                label = item.select_one('.label')
                value = item.select_one('.value')
                if label and value:
                    key = label.get_text(strip=True).lower().replace(' ', '_')
                    actress_data[key] = value.get_text(strip=True)
            
            # Extract related movies
            movie_links = self.extract_movie_links(html_content, url)
            if movie_links:
                actress_data['movies'] = movie_links
            
            return actress_data
            
        except Exception as e:
            self._logger.error(f"Error parsing actress page: {str(e)}")
            return {'url': url, 'error': str(e)}
    
    def extract_movie_links(self, html_content: str, base_url: str) -> List[Dict[str, str]]:
        """Extract movie links from an actress page.
        
        Args:
            html_content: HTML content
            base_url: Base URL for the website
            
        Returns:
            list: List of movie data dictionaries
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            movies = []
            
            # Try different selectors for movie items
            selectors = [
                '.movie-item',
                '.video-item',
                '.item',
                'article',
                '.content-item'
            ]
            
            for selector in selectors:
                items = soup.select(selector)
                if items:
                    for item in items:
                        try:
                            movie = {}
                            
                            # Get title
                            title_elem = item.select_one('h3') or item.select_one('.title') or item.select_one('a')
                            if title_elem:
                                movie['title'] = title_elem.get_text(strip=True)
                            
                            # Get URL
                            link = item.select_one('a')
                            if link:
                                url = link.get('href', '')
                                if url:
                                    if not url.startswith('http'):
                                        url = f'http://123av.com{url}'
                                    movie['url'] = url
                                    
                                    # Extract code from URL
                                    code_match = re.search(r'/([A-Z]+-\d+)', url)
                                    if code_match:
                                        movie['code'] = code_match.group(1)
                            
                            # Get thumbnail
                            img = item.select_one('img')
                            if img:
                                movie['thumbnail'] = img.get('src', '')
                            
                            if movie.get('url') and movie.get('title'):
                                movies.append(movie)
                                
                        except Exception as e:
                            self._logger.error(f"Error processing movie item: {str(e)}")
                            continue
                            
                    break
            
            return movies
            
        except Exception as e:
            self._logger.error(f"Error extracting movie links: {str(e)}")
            return []
